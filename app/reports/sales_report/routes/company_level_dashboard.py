from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.reports.sales_report.utils.sql_query_helper import COMPANY_SALES
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions

router = APIRouter(tags=["Sales Report"])


@router.post("/company-wise-sales")
def company_wise_sales(
    payload: SalesReportRequest, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
        WITH filtered_sales AS (
            SELECT
                ih.company_id,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.company_id
        )
        {COMPANY_SALES}
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(row._mapping) for row in rows]
    return {"company wise sales": result}


@router.post("/company-trendline-sales")
def company_trendline_sales(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    out = {"granularity": ctx["granularity"]}
    query = f"""
        SELECT
            {ctx['period_label_sql']} AS period,
            c.company_name,
            {ctx['value_expr']} as value
        {BASE_SQL}
        LEFT JOIN tbl_company c ON c.id = ih.company_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY period, c.company_name, {ctx['order_by_sql']}
        ORDER BY {ctx['order_by_sql']}, c.company_name
    """
    print(ctx["params"])
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    out["company trendline sales"] = [dict(r._mapping) for r in rows]
    return out


@router.post("/region-wise-sale")
def region_wise_sale(payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            r.region_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            {ctx['join_sql']}
            JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY r.region_name
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
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
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY rt.route_name
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
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
            {BASE_SQL}
            {ctx['join_sql']}
            JOIN salesman s ON s.id = ih.salesman_id 
            WHERE {ctx['where_sql']}
            GROUP BY s.name, rt.route_name
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
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
            {BASE_SQL}
            JOIN items i ON i.id = id.item_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY i.name
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
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
            {BASE_SQL}
            JOIN agent_customers ac ON ac.id = ih.customer_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ac.name,rt.route_name,ac.contact_no
            ORDER BY value DESC
            LIMIT 10;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result








