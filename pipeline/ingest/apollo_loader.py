import csv
from pipeline.models import NormalizedLabTest
from pipeline.ingest.base_loader import BaseLoader
from pipeline.ingest.tat_normalizer import parse_tat_to_hours


class ApolloLoader(BaseLoader):

    def get_lab_slug(self) -> str:
        return "apollo"

    def load(self, csv_path: str) -> list[NormalizedLabTest]:
        results = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_name = (row.get("test_name") or "").strip()
                if not test_name:
                    continue

                # Price (MRP only)
                mrp = None
                mrp_str = (row.get("mrp") or "").strip()
                if mrp_str:
                    try:
                        mrp = float(mrp_str)
                    except ValueError:
                        pass

                # Test type: has package_id -> package
                package_id = (row.get("package_id") or "").strip()
                test_type = "package" if package_id and package_id != "0" and package_id != "" else "test"

                # TAT
                tat_text = (row.get("tat") or "").strip()
                tat_hours = parse_tat_to_hours(tat_text)

                # Status
                status = (row.get("status") or "").strip().lower()
                is_active = status != "inactive"

                results.append(NormalizedLabTest(
                    lab_slug="apollo",
                    source_test_code=(row.get("test_code") or "").strip() or None,
                    source_test_name=test_name,
                    source_product_id=(row.get("id") or "").strip() or None,
                    price=mrp,  # Apollo only has MRP
                    mrp=mrp,
                    test_type=test_type,
                    department_raw=(row.get("department_name") or "").strip() or None,
                    methodology=(row.get("methodology") or "").strip() or None,
                    sample_type=(row.get("sampleType_name") or "").strip() or None,
                    sample_container=(row.get("container") or "").strip() or None,
                    fasting_required=None,
                    tat_text=tat_text or None,
                    tat_hours=tat_hours,
                    location_code=(row.get("city_id") or "").strip() or None,
                    location_name=(row.get("centre_name") or "").strip() or None,
                    raw_data=dict(row),
                ))

        print(f"  Apollo: loaded {len(results)} rows")
        return results

    def get_unique_tests(self, tests: list[NormalizedLabTest]) -> list[NormalizedLabTest]:
        """Deduplicate to one representative per test_code for matching."""
        by_code: dict[str, NormalizedLabTest] = {}
        for t in tests:
            code = t.source_test_code
            if not code:
                continue
            if code not in by_code:
                by_code[code] = t
            elif t.location_code == "GRL0001":
                # Prefer Global Reference Lab as representative
                by_code[code] = t
        unique = list(by_code.values())
        print(f"  Apollo: {len(unique)} unique test codes from {len(tests)} rows")
        return unique
