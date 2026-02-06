from pydantic import BaseModel
from typing import Optional


class NormalizedLabTest(BaseModel):
    lab_slug: str
    source_test_code: Optional[str] = None
    source_test_name: str
    source_product_id: Optional[str] = None
    price: Optional[float] = None
    mrp: Optional[float] = None
    test_type: str = "test"  # 'test' or 'package'
    department_raw: Optional[str] = None
    methodology: Optional[str] = None
    sample_type: Optional[str] = None
    sample_volume: Optional[str] = None
    sample_container: Optional[str] = None
    fasting_required: Optional[bool] = None
    tat_text: Optional[str] = None
    tat_hours: Optional[int] = None
    home_collection: Optional[bool] = None
    nabl_accredited: Optional[bool] = None
    source_url: Optional[str] = None
    location_code: Optional[str] = None
    location_name: Optional[str] = None
    aliases: list[str] = []
    raw_data: dict = {}
