from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.reports.visit_report.schemas.visit_schema import VisitPlanRequest
from app.reports.visit_report.utils.visit_helper import prepare_dashboard_context
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.utils.constant import ROWS_PER_PAGE

router = APIRouter(tags=["Visit Report"], dependencies=[Depends(get_current_user)])

@router.post("/visit-tableview")
def visit_tableview(payload: VisitPlanRequest, request: Request, page: int = Query(1, ge=1), db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    base_sql = f"""
            FROM visit_plan vp
            LEFT JOIN agent_customers ac ON ac.id = vp.customer_id
            LEFT JOIN tbl_route rt ON rt.id = vp.route_id
            LEFT JOIN salesman s ON s.id = vp.salesman_id
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
                TO_CHAR(vp.visit_start_time, 'YYYY-MM-DD') AS date,
                ac.osa_code AS customer_code,
                ac.name AS customer_name,
                ac.contact_no AS customer_contact,
                rt.route_code AS route_code,
                rt.route_name AS route_name,
                s.osa_code AS salesman_code,
                s.name AS salesman_name,
                TO_CHAR(vp.visit_start_time, 'HH24:MI:SS') AS visit_start_time,
                TO_CHAR(vp.visit_end_time, 'HH24:MI:SS') AS visit_end_time,
                 COALESCE(
                    (vp.visit_end_time - vp.visit_start_time)::text,
                    '-'
                ) AS time_spent,

                COALESCE(
                        (
                            vp.visit_start_time -
                            LAG(vp.visit_end_time) OVER (
                                PARTITION BY vp.salesman_id
                                ORDER BY vp.visit_start_time
                            )
                        )::text,
                        '-'
                    ) AS idle_time,
                ac.latitude AS customer_latitude,
                ac.longitude AS customer_longitude,
                vp.latitude,
                vp.longitude,
                vp.shop_status,
                vp.remark AS reason
            {base_sql}
            ORDER BY date 
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
