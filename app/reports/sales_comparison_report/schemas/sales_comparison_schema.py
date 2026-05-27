from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import date


class SalesComparisonRequest(BaseModel):
    report_by: Literal["day", "month", "year"]
    selected_date: date
    search_type: Literal["quantity", "amount"] = "quantity"

    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None
