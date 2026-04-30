from fastapi import APIRouter, Depends, HTTPException
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context
from app.utils.helper import detect_level
from app.reports.sales_report.utils.sql_query_helper import VISITED_CUSTOMER_PERFORMANCE
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
    level = detect_level(payload)
    if level != "region":
        raise HTTPException(status_code=400, detail="User have not permission for this region")

    query = f"""
            SELECT
            r.region_name,
            {ctx['value_expr']} AS value,
            0 AS total_return
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            {ctx['join_sql']}
            JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY r.region_name
            ORDER BY value DESC
            """
    print(ctx["params"])
    rows = db.execute(text(query), ctx["params"]).fetchall()
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
    level = detect_level(payload)
    if level != "region":
        raise HTTPException(status_code=400, detail="region level required")
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
                FROM invoice_headers ih
                JOIN invoice_details id ON id.header_id = ih.id
                JOIN items it ON it.id = id.item_id
                LEFT JOIN item_uoms iu
                    ON iu.item_id = id.item_id
                    AND iu.uom_id = id.uom
                {ctx['join_sql']}
                JOIN tbl_region r ON r.id = rt.region_id
                WHERE {ctx['where_sql']}
                GROUP BY r.region_name, it.name
            )
            SELECT region_name, item_name, value
            FROM region_item_sales
            WHERE rn = 1
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
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
    level = detect_level(payload)
    if level != "region":
        raise HTTPException(status_code=400, detail="region level required")
    
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
    level = detect_level(payload)
    if level != "region":
        raise HTTPException(status_code=400, detail="region level required")
    query = f"""
            SELECT
                {ctx['period_label_sql']} AS period,
                r.region_name,
                {ctx['value_expr']} AS value
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            {ctx['join_sql']}
            JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY period, r.region_name,{ctx['order_by_sql']}
            ORDER BY {ctx['order_by_sql']}, r.region_name
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result
