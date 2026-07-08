from pydantic import BaseModel
from typing import Optional, List
from datetime import date

class NumericalDistributionRequest(BaseModel):
    from_date: date
    to_date: date
    drill_down_fields: Optional[List[str]] = None
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None

    