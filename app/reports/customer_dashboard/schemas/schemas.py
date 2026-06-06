from pydantic import BaseModel
from typing import Optional, List

class CustomerDashRequest(BaseModel):
    from_date: str
    to_date: str
    search_type:str = "quantity"
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None