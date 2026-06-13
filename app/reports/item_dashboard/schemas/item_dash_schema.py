from pydantic import BaseModel
from typing import Optional, List

class ItemDashboardRequest(BaseModel):
    from_date: str
    to_date: str
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    item_category_ids: Optional[List[int]] = None
    item_ids: Optional[List[int]] = None