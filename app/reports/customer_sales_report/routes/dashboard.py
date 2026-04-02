from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.reports.customer_sales_report.schemas.schemas import CustomerSalesReportRequest
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.reports.customer_sales_report.utils.customer_report_helper import prepare_dashboard_context

router = APIRouter(tags=["Customer Sales Report Dashboard"])

@router.post("customer-sales-kpis")
def customer_sales_kpis(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    out = {"kpis":{}}
    query = f"""
            SELECT COALESCE({ctx["value_expr"]}, 0) AS total_sales
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            {ctx["join_sql"]}
            WHERE {ctx["where_sql"]}
            """
    result = db.execute(text(query), ctx["params"]).scalar()
    out["kpis"]["total_sales"] = result
    return out



@router.post("/customer-sales-trend")
def customer_sales_trend(payload:CustomerSalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    query = f"""
             SELECT
            {ctx['period_label_sql']} AS period,
            {ctx['value_expr']} AS value
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY period, {ctx['order_by_sql']}
            ORDER BY {ctx['order_by_sql']}
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
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
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            JOIN agent_customers cst ON cst.id = ih.customer_id
            JOIN outlet_channel oc ON oc.id = cst.outlet_channel_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY oc.outlet_channel, oc.outlet_channel_code
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
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
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            JOIN agent_customers cst ON cst.id = ih.customer_id
            JOIN customer_categories cc ON cc.id = cst.category_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY cc.customer_category_name, cc.customer_category_code
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping)for r in rows]
    return {"customer_category_wise_sales": result}