import csv
from pipeline.models import NormalizedLabTest
from pipeline.ingest.base_loader import BaseLoader
from pipeline.ingest.tat_normalizer import parse_tat_minutes_to_hours


class NeubergLoader(BaseLoader):

    def get_lab_slug(self) -> str:
        return "neuberg"

    def load(self, csv_path: str) -> list[NormalizedLabTest]:
        results = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_name = (row.get("service_name") or "").strip()
                if not test_name:
                    continue

                # Price
                price = None
                price_str = (row.get("price") or "").strip()
                if price_str:
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass

                # MRP
                mrp = None
                mrp_str = (row.get("mrp") or "").strip()
                if mrp_str:
                    try:
                        mrp = float(mrp_str)
                    except ValueError:
                        pass

                # Test type
                is_pkg = (row.get("is_package") or "").strip().lower()
                test_type = "package" if is_pkg in ("true", "1") else "test"

                # Home collection
                hc_raw = (row.get("is_home_visit_applicable") or "").strip().lower()
                home_collection = hc_raw in ("true", "1")

                # TAT
                tat_minutes_str = (row.get("tat_minutes") or "").strip()
                tat_hours = parse_tat_minutes_to_hours(tat_minutes_str)

                # Parse aliases from alias_name (pipe-delimited)
                alias_raw = (row.get("alias_name") or "").strip()
                aliases = []
                if alias_raw:
                    aliases = [a.strip() for a in alias_raw.split("|") if a.strip()]

                # Active status
                is_active_raw = (row.get("is_active") or "").strip().lower()
                is_active = is_active_raw in ("true", "1")

                # Gender
                gender = (row.get("applicable_gender") or "").strip()

                results.append(NormalizedLabTest(
                    lab_slug="neuberg",
                    source_test_code=(row.get("service_code") or "").strip() or None,
                    source_test_name=test_name,
                    source_product_id=(row.get("service_id") or "").strip() or None,
                    price=price,
                    mrp=mrp if mrp else price,
                    test_type=test_type,
                    department_raw=None,  # Neuberg doesn't have department in CSV
                    methodology=None,
                    sample_type=(row.get("specimen_name") or "").strip() or None,
                    fasting_required=None,
                    tat_text=f"{tat_minutes_str} minutes" if tat_minutes_str else None,
                    tat_hours=tat_hours,
                    home_collection=home_collection,
                    location_code=(row.get("city_name") or "").strip() or None,
                    location_name=(row.get("city_name") or "").strip() or None,
                    aliases=aliases,
                    raw_data=dict(row),
                ))

        print(f"  Neuberg: loaded {len(results)} rows")
        return results

    def get_unique_tests(self, tests: list[NormalizedLabTest]) -> list[NormalizedLabTest]:
        """Deduplicate to one representative per service_code for matching."""
        by_code: dict[str, NormalizedLabTest] = {}
        for t in tests:
            code = t.source_test_code
            if not code:
                continue
            if code not in by_code:
                by_code[code] = t
            # Keep first occurrence (already has aliases)
        unique = list(by_code.values())
        print(f"  Neuberg: {len(unique)} unique service codes from {len(tests)} rows")
        return unique
