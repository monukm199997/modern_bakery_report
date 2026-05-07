from pydantic import BaseModel

class CustomerDashboardRequest(BaseModel):
    from_date:str
    to_date:str