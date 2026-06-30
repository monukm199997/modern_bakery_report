from pydantic import BaseModel
from typing import Optional, List


class VehiclesPermitRequest(BaseModel):
    company_ids: Optional[List[int]] = None
    region_ids: Optional[list[int]] = None