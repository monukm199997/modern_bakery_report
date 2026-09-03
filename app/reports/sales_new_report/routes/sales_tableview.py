from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_new_report.schemas.sales_schema import SalesReportRequest
from app.reports.sales_new_report.utils.sales_helper import prepare_sales_report_context
from app.common.apply_payload_permissions import apply_payload_permissions
from app.utils.constant import ROWS_PER_PAGE
from app.reports.sales_new_report.utils.sales_sql_query import JOINS_SQL

router = APIRouter(tags=["Sales New Report"], dependencies=[Depends(get_current_user)])

def get_sales_report_table(
    payload: SalesReportRequest, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1)
    ):
    ctx = prepare_sales_report_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE

    query = f"""
        SELECT
            {ctx["select_sql"]}
        {JOINS_SQL}
        {ctx["extra_join_sql"]}
        WHERE {ctx["where_sql"]}
        {ctx["group_by_sql"]}
        LIMIT :limit OFFSET :offset
    """
    params = {
        **ctx["params"],
        "limit": ROWS_PER_PAGE,
        "offset": offset,
    }

    rows = db.execute(text(query), params).mappings().all()
    count_query = f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                {ctx["select_sql"]}
            {JOINS_SQL}
            {ctx["extra_join_sql"]}
            WHERE {ctx["where_sql"]}
            {ctx["group_by_sql"]}
        ) AS count_query
    """

    total_rows = db.execute(text(count_query), ctx["params"]).scalar() or 0
    total_pages = (
        (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
        if total_rows > 0
        else 0
    )
    
    base_url = "/sales-new-tableview"
    return {
       
        "pagination": {
            "total_rows": total_rows,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": ROWS_PER_PAGE,
            "next_page": f"{base_url}?page={page + 1}" if page < total_pages else None,
            "prev_page": f"{base_url}?page={page - 1}" if page > 1 else None,
        },
        "search_type": payload.search_type,
        "drill_down_fields": payload.drill_down_fields or [],
        "data": [dict(row) for row in rows],
    }

@router.post("/sales-new-tableview")
def sales_report_tableview(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_sales_report_table(payload, db, page)