from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.utils.helper import validate_mandatory
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.reports.customer_sales_report.utils.customer_report_helper import (
    prepare_dashboard_context,
)
from app.reports.customer_sales_report.schemas.schemas import CustomerSalesReportRequest
from app.utils.constant import ROWS_PER_PAGE
from app.reports.customer_sales_report.utils.sql_query_helper import (
    SELECT,
    FROM_CLAUSE,
    GROUP_BY,
)
router = APIRouter(tags=["Customer Sales Report"], dependencies=[Depends(get_current_user)])

@router.post("/tableview")
def customer_sales_tableview(
    payload: CustomerSalesReportRequest,
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
        payload = apply_payload_permissions(payload, db, current_user)
        validate_mandatory(payload)
        ctx = prepare_dashboard_context(payload)
        offset = (page - 1) * ROWS_PER_PAGE
        base_sql = f"""
                {FROM_CLAUSE}
                {ctx['join_sql']}
                LEFT JOIN tbl_region r ON r.id = rt.region_id
                WHERE {ctx['where_sql']}
                {GROUP_BY}
                """
        query = f"""
                {SELECT}
                {ctx['value_expr']} AS value
                {base_sql}
                LIMIT {ROWS_PER_PAGE} OFFSET {offset}
                """
        rows = db.execute(text(query), ctx["params"]).fetchall()
        result = [dict(r._mapping) for r in rows]
        count_sql = f"SELECT COUNT(*)FROM (SELECT 1 {base_sql})AS counted_rows"
        total_rows = db.execute(text(count_sql), ctx["params"]).scalar()
        total_pages = (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
        base_url = str(request.url).split("?")[0]
        return {
                "pagination": {
                "total_rows": total_rows,
                "total_pages": total_pages,
                "current_page": page,
                "page_size": ROWS_PER_PAGE,
                "next_page": f"{base_url}?page={page + 1}" if page < total_pages else None,
                "prev_page": f"{base_url}?page={page - 1}" if page > 1 else None,
                },
                "data": result,
        }