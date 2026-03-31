from pydantic import BaseModel
from typing import Optional,List

class LoadUnloadReportRequest(BaseModel):
    from_date: str
    to_date: str
    search_type:str = "quantity"
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None
    display_quantity: Optional[str] = None