from pydantic import BaseModel,  model_validator
from typing import Optional, List, Literal
import re

class SalesDashboardRequest(BaseModel):
    select_date:str
    search_type:str = "quantity"
    view_type: Literal["month", "year"]

    @model_validator(mode="after")
    def validate_select_date(self):

        if self.view_type == "year":
            if not re.fullmatch(r"\d{4}", self.select_date):
                raise ValueError(
                    "For year view, select_date must be in YYYY format"
                )

        if self.view_type == "month":
            if not re.fullmatch(r"\d{4}-\d{2}", self.select_date):
                raise ValueError(
                    "For month view, select_date must be in YYYY-MM format"
                )

        return self


class SalesDashboardKpisRequest(BaseModel):
    from_date: str
    to_date: str
    search_type:str = "quantity"
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None


class SalesDashboardPerfomanceRequest(SalesDashboardKpisRequest):
    segment_by: Literal[
        "customer_channel",
        "product_category",
        "sales_region",
        "route"
    ] = "customer_channel"

    limit: int = 10


