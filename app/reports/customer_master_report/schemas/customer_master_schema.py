from pydantic import BaseModel
from typing import Optional, List

class CustomerMasterRequest(BaseModel):
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
