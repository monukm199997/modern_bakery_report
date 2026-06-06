from pydantic import BaseModel
from typing import Optional, List

class VehiclesRequest(BaseModel):
    from_date : str
    to_date : str
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None


