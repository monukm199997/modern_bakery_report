from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class InventoryMovementRequest(BaseModel):
    from_date: date
    to_date: date
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    channel_ids: Optional[List[int]] = None
    