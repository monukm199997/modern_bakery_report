from fastapi import APIRouter, Depends, HTTPException
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context
from app.reports.sales_report.utils.sql_query_helper import VISITED_CUSTOMER_PERFORMANCE, REGION_CONTRIBUTION_TOP_ITEMS
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions

router = APIRouter(tags=["Sales Report"])


@router.post("/region-performance")
def region_perfomance(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)

    query = f"""
            SELECT
            r.region_name,
            {ctx['value_expr']} AS value,
            0 AS total_return
            {BASE_SQL}
            {ctx['join_sql']}
            JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY r.region_name
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/region-contribution-top-items")
def region_contribution_top_items(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
        WITH region_item_sales AS (
                SELECT
                    r.region_name,
                    it.name AS item_name,
                    {ctx['value_expr']} AS value,
                    ROW_NUMBER() OVER (
                        PARTITION BY r.region_name
                        ORDER BY {ctx['value_expr']} DESC
                    ) AS rn
                {BASE_SQL}
                JOIN items it ON it.id = id.item_id
                {ctx['join_sql']}
                JOIN tbl_region r ON r.id = rt.region_id
                WHERE {ctx['where_sql']}
                GROUP BY r.region_name, it.name
            )
            {REGION_CONTRIBUTION_TOP_ITEMS}
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/region-wise-visited-customer-performance")
def region_wise_visited_customer_performance(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    
    rows = db.execute(text(VISITED_CUSTOMER_PERFORMANCE), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/region-trendline-sales")
def region_trendline_sales(
    payload: SalesReportRequest, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
    ):
    
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)

    query = f"""
            SELECT
                {ctx['period_label_sql']} AS period,
                r.region_name,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            {ctx['join_sql']}
            JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY period, r.region_name,{ctx['order_by_sql']}
            ORDER BY {ctx['order_by_sql']}, r.region_name
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result
