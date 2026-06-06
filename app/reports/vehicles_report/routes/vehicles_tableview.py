from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.reports.vehicles_report.schemas.vehicles_schema import VehiclesRequest
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.utils.constant import ROWS_PER_PAGE
from app.reports.vehicles_report.utils.vehicles_helper import prepare_dashboard_context


router = APIRouter(tags=["vehicles_report"], dependencies=[Depends(get_current_user)])

@router.post("/vehicle-tableview")
def vehicle_tableview(payload:VehiclesRequest, request: Request, page: int = Query(1, ge=1), db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    base_sql = f"""
            FROM tbl_trip tt
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
        """
    count_sql = f"""
            SELECT COUNT(*)
            {base_sql}
        """
    total_rows = db.execute(text(count_sql), ctx['params']).scalar() or 0
    offset = (page - 1) * ROWS_PER_PAGE
    ctx['params']["limit"] = ROWS_PER_PAGE
    ctx['params']["offset"] = offset

    query = f"""
        SELECT
            trip_date,
            trip_code,
            start_odometer,
            end_odometer,
            distance_traveled
        {base_sql}
        ORDER BY trip_date
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    total_pages = (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
    base_url = str(request.url).split("?")[0]

    return {
        "total_rows": total_rows,
        "total_pages": total_pages,
        "current_page": page,
        "next_page": f"{base_url}?page={page + 1}" if page < total_pages else None,
        "previous_page": f"{base_url}?page={page - 1}" if page > 1 else None,
        "rows": result,
    }

