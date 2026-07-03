from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, model_validator


class SalesComparisonRequest(BaseModel):
    current_from_date: date
    current_to_date: date
    previous_from_date: date
    previous_to_date: date

    # amount = revenue, quantity = volume, both = revenue + volume
    search_type: Literal["amount", "quantity", "both"] = "amount"

    # allowed: customer, item, salesman, route, supervisor, customer_group, channel
    drill_down_fields: Optional[List[str]] = None

    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None
    customer_groups_ids: Optional[List[int]] = None
    super_wiser_ids: Optional[List[int]] = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.current_from_date > self.current_to_date:
            raise ValueError("current_from_date cannot be greater than current_to_date")
        if self.previous_from_date > self.previous_to_date:
            raise ValueError("previous_from_date cannot be greater than previous_to_date")
        return self
