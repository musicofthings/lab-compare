import csv
from pipeline.models import NormalizedLabTest
from pipeline.ingest.base_loader import BaseLoader
from pipeline.ingest.tat_normalizer import parse_tat_to_hours


class MetropolisLoader(BaseLoader):

    def get_lab_slug(self) -> str:
        return "metropolis"

    def load(self, csv_path: str) -> list[NormalizedLabTest]:
        results = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_name = (row.get("Test Name") or "").strip()
                if not test_name:
                    continue

                # Parse price
                price_str = (row.get("Price") or "").strip()
                price = None
                if price_str:
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass

                # Parse fasting
                fasting_raw = (row.get("Fasting Req?") or "").strip().upper()
                fasting = True if fasting_raw == "YES" else (False if fasting_raw == "NO" else None)

                # Parse NABL
                nabl_raw = (row.get("NABL") or "").strip().upper()
                nabl = True if nabl_raw == "Y" else (False if nabl_raw == "N" else None)

                # Test type
                test_type_raw = (row.get("Test Type") or "").strip().upper()
                test_type = "package" if test_type_raw == "PKG" else "test"

                # TAT
                tat_text = (row.get("Reported On") or "").strip()
                tat_hours = parse_tat_to_hours(tat_text)

                results.append(NormalizedLabTest(
                    lab_slug="metropolis",
                    source_test_code=(row.get("Test Code") or "").strip(),
                    source_test_name=test_name,
                    price=price,
                    mrp=price,  # Metropolis has single price = MRP
                    test_type=test_type,
                    department_raw=None,  # Metropolis PDF doesn't have department
                    methodology=(row.get("Method") or "").strip() or None,
                    sample_type=None,
                    sample_volume=(row.get("Sample Quantity") or "").strip() or None,
                    fasting_required=fasting,
                    tat_text=tat_text or None,
                    tat_hours=tat_hours,
                    nabl_accredited=nabl,
                    location_code="DELHI",
                    location_name="Delhi",
                    raw_data=dict(row),
                ))

        print(f"  Metropolis: loaded {len(results)} tests")
        return results
