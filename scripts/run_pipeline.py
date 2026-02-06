"""Main pipeline orchestrator.

Steps:
1. Seed reference data (labs, cities, departments)
2. Load and normalize all 5 lab CSVs
3. Run test matching to create canonical tests
4. Upload everything to Supabase
"""
import sys
import os
import re
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tqdm import tqdm
from pipeline.config import CSV_FILES, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BATCH_SIZE
from pipeline.db import get_client, batch_upsert, batch_insert
from pipeline.models import NormalizedLabTest
from pipeline.ingest.metropolis_loader import MetropolisLoader
from pipeline.ingest.agilus_loader import AgilusLoader
from pipeline.ingest.apollo_loader import ApolloLoader
from pipeline.ingest.neuberg_loader import NeubergLoader
from pipeline.ingest.trustlab_loader import TRUSTlabLoader
from pipeline.ingest.city_normalizer import normalize_city, get_all_cities, CITY_STATE_MAP
from pipeline.ingest.department_normalizer import normalize_department, get_all_departments
from pipeline.matching.matcher import TestMatcher


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:200]


def step1_seed_reference_data(client):
    """Seed labs, cities, departments."""
    print("\n=== Step 1: Seeding Reference Data ===")

    # Labs
    labs_data = [
        {"name": "Metropolis Healthcare", "slug": "metropolis", "website_url": "https://www.metropolisindia.com"},
        {"name": "Agilus Diagnostics", "slug": "agilus", "website_url": "https://agilusdiagnostics.com"},
        {"name": "Apollo Diagnostics", "slug": "apollo", "website_url": "https://www.apollodiagnostics.in"},
        {"name": "Neuberg Diagnostics", "slug": "neuberg", "website_url": "https://www.neubergdiagnostics.com"},
        {"name": "TRUSTlab Diagnostics", "slug": "trustlab", "website_url": "https://www.trustlab.in"},
    ]
    result = batch_upsert(client, "labs", labs_data, "slug")
    print(f"  Labs: {result} rows")

    # Cities
    cities_data = get_all_cities()
    result = batch_upsert(client, "cities", cities_data, "name,state")
    print(f"  Cities: {result} rows")

    # Departments
    depts_data = get_all_departments()
    result = batch_upsert(client, "departments", depts_data, "slug")
    print(f"  Departments: {result} rows")

    return labs_data, cities_data, depts_data


def step2_load_csvs():
    """Load all 5 lab CSVs into normalized format."""
    print("\n=== Step 2: Loading CSVs ===")

    loaders = {
        "metropolis": MetropolisLoader(),
        "agilus": AgilusLoader(),
        "apollo": ApolloLoader(),
        "neuberg": NeubergLoader(),
        "trustlab": TRUSTlabLoader(),
    }

    all_tests: dict[str, list[NormalizedLabTest]] = {}

    for slug, loader in loaders.items():
        csv_path = CSV_FILES.get(slug)
        if not csv_path or not os.path.exists(csv_path):
            print(f"  WARNING: CSV not found for {slug}: {csv_path}")
            continue
        tests = loader.load(csv_path)
        all_tests[slug] = tests

    total = sum(len(v) for v in all_tests.values())
    print(f"\n  Total loaded: {total} rows across {len(all_tests)} labs")
    return all_tests, loaders


def step3_create_lab_locations(client, all_tests: dict):
    """Create lab_location records and return lookup maps."""
    print("\n=== Step 3: Creating Lab Locations ===")

    # Get lab IDs
    labs_result = client.table("labs").select("id, slug").execute()
    lab_id_map = {r["slug"]: r["id"] for r in labs_result.data}

    # Get city IDs
    cities_result = client.table("cities").select("id, name").execute()
    city_id_map = {r["name"]: r["id"] for r in cities_result.data}

    # Collect unique (lab_slug, location_code) pairs
    location_set = set()
    for slug, tests in all_tests.items():
        for t in tests:
            if t.location_code:
                location_set.add((slug, t.location_code, t.location_name or ""))

    # Build location records
    location_rows = []
    for lab_slug, loc_code, loc_name in location_set:
        lab_id = lab_id_map.get(lab_slug)
        if not lab_id:
            continue

        city_name = normalize_city(loc_code, lab_slug)
        city_id = city_id_map.get(city_name) if city_name else None

        # If city not in our map, try to add it
        if city_name and not city_id:
            try:
                result = client.table("cities").insert({
                    "name": city_name,
                    "state": CITY_STATE_MAP.get(city_name, ("Unknown", 3))[0],
                    "tier": CITY_STATE_MAP.get(city_name, ("Unknown", 3))[1],
                }).execute()
                if result.data:
                    city_id = result.data[0]["id"]
                    city_id_map[city_name] = city_id
            except Exception:
                pass

        location_rows.append({
            "lab_id": lab_id,
            "city_id": city_id,
            "location_code": loc_code,
            "location_name": loc_name[:200] if loc_name else None,
        })

    result = batch_upsert(client, "lab_locations", location_rows, "lab_id,location_code")
    print(f"  Lab locations: {result} rows")

    # Build lookup: (lab_slug, location_code) -> lab_location_id
    locs_result = client.table("lab_locations").select("id, lab_id, location_code").execute()
    # Need reverse lab_id -> slug
    slug_by_id = {v: k for k, v in lab_id_map.items()}
    loc_lookup = {}
    for r in locs_result.data:
        slug = slug_by_id.get(r["lab_id"])
        if slug:
            loc_lookup[(slug, r["location_code"])] = r["id"]

    return lab_id_map, city_id_map, loc_lookup


def step4_run_matching(all_tests: dict, loaders: dict):
    """Run test matching algorithm."""
    print("\n=== Step 4: Running Test Matching ===")

    # Get unique tests per lab for matching
    unique_tests: list[NormalizedLabTest] = []

    for slug, tests in all_tests.items():
        loader = loaders.get(slug)
        if hasattr(loader, "get_unique_tests"):
            unique = loader.get_unique_tests(tests)
        else:
            # For labs without dedup (Metropolis, Agilus, TRUSTlab)
            # Deduplicate by test_code
            seen = {}
            for t in tests:
                key = t.source_test_code or t.source_test_name
                if key not in seen:
                    seen[key] = t
            unique = list(seen.values())
            print(f"  {slug}: {len(unique)} unique from {len(tests)} total")

        unique_tests.extend(unique)

    print(f"\n  Total unique tests for matching: {len(unique_tests)}")

    matcher = TestMatcher()
    assignments = matcher.run(unique_tests)
    canonicals = matcher.get_canonical_tests()

    return matcher, assignments, canonicals


def step5_upload_canonical_tests(client, canonicals: list[dict], lab_id_map: dict):
    """Upload canonical tests and aliases to Supabase."""
    print("\n=== Step 5: Uploading Canonical Tests ===")

    # Get department IDs
    depts_result = client.table("departments").select("id, name").execute()
    dept_id_map = {r["name"]: r["id"] for r in depts_result.data}

    canonical_rows = []
    alias_rows = []

    for ct in tqdm(canonicals, desc="Preparing canonical tests"):
        slug = slugify(ct["name"])
        # Ensure unique slug by appending cluster_id
        slug = f"{slug}-{ct['cluster_id']}"

        row = {
            "name": ct["name"][:500],
            "slug": slug[:200],
            "test_type": None,
            "keywords": [k[:200] for k in ct["keywords"][:20]],
            "is_popular": ct["lab_count"] >= 3,
        }
        canonical_rows.append(row)

    # Upload in batches
    total = 0
    for i in tqdm(range(0, len(canonical_rows), BATCH_SIZE), desc="Uploading canonical tests"):
        batch = canonical_rows[i:i + BATCH_SIZE]
        try:
            result = client.table("canonical_tests").upsert(batch, on_conflict="slug").execute()
            total += len(result.data) if result.data else 0
        except Exception as e:
            print(f"  Error uploading batch {i}: {e}")
            # Try one by one
            for row in batch:
                try:
                    result = client.table("canonical_tests").upsert(row, on_conflict="slug").execute()
                    total += 1
                except Exception:
                    pass

    print(f"  Canonical tests: {total} rows uploaded")

    # Build canonical_test slug -> id lookup
    ct_result = client.table("canonical_tests").select("id, slug").execute()
    ct_slug_to_id = {r["slug"]: r["id"] for r in ct_result.data}

    # Map cluster_id -> canonical_test_id
    cluster_to_ct_id = {}
    for ct in canonicals:
        slug = f"{slugify(ct['name'])}-{ct['cluster_id']}"[:200]
        ct_id = ct_slug_to_id.get(slug)
        if ct_id:
            cluster_to_ct_id[ct["cluster_id"]] = ct_id

    # Upload aliases
    for ct in canonicals:
        ct_id = cluster_to_ct_id.get(ct["cluster_id"])
        if not ct_id:
            continue
        for keyword in ct["keywords"]:
            alias_rows.append({
                "canonical_test_id": ct_id,
                "alias": keyword[:500],
            })

    if alias_rows:
        alias_total = batch_insert(client, "test_aliases", alias_rows)
        print(f"  Aliases: {alias_total} rows uploaded")

    return cluster_to_ct_id


def step6_upload_lab_tests(client, all_tests: dict, matcher, lab_id_map: dict, loc_lookup: dict, cluster_to_ct_id: dict):
    """Upload all lab_test rows with canonical_test_id assignments."""
    print("\n=== Step 6: Uploading Lab Tests ===")

    # Build test_code -> cluster_id from assignments
    code_to_cluster: dict[str, int] = {}
    for key, cid in matcher.assignment.items():
        # key is "lab_slug:source_test_code"
        parts = key.split(":", 1)
        if len(parts) == 2:
            code_to_cluster[key] = cid

    total_uploaded = 0

    for slug, tests in all_tests.items():
        lab_id = lab_id_map.get(slug)
        if not lab_id:
            print(f"  WARNING: No lab_id for {slug}")
            continue

        print(f"\n  Uploading {slug}: {len(tests)} rows...")
        rows = []

        for t in tests:
            # Find canonical_test_id
            key = f"{t.lab_slug}:{t.source_test_code}"
            cluster_id = code_to_cluster.get(key)
            ct_id = cluster_to_ct_id.get(cluster_id) if cluster_id else None

            # Find lab_location_id
            loc_id = loc_lookup.get((t.lab_slug, t.location_code))

            # Compute discount
            discount = None
            if t.mrp and t.price and t.mrp > 0 and t.price < t.mrp:
                discount = round(((t.mrp - t.price) / t.mrp) * 100, 2)

            # Find match info
            member_info = None
            if cluster_id and cluster_id in matcher.clusters:
                for m in matcher.clusters[cluster_id]:
                    if m["lab_slug"] == t.lab_slug and m["source_test_code"] == t.source_test_code:
                        member_info = m
                        break

            row = {
                "lab_id": lab_id,
                "canonical_test_id": ct_id,
                "lab_location_id": loc_id,
                "source_test_code": t.source_test_code,
                "source_test_name": t.source_test_name[:500],
                "source_product_id": t.source_product_id,
                "price": float(t.price) if t.price else None,
                "mrp": float(t.mrp) if t.mrp else None,
                "discount_pct": discount,
                "test_type": t.test_type,
                "department_raw": t.department_raw,
                "methodology": t.methodology,
                "sample_type": t.sample_type,
                "sample_volume": t.sample_volume,
                "sample_container": t.sample_container,
                "fasting_required": t.fasting_required,
                "tat_text": t.tat_text,
                "tat_hours": t.tat_hours,
                "home_collection": t.home_collection,
                "nabl_accredited": t.nabl_accredited,
                "source_url": t.source_url,
                "match_confidence": member_info["confidence"] if member_info else None,
                "match_method": member_info["method"] if member_info else None,
                "is_active": True,
            }
            rows.append(row)

        # Upload in batches
        for i in tqdm(range(0, len(rows), BATCH_SIZE), desc=f"  {slug}"):
            batch = rows[i:i + BATCH_SIZE]
            try:
                result = client.table("lab_tests").insert(batch).execute()
                total_uploaded += len(result.data) if result.data else 0
            except Exception as e:
                err_str = str(e)
                if "duplicate" in err_str.lower() or "unique" in err_str.lower():
                    # Skip duplicates
                    for row in batch:
                        try:
                            result = client.table("lab_tests").insert(row).execute()
                            total_uploaded += 1
                        except Exception:
                            pass
                else:
                    print(f"  Error: {err_str[:200]}")

    print(f"\n  Total lab_tests uploaded: {total_uploaded}")


def main():
    if not SUPABASE_URL or "your-project" in SUPABASE_URL:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env")
        print("Also run the schema SQL in Supabase SQL Editor first!")
        sys.exit(1)

    client = get_client()
    print(f"Connected to Supabase: {SUPABASE_URL}")

    # Step 1: Seed reference data
    step1_seed_reference_data(client)

    # Step 2: Load CSVs
    all_tests, loaders = step2_load_csvs()

    # Step 3: Create lab locations
    lab_id_map, city_id_map, loc_lookup = step3_create_lab_locations(client, all_tests)

    # Step 4: Run matching
    matcher, assignments, canonicals = step4_run_matching(all_tests, loaders)

    # Print matching summary
    print(f"\n=== Matching Summary ===")
    print(f"  Total canonical tests: {len(canonicals)}")
    cross_lab = sum(1 for c in canonicals if c["lab_count"] >= 2)
    print(f"  Cross-lab matches (2+ labs): {cross_lab}")
    three_plus = sum(1 for c in canonicals if c["lab_count"] >= 3)
    print(f"  Available at 3+ labs: {three_plus}")
    four_plus = sum(1 for c in canonicals if c["lab_count"] >= 4)
    print(f"  Available at 4+ labs: {four_plus}")
    all_five = sum(1 for c in canonicals if c["lab_count"] >= 5)
    print(f"  Available at all 5 labs: {all_five}")

    # Step 5: Upload canonical tests
    cluster_to_ct_id = step5_upload_canonical_tests(client, canonicals, lab_id_map)

    # Step 6: Upload lab tests
    step6_upload_lab_tests(client, all_tests, matcher, lab_id_map, loc_lookup, cluster_to_ct_id)

    print("\n=== Pipeline Complete! ===")


if __name__ == "__main__":
    main()
