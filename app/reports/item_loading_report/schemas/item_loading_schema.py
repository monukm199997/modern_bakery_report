from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date

class ItemLoadingRequest(BaseModel):
    from_date: date
    to_date: date
    search_type: Literal["amount", "quantity"] = "amount"
    drill_down_fields: Optional[List[Literal["item", "route"]]] = None
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    supervisor_ids: Optional[List[int]] = None