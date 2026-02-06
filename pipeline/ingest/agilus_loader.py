import csv
import re
from pipeline.models import NormalizedLabTest
from pipeline.ingest.base_loader import BaseLoader
from pipeline.ingest.tat_normalizer import parse_tat_to_hours


class AgilusLoader(BaseLoader):

    def get_lab_slug(self) -> str:
        return "agilus"

    def load(self, csv_path: str) -> list[NormalizedLabTest]:
        results = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_name = (row.get("test_name") or "").strip()
                if not test_name:
                    continue

                # Clean name: strip " Package in New delhi" suffix
                test_name_clean = re.sub(
                    r"\s+Package\s+in\s+New\s*delhi\s*$", "", test_name, flags=re.IGNORECASE
                ).strip()

                # Price
                price = None
                price_str = (row.get("price") or "").strip()
                if price_str:
                    try:
                        price = float(price_str)
                    except ValueError:
                        pass

                # market_price is always 0, so mrp = price
                mrp = price

                # Test type
                product_type = (row.get("product_type") or "").strip().upper()
                test_type = "package" if product_type == "PACKAGE" else "test"

                # Home collection
                hc_raw = (row.get("home_collection") or "").strip().lower()
                home_collection = hc_raw in ("true", "1", "yes")

                # TAT
                tat_text = (row.get("tat") or "").strip()
                tat_hours = parse_tat_to_hours(tat_text)

                results.append(NormalizedLabTest(
                    lab_slug="agilus",
                    source_test_code=(row.get("test_code") or "").strip() or None,
                    source_test_name=test_name_clean,
                    source_product_id=(row.get("product_id") or "").strip() or None,
                    price=price,
                    mrp=mrp,
                    test_type=test_type,
                    department_raw=(row.get("department") or "").strip() or None,
                    sample_type=(row.get("sample_type") or "").strip() or None,
                    sample_volume=(row.get("sample_volume") or "").strip() or None,
                    sample_container=(row.get("sample_container") or "").strip() or None,
                    fasting_required=None,
                    tat_text=tat_text or None,
                    tat_hours=tat_hours,
                    home_collection=home_collection,
                    source_url=(row.get("full_url") or "").strip() or None,
                    location_code="NEW_DELHI",
                    location_name="New Delhi",
                    raw_data=dict(row),
                ))

        print(f"  Agilus: loaded {len(results)} tests")
        return results
