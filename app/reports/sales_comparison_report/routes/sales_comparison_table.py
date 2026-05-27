from fastapi import APIRouter, Query, Request, Depends, HTTPException
from sqlalchemy import text
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.utils.constant import ROWS_PER_PAGE
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)
from app.reports.sales_comparison_report.utils.sales_comparison_helper import (
    get_periods,
    prepare_dashboard_context,
    compute_comparison,
    format_period_label
)

router = APIRouter(tags=["Sales Comparison Report"], dependencies = [Depends(get_current_user)])

@router.post("/sales-comparison-table")
def sales_comparison_table(
    payload: SalesComparisonRequest,
    request: Request,
    db:Session = Depends(get_db),
    page: int = Query(1, ge=1),
):

    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    base_from = f"""
        {BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {where_sql}
    """

    count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT i.code, i.name
            {base_from}
            GROUP BY i.code, i.name
        ) t
    """
    total_rows = db.execute(text(count_sql), params).scalar() or 0

    offset = (page - 1) * ROWS_PER_PAGE
    params["limit"] = ROWS_PER_PAGE
    params["offset"] = offset

    data_sql = f"""
        SELECT
            i.code AS item_code,
            i.name AS item,
            {current_expr} AS current_sales,
            {prev_expr}    AS previous_sales
        {base_from}
        GROUP BY i.code, i.name
        ORDER BY i.code, i.name
        LIMIT :limit OFFSET :offset
    """
    rows = [dict(r._mapping) for r in db.execute(text(data_sql), params)]
    
    total_pages = (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
    base_url = str(request.url).split("?")[0]
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label    = format_period_label(payload.report_by, prev_from, prev_to)
    # current_label = f"{current_from:%b %d, %Y} – {current_to:%b %d, %Y}"
    # prev_label = f"{prev_from:%b %d, %Y} – {prev_to:%b %d, %Y}"

    data = [
        {
            "item_code": r["item_code"],
            "item": r["item"],
            "current_period": current_label,
            "previous_period": prev_label,
            **compute_comparison(r["current_sales"], r["previous_sales"]),
        }
        for r in rows
    ]

    return {
        "total_rows": total_rows,
        "total_pages": total_pages,
        "current_page": page,
        "next_page": f"{base_url}?page={page + 1}" if page < total_pages else None,
        "previous_page": f"{base_url}?page={page - 1}" if page > 1 else None,
        "data": data,
    }
