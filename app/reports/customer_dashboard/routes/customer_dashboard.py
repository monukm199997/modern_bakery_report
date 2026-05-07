from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.reports.customer_dashboard.schemas.schemas import CustomerDashboardRequest
from app.utils.helper import validate_mandatory, choose_granularity, quantity_expr_sql
from app.reports.customer_dashboard.utils.cust_dash_helper import get_invoice_date
from app.dependencies.auth import get_current_user
from app.reports.customer_dashboard.utils.query_helper import (
    TOTAL_CUSTOMER_IN_CATEGORY,
    TOTAL_CUSTOMER_IN_CHANNEL,
    TOTAL_CUSTOMER_IN_REGION,
    TOTAL_CUSTOMER_IN_ROUTE,
    TOTAL_PENDING_CUSTOMER,
    TOTAL_NEW_CUSTOMER,
    TOTAL_CUSTOMER,
    BASE_SQL,
)

router = APIRouter(tags=["Customer Dashboard"], dependencies=[Depends(get_current_user)])
quantity = quantity_expr_sql()


@router.get("/kpis")
def customer_dash_kpis(db: Session = Depends(get_db)):
    query = f"""
            SELECT
                {TOTAL_CUSTOMER},
                {TOTAL_PENDING_CUSTOMER},
                {TOTAL_NEW_CUSTOMER}     
            """
    rows = db.execute(text(query)).fetchone()
    result = {
        "total_customer": rows.total_customer,
        "total_pending_customer": rows.total_pending_customer,
        "total_new_customer": rows.total_new_customer,
    }
    return result


@router.post("/sales-trend-line")
def sales_trend_line(payload: CustomerDashboardRequest, db: Session = Depends(get_db)):
    validate_mandatory(payload)
    where_fragments, params = get_invoice_date(payload)
    invoice_date = " AND ".join(where_fragments)
    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )
    query = f"""
        SELECT
                {period_label_sql} AS period_label,
                {quantity} AS value
            {BASE_SQL}
            WHERE {invoice_date}
            GROUP BY {period_label_sql},{order_by_sql}
            ORDER BY {order_by_sql}
        """
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return {"granularity": granularity, "sales_trend_line": result}


@router.post("/top-customer-trendline")
def top_customer_trendline(
    payload: CustomerDashboardRequest, db: Session = Depends(get_db)
):
    validate_mandatory(payload)
    where_fragments, params = get_invoice_date(payload)
    invoice_date = " AND ".join(where_fragments)
    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )

    query = f"""
            SELECT
                {period_label_sql} AS period_label,
                ac.name AS customer_name,
                {quantity} AS value
            {BASE_SQL}
            LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
            WHERE {invoice_date}
            GROUP BY {period_label_sql},{order_by_sql}, ac.name
            ORDER BY value DESC
            LIMIT 20
        """
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return {"granularity": granularity, "top_customer_trend_line": result}


@router.post("/region-customer")
def region_customer(payload: CustomerDashboardRequest, db: Session = Depends(get_db)):
    validate_mandatory(payload)
    where_fragments, params = get_invoice_date(payload)
    invoice_date = " AND ".join(where_fragments)

    query = f"""
            SELECT
            {TOTAL_CUSTOMER_IN_REGION}
            WHERE {invoice_date}
            GROUP BY r.region_name
            ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/route-customer")
def route_customer(payload:CustomerDashboardRequest, db:Session = Depends(get_db)):
    validate_mandatory(payload)
    where_fragments, params = get_invoice_date(payload)
    invoice_date = " AND ".join(where_fragments)

    query = f"""
        SELECT
        {TOTAL_CUSTOMER_IN_ROUTE}
        WHERE {invoice_date}
        GROUP BY rt.route_name
        ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/channel-customer")
def channel_customer(payload:CustomerDashboardRequest, db:Session = Depends(get_db)):
    validate_mandatory(payload)
    where_fragments, params = get_invoice_date(payload)
    invoice_date = " AND ".join(where_fragments)

    query = f"""
            SELECT
            {TOTAL_CUSTOMER_IN_CHANNEL}
            WHERE {invoice_date}
            GROUP BY oc.outlet_channel
            ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/category-customer")
def category_customer(payload:CustomerDashboardRequest, db:Session = Depends(get_db)):
    validate_mandatory(payload)
    where_fragments, params = get_invoice_date(payload)
    invoice_date = " AND ".join(where_fragments)

    query = f"""
            SELECT
            {TOTAL_CUSTOMER_IN_CATEGORY}
            WHERE {invoice_date}
            GROUP BY cc.customer_category_name
            ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

@router.post("/top-customer")
def top_customer(payload:CustomerDashboardRequest, db:Session = Depends(get_db)):
    pass
# TOP 100 customer query sales, exchange ...