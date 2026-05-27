from pydantic import BaseModel
from typing import Optional, List

class SalesAchievementSchema(BaseModel):
    from_date: str
    to_date: str
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None