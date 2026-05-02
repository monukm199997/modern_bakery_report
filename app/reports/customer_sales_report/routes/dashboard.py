from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.reports.customer_sales_report.schemas.schemas import CustomerSalesReportRequest
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.reports.customer_sales_report.utils.customer_report_helper import prepare_dashboard_context
from app.reports.customer_sales_report.utils.sql_query_helper import (
CUSTOMER_SALES_KPIS_SQL,
BASE_SQL, 
OPTIONAL_JOINS_SQL,
OPTIONAL_JOINS_SQL_1
)

router = APIRouter(tags=["Customer Sales Report"])

@router.post("/customer-sales-kpis")
def customer_sales_kpis(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    out = {"kpis":{}}
    query = f"""
            SELECT COALESCE({ctx["value_expr"]}, 0) AS total_sales
            {BASE_SQL}
            """
    result = db.execute(text(query), ctx["params"]).scalar()
    out["kpis"]["total_sales"] = result
    if not result:
        return {"message": "No data found for the given criteria"}
    rows = db.execute(text(CUSTOMER_SALES_KPIS_SQL), ctx["params"]).fetchone()
    if not rows:
        return {"message": "No data found for the given criteria"}
    out["kpis"]["total_customers"] = rows.total_customers
    out["kpis"]["active_sales_customers"] = rows.active_sales_customers
    out["kpis"]["inactive_sales_customers"] = rows.inactive_sales_customers
    return out


@router.post("/customer-sales-trend")
def customer_sales_trend(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
             SELECT
            {ctx['period_label_sql']} AS period,
            {ctx['value_expr']} AS value
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY period, {ctx['order_by_sql']}
            ORDER BY {ctx['order_by_sql']}
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
            return{"message": "No data found for the given criteria"}
    result = [dict(r._mapping) for r in rows]
    return {"trend": result}


@router.post("/Channel-wise Sales")
def channel_wise_sales(payload:CustomerSalesReportRequest, db:Session= Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
                oc.outlet_channel_code || '-' || oc.outlet_channel AS channel_name,
                {ctx['value_expr']} AS value,
                ROUND(
                    ({ctx['value_expr']} /
                     NULLIF(SUM({ctx['value_expr']}) OVER (),0))::numeric * 100,
                    2
                ) AS percentage
            {BASE_SQL}
            {OPTIONAL_JOINS_SQL}
            WHERE {ctx['where_sql']}
            GROUP BY oc.outlet_channel, oc.outlet_channel_code
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"message": "No data found for the given criteria"}
    result = [dict(r._mapping) for r in rows]
    return {"channel_wise_sales": result}


@router.post("/customer-category-wise-sales")
def customer_category_wise_sales(payload:CustomerSalesReportRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    query = f"""
            SELECT
            cc.customer_category_code || '-' ||  cc.customer_category_name AS customer_category_name,
                {ctx['value_expr']} AS value,
                ROUND(
                    ({ctx['value_expr']}/
                     NULLIF(SUM({ctx['value_expr']}) OVER (),0))::numeric  * 100,
                    2
                ) AS percentage
            {BASE_SQL}
            {OPTIONAL_JOINS_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY cc.customer_category_name, cc.customer_category_code
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"message": "No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return {"customer_category_wise_sales": result}


@router.post("/top-10-items")
def top_10_items(payload:CustomerSalesReportRequest, db: Session = Depends(get_db)):

    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
                it.name AS item,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            JOIN items it ON it.id = id.item_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY it.name
            ORDER BY value DESC
            LIMIT 10
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"message": "No data found for the given criteria"}
    result = [dict(r._mapping) for r in rows]
    return {"top_10_items": result}


@router.post("/top-10-customers")
def top_10_customers(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
                cst.osa_code || ' - ' || cst.name AS customers_name,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            JOIN agent_customers cst ON cst.id = ih.customer_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY cst.id, cst.osa_code, cst.name
            ORDER BY value DESC
            LIMIT 10
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria"}
    result = [dict(r._mapping) for r in rows]
    return {"top_10_customers": result}


@router.post("/top-10-channels")
def top_10_channels(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
               oc.outlet_channel_code || '-' || oc.outlet_channel AS channel_name,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            {OPTIONAL_JOINS_SQL_1}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY oc.outlet_channel, oc.outlet_channel_code
            ORDER BY value DESC
            LIMIT 10
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping) for r in rows]
    return {"top_10_channels": result}


@router.post("/top-10-customer-categories")
def top_10_customer_categories(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
                cc.customer_category_code || '-' ||  cc.customer_category_name AS customer_category_name,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            {OPTIONAL_JOINS_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY cc.customer_category_name,cc.customer_category_code
            ORDER BY value DESC
            LIMIT 10
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping) for r in rows]
    return{"top_10_customer_categories": result}
