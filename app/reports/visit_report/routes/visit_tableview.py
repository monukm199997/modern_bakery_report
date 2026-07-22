from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.reports.visit_report.schemas.visit_schema import VisitPlanRequest
from app.reports.visit_report.utils.visit_helper import prepare_dashboard_context
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.reports.visit_report.utils.visit_sql_query import BASE_SQL_JOIN, SELECT_SQL
from app.utils.constant import ROWS_PER_PAGE

router = APIRouter(tags=["Visit Report"])


@router.post("/visit-tableview")
def visit_tableview(
    payload: VisitPlanRequest,
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_dashboard_context(payload)

    base_sql = f"""
           {BASE_SQL_JOIN}
            WHERE {ctx['where_sql']}
        """
    count_sql = f"""
            SELECT COUNT(*)
            {base_sql}
        """
    total_rows = db.execute(text(count_sql), ctx["params"]).scalar() or 0
    offset = (page - 1) * ROWS_PER_PAGE
    ctx["params"]["limit"] = ROWS_PER_PAGE
    ctx["params"]["offset"] = offset

    query = f"""
            SELECT
               {SELECT_SQL}
            {base_sql}
            ORDER BY date 
            LIMIT :limit OFFSET :offset
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
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
