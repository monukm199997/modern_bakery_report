from typing import List, Optional
from pydantic import BaseModel  



class SalesReportRequest(BaseModel):
    from_date: str
    to_date: str
    search_type: str = "quantity"                
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None
    item_category_ids: Optional[List[int]] = None
    item_ids: Optional[List[int]] = None
    customer_channel_ids: Optional[List[int]] = None
    display_quantity: Optional[str] = None 



class ExportRequest(BaseModel):
    from_date: str
    to_date: str
    search_type: str = "quantity"                
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None
    item_category_ids: Optional[List[int]] = None
    item_ids: Optional[List[int]] = None
    customer_channel_ids: Optional[List[int]] = None
    display_quantity: Optional[str] = None 
 