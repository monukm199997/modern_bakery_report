from typing import Optional, List
from datetime import datetime

from pydantic import BaseModel

# Support both Pydantic v1 and v2.
try:
    from pydantic import field_validator  # Pydantic v2
    _PYDANTIC_V2 = True
except ImportError:  # pragma: no cover
    from pydantic import validator        # Pydantic v1
    _PYDANTIC_V2 = False


def _parse(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except (ValueError, TypeError):
        raise ValueError("as_of_date must be in YYYY-MM-DD format")


class SalesAchievementSchema(BaseModel):
    """
    Single-date input. The report is always month-to-date, so the caller
    supplies one snapshot date and the month range is derived from it:

        from_date  = 1st of as_of_date's month
        to_date    = as_of_date

    This guarantees from_date and to_date are always in the same month,
    which is what the target lookup and projection math require.
    """
    as_of_date: str
    company_ids: Optional[List[int]] = None
    region_ids: Optional[List[int]] = None
    route_ids: Optional[List[int]] = None

    # ---- derived values; the routes/helper read these unchanged ----

    @property
    def from_date(self) -> str:
        d = _parse(self.as_of_date)
        return d.replace(day=1).strftime("%Y-%m-%d")

    @property
    def to_date(self) -> str:
        return self.as_of_date

    # ---- validation ----

    if _PYDANTIC_V2:

        @field_validator("as_of_date")
        @classmethod
        def _check_format(cls, v: str) -> str:
            _parse(v)
            return v

    else:  # Pydantic v1

        @validator("as_of_date")
        def _check_format(cls, v):  # noqa: N805
            _parse(v)
            return v