from pydantic import BaseModel
from typing import List, Optional

class CustomerSalesReportRequest(BaseModel):
    from_date: str
    to_date: str
    search_type: str = "quantity"                
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    display_quantity: Optional[str] = None



class CustomerSalesReportExportRequest(BaseModel):
    from_date: str
    to_date: str
    search_type: str = "quantity"              # quantity | amount
    view_type: str = "default"                 # default | detail
    display_quantity: Optional[str] = "without_free_good"           # with_free_good | without_free_good
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
