import csv
from pipeline.models import NormalizedLabTest
from pipeline.ingest.base_loader import BaseLoader
from pipeline.ingest.tat_normalizer import parse_tat_to_hours


class TRUSTlabLoader(BaseLoader):

    def get_lab_slug(self) -> str:
        return "trustlab"

    def load(self, csv_path: str) -> list[NormalizedLabTest]:
        results = []

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                test_name = (row.get("test_name") or "").strip()
                if not test_name:
                    continue

                # Prices
                mrp = None
                mrp_str = (row.get("mrp") or "").strip()
                if mrp_str:
                    try:
                        mrp = float(mrp_str)
                    except ValueError:
                        pass

                l2l_price = None
                l2l_str = (row.get("l2l_price") or "").strip()
                if l2l_str:
                    try:
                        l2l_price = float(l2l_str)
                    except ValueError:
                        pass

                # Use MRP as the consumer price for comparison
                price = mrp

                # Test type
                dept = (row.get("departments") or "").strip()
                test_type = "package" if dept.lower() == "package" else "test"

                # Fasting
                fasting_raw = (row.get("fasting") or "").strip().lower()
                fasting = True if "required" in fasting_raw and "not" not in fasting_raw else (
                    False if "not required" in fasting_raw else None
                )

                # Home collection
                hc_raw = (row.get("home_collection") or "").strip().lower()
                home_collection = hc_raw in ("true", "1", "yes")

                # NABL
                nabl_raw = (row.get("nabl") or "").strip().upper()
                nabl = True if nabl_raw == "Y" else (False if nabl_raw == "N" else None)

                # TAT
                tat_text = (row.get("report_tat") or "").strip()
                tat_hours = parse_tat_to_hours(tat_text)

                # Active
                is_active_raw = (row.get("is_active") or "").strip().lower()

                # Expand comma-separated locations into separate entries
                location_raw = (row.get("location") or "").strip()
                locations = [loc.strip() for loc in location_raw.split(",") if loc.strip()] if location_raw else ["Begumpet"]

                for loc in locations:
                    results.append(NormalizedLabTest(
                        lab_slug="trustlab",
                        source_test_code=(row.get("test_code") or "").strip() or None,
                        source_test_name=test_name,
                        source_product_id=(row.get("id") or "").strip() or None,
                        price=price,
                        mrp=mrp,
                        test_type=test_type,
                        department_raw=dept or None,
                        methodology=(row.get("test_methodology") or "").strip() or None,
                        sample_type=(row.get("sample_type") or "").strip() or None,
                        sample_volume=(row.get("sample_volume") or "").strip() or None,
                        sample_container=(row.get("sample_container") or "").strip() or None,
                        fasting_required=fasting,
                        tat_text=tat_text or None,
                        tat_hours=tat_hours,
                        home_collection=home_collection,
                        nabl_accredited=nabl,
                        location_code=loc,
                        location_name=loc,
                        raw_data=dict(row),
                    ))

        print(f"  TRUSTlab: loaded {len(results)} rows (expanded from locations)")
        return results
