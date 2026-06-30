from typing import Optional, List
from pydantic import BaseModel, field_validator


class SalesReportRequest(BaseModel):
    from_date: str
    to_date: str

    # amount, quantity, both
    search_type: str = "both"

    # customer, item, salesman, route, supervisor, customer_group, channel
    drill_down_fields: Optional[List[str]] = None

    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None
    salesman_ids: Optional[List[int]] = None
    item_category_ids: Optional[List[int]] = None
    item_ids: Optional[List[int]] = None
    customer_channel_ids: Optional[List[int]] = None
    customer_ids: Optional[List[int]] = None
    customer_groups_ids: Optional[List[int]] = None
    super_wiser_ids: Optional[List[int]] = None

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, value):
        value = value.lower()
        if value not in ["amount", "quantity", "both"]:
            raise ValueError("search_type must be amount, quantity, or both")
        return value