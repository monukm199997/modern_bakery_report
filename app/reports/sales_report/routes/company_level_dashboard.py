from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context
from app.utils.helper import detect_level
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions

router = APIRouter(tags=["Sales Report"])


@router.post("/company-wise-sales")
def company_level_dashboard(
    payload: SalesReportRequest, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    level = detect_level(payload)

    if level != "company":
        raise HTTPException(status_code=400, detail="Company level required")

    query = f"""
        WITH filtered_sales AS (
            SELECT
                ih.company_id,
                {ctx['value_expr']} AS value
            FROM invoice_headers ih
            JOIN invoice_details id
                ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.company_id
        )
        SELECT
            c.company_name,
            SUM(value) AS value
        FROM filtered_sales fs
        JOIN tbl_company c
            ON c.id = fs.company_id
        GROUP BY c.company_name
        ORDER BY value DESC
        """
    print(ctx["params"])
    rows = db.execute(text(query), ctx["params"]).fetchall()
    charts = [dict(row._mapping) for row in rows]
    return {"charts": charts}


@router.post("/company-trendline-sales")
def company_trendline_sales(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    level = detect_level(payload)

    if level != "company":
        raise HTTPException(status_code=400, detail="company level required")

    out = {"granularity": ctx["granularity"], "charts": []}

    query = f"""
        SELECT
            {ctx['period_label_sql']} AS period,
            c.company_name,
            {ctx['value_expr']} as value
        FROM invoice_headers ih
        JOIN invoice_details id ON id.header_id = ih.id
        JOIN tbl_company c ON c.id = ih.company_id
        LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY period, c.company_name, {ctx['order_by_sql']}
        ORDER BY {ctx['order_by_sql']}, c.company_name
    """

    rows = db.execute(text(query), ctx["params"]).fetchall()

    out["charts"] = [dict(r._mapping) for r in rows]

    return out

@router.post("/region-wise-sale")
def region_wise_sale(payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    level = detect_level(payload)

    if level != "company":
        raise HTTPException(status_code=400, detail="company level required")
    
    query = f"""
            SELECT
            r.region_name,
            {ctx['value_expr']} as value
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

@router.post("/top-route")
def top_route(payload: SalesReportRequest,
    db:Session=Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)

    query = f"""
            SELECT
            rt.route_name,
            {ctx['value_expr']} as value
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY rt.route_name
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/top-salesman")
def top_salesman(payload:SalesReportRequest,
    db:Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            s.name as salesman_name,
            rt.route_name,
            {ctx['value_expr']} as value
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
            {ctx['join_sql']}
            JOIN salesman s ON s.id = ih.salesman_id 
            WHERE {ctx['where_sql']}
            GROUP BY s.name, rt.route_name
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result


@router.post("/top-items")
def top_items(payload:SalesReportRequest,
    db:Session=Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            i.name as item_name,
            {ctx['value_expr']} as value
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            JOIN items i ON i.id = id.item_id
            LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY i.name
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result


@router.post("/top-customers")
def top_customers(payload:SalesReportRequest,
    db:Session=Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            ac.name as customer_name,
            rt.route_name,
            ac.contact_no,
            {ctx['value_expr']} as value
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            JOIN agent_customers ac ON ac.id = ih.customer_id
            LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ac.name,rt.route_name,ac.contact_no
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return result








