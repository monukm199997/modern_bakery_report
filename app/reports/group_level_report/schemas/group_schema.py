from typing import Optional, List
from pydantic import BaseModel, field_validator


class GroupLevelReportRequest(BaseModel):
    from_date: str
    to_date: str
    search_type: str = "both"                              
    drill_down_fields: Optional[List[str]] = None
    company_ids: Optional[List[int]] = None
    customer_groups_ids: Optional[List[int]] = None
    customer_groups_1_ids: Optional[List[str]] = None
    customer_groups_2_ids: Optional[List[str]] = None 

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, value):
        value = value.lower()
        if value not in ("amount", "quantity", "both"):
            raise ValueError("search_type must be amount, quantity, or both")
        return value

    @field_validator("drill_down_fields")
    @classmethod
    def validate_drill_down_fields(cls, value):
        if value:
            for field in value:
                if field.lower() not in ("customer", "item"):
                    raise ValueError(
                        "drill_down_fields may only be 'customer' or 'item'"
                    )
        return value
    


class GroupLevelTableRequest(GroupLevelReportRequest):
    
    page: int = 1
    page_size: int = 50
 
    @field_validator("page")
    @classmethod
    def validate_page(cls, value):
        if value < 1:
            raise ValueError("page must be >= 1")
        return value
 
    @field_validator("page_size")
    @classmethod
    def validate_page_size(cls, value):
        if value < 1:
            raise ValueError("page_size must be >= 1")
        if value > 500:
            raise ValueError("page_size must be <= 500")
        return value