from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.group_level_report.schemas.group_schema import GroupLevelReportRequest
from app.reports.group_level_report.utils.group_level_helper import (
    get_group_level_rows,
    build_group_level_excel,
)

router = APIRouter(tags=["Group Level Report"])#, dependencies=[Depends(get_current_user)])


@router.post("/group-level/export")
def group_level_export(
    payload: GroupLevelReportRequest,
    db: Session = Depends(get_db),
):
    rows = get_group_level_rows(payload, db)
    return build_group_level_excel(rows)