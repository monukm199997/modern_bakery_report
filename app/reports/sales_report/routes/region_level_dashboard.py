from fastapi import APIRouter,Depends,HTTPException
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context
from app.common.helper import detect_level
from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(tags=["Sales Dashboard - region level"])

@router.post("/region-performance")
def region_perfomance(payload:SalesReportRequest,db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    level = detect_level(payload)
    if level != "region":
        raise HTTPException(status_code=400, detail="region level required")
    
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
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result

    
@router.post("/region-contribution-top-items")
def region_contribution_top_items(payload:SalesReportRequest, db:Session=Depends(get_db)):
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
    rows = db.execute(text(query),ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result
    
            
@router.post("/region-wise-visited-customer-performance")
def region_wise_visited_customer_performance(payload:SalesReportRequest, db:Session=Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    level = detect_level(payload)

    total_customers =""" WITH total_customers AS (
                    SELECT DISTINCT
                        r.id AS region_id,
                        r.region_name,
                        ac.id AS customer_id
                    FROM agent_customers ac
                    JOIN tbl_route rt ON rt.id = ac.route_id
                    JOIN tbl_region r ON r.id = rt.region_id
                    WHERE
                        ac.status = 1
                        AND r.id = ANY(:region_ids)
                )"""
    
    visited_customers = """
                    visited_customers AS (
                    SELECT DISTINCT
                        r.id AS region_id,
                        ih.customer_id
                    FROM invoice_headers ih
                    JOIN invoice_details id ON id.header_id = ih.id
                    JOIN agent_customers ac ON ac.id = ih.customer_id
                    JOIN tbl_route rt ON rt.id = ih.route_id
                    JOIN tbl_region r ON r.id = rt.region_id
                    WHERE
                        ac.status = 1
                        AND id.item_total > 0
                        AND ih.invoice_date BETWEEN :from_date AND :to_date
                        AND r.id = ANY(:region_ids)
                )"""
    
    query =f"""
            {total_customers},
            {visited_customers}
            SELECT
                    t.region_name,
                    COUNT(DISTINCT v.customer_id) AS visited_customers,
                    COUNT(DISTINCT t.customer_id) AS total_customers,
                    ROUND(
                        (COUNT(DISTINCT v.customer_id)::numeric
                        / NULLIF(COUNT(DISTINCT t.customer_id), 0)) * 100,
                        2
                    ) AS visited_percentage
                FROM total_customers t
                LEFT JOIN visited_customers v
                    ON t.customer_id = v.customer_id
                    AND t.region_id = v.region_id
                GROUP BY t.region_id, t.region_name
                ORDER BY t.region_name;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result


@router.post("/region-trendline-sales")
def region_trendline_sales(payload:SalesReportRequest,db:Session=Depends(get_db)):
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
    result = [dict(r._mapping)for r in rows]
    return result