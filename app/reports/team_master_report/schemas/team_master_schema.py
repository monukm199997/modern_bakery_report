from pydantic import BaseModel, typing
from typing import List, Optional

class TeamMasterRequest(BaseModel):
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
