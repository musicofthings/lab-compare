"""Fix canonical_test_id linkage in lab_tests.

The issue: the matching algorithm assigns cluster IDs by (lab_slug, source_test_code),
but lab_tests has multiple rows per test_code (one per location). The pipeline only
linked the exact representative row, not all location variants.

Fix: For each (lab_slug, source_test_code) that has a canonical_test_id on ANY row,
propagate it to ALL rows with the same (lab_id, source_test_code).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tqdm import tqdm
from supabase import create_client
from pipeline.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BATCH_SIZE


def main():
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    print("Connected to Supabase")

    # Step 1: Get all lab_tests that DO have a canonical_test_id
    print("\nStep 1: Fetching linked lab_tests...")
    linked = []
    offset = 0
    while True:
        result = client.table("lab_tests") \
            .select("lab_id, source_test_code, canonical_test_id, match_confidence, match_method") \
            .not_.is_("canonical_test_id", "null") \
            .not_.is_("source_test_code", "null") \
            .range(offset, offset + 999) \
            .execute()
        if not result.data:
            break
        linked.extend(result.data)
        offset += 1000
        if len(result.data) < 1000:
            break

    print(f"  Found {len(linked)} linked rows")

    # Build lookup: (lab_id, source_test_code) -> (canonical_test_id, confidence, method)
    linkage_map = {}
    for r in linked:
        key = (r["lab_id"], r["source_test_code"])
        if key not in linkage_map:
            linkage_map[key] = {
                "canonical_test_id": r["canonical_test_id"],
                "match_confidence": r["match_confidence"],
                "match_method": r["match_method"],
            }

    print(f"  Unique (lab_id, test_code) pairs with links: {len(linkage_map)}")

    # Step 2: Also build cross-lab linkage via source_test_name matching
    # Get all canonical_tests and their names
    print("\nStep 2: Fetching canonical tests for name-based linkage...")
    canonicals = []
    offset = 0
    while True:
        result = client.table("canonical_tests") \
            .select("id, name, keywords") \
            .range(offset, offset + 999) \
            .execute()
        if not result.data:
            break
        canonicals.extend(result.data)
        offset += 1000
        if len(result.data) < 1000:
            break

    print(f"  Found {len(canonicals)} canonical tests")

    # Build name -> canonical_test_id lookup (case-insensitive)
    name_to_ct = {}
    for ct in canonicals:
        name_to_ct[ct["name"].strip().lower()] = ct["id"]
        if ct.get("keywords"):
            for kw in ct["keywords"]:
                if kw:
                    name_to_ct[kw.strip().lower()] = ct["id"]

    print(f"  Name lookup entries: {len(name_to_ct)}")

    # Step 3: Fetch ALL unlinked lab_tests and try to link them
    # NOTE: We always fetch from offset 0 when rows get fixed (they drop out of
    # the IS NULL filter). We only advance the offset when a page has zero fixable rows.
    print("\nStep 3: Fetching unlinked lab_tests...")
    unlinked_count = 0
    fixed_count = 0
    batch_updates = []
    pages_processed = 0

    offset = 0
    while True:
        result = client.table("lab_tests") \
            .select("id, lab_id, source_test_code, source_test_name") \
            .is_("canonical_test_id", "null") \
            .range(offset, offset + 999) \
            .execute()

        if not result.data:
            break

        page_fixed = 0
        for row in result.data:
            unlinked_count += 1

            # Try linkage by (lab_id, test_code)
            key = (row["lab_id"], row["source_test_code"])
            link_info = linkage_map.get(key)

            if not link_info:
                # Try by exact name match
                name_lower = row["source_test_name"].strip().lower()
                ct_id = name_to_ct.get(name_lower)
                if ct_id:
                    link_info = {
                        "canonical_test_id": ct_id,
                        "match_confidence": 0.85,
                        "match_method": "name_propagation",
                    }

            if link_info:
                batch_updates.append({
                    "id": row["id"],
                    **link_info,
                })
                fixed_count += 1
                page_fixed += 1

        # Flush batch updates periodically
        if len(batch_updates) >= 500:
            _flush_updates(client, batch_updates)
            batch_updates = []

        pages_processed += 1

        # If we fixed rows on this page, don't advance offset — those rows
        # will disappear from the NULL filter, so the next page at same offset
        # will have new rows. Only advance if nothing was fixable on this page.
        if page_fixed == 0:
            offset += 1000

        if len(result.data) < 1000:
            break

        if pages_processed % 10 == 0:
            print(f"  Processed {pages_processed} pages, fixed {fixed_count} so far...")

    # Flush remaining
    if batch_updates:
        _flush_updates(client, batch_updates)

    print(f"\n  Total unlinked: {unlinked_count}")
    print(f"  Fixed: {fixed_count}")
    print(f"  Still unlinked: {unlinked_count - fixed_count}")

    # Verify
    result_linked = client.table("lab_tests").select("id", count="exact").not_.is_("canonical_test_id", "null").limit(0).execute()
    result_null = client.table("lab_tests").select("id", count="exact").is_("canonical_test_id", "null").limit(0).execute()
    print(f"\n  Final state:")
    print(f"    Linked: {result_linked.count}")
    print(f"    Unlinked: {result_null.count}")


def _flush_updates(client, updates):
    """Update lab_tests rows with canonical_test_id."""
    for i in range(0, len(updates), 50):
        batch = updates[i:i + 50]
        for upd in batch:
            row_id = upd.pop("id")
            try:
                client.table("lab_tests").update(upd).eq("id", row_id).execute()
            except Exception as e:
                pass
            upd["id"] = row_id  # restore


if __name__ == "__main__":
    main()
