from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.customer_dashboard.schemas.schemas import CustomerDashRequest
from app.reports.customer_dashboard.utils.cust_dash_helper import (
    get_trend_line,
    get_active_customers,
    get_new_customers,
    get_at_risk_customers,
    get_inactive_customers,
    get_avg_sales_value,
    get_customer_growth,
    get_customer_coverage,
    get_sales_returns,
    customer_health,
    customer_health_histogram,
    get_risk_customers,
    get_inactive_customer,
    get_top_customers,
    get_region_customers,
    get_route_customers,
    get_channel_customers,
    get_categories_customers,
    get_top_100_customers,
    get_outstanding_recovery,
)

router = APIRouter(tags=["Customer Dashboard"], dependencies=[Depends(get_current_user)])

@router.post("/sales-trend-line")
def sales_trend_line(payload: CustomerDashRequest, db: Session = Depends(get_db)):
    return get_trend_line(payload, db)
@router.post("/region-customer")
def region_customer(payload: CustomerDashRequest, db: Session = Depends(get_db)):
    return get_region_customers(payload, db)

@router.post("/route-customer")
def route_customer(payload: CustomerDashRequest, db: Session = Depends(get_db)):
    return get_route_customers(payload, db)

@router.post("/channel-customer")
def channel_customer(payload: CustomerDashRequest, db: Session = Depends(get_db)):
    return get_channel_customers(payload, db)

@router.post("/category-customer")
def category_customer(payload: CustomerDashRequest, db: Session = Depends(get_db)):
    return get_categories_customers(payload, db)

@router.post("/customer-dashboard-kpis")
def customer_dashboard_kpis(payload: CustomerDashRequest, db:Session = Depends(get_db)):
    return {
        "total_active_customers": get_active_customers(payload, db),
        "new_customers": get_new_customers(payload, db),
        "at_risk_customers": get_at_risk_customers(payload, db),
        "inactive_customers": get_inactive_customers(payload, db),
        "avg_sales_value": get_avg_sales_value(payload,db),
    }

@router.post("/customer-growth")
def customer_growth(payload: CustomerDashRequest, db:Session = Depends(get_db)):
    return {
        "growth": get_customer_growth(payload, db),
        "coverage": get_customer_coverage(payload, db),
        "sales_returns": get_sales_returns(payload, db)
    }

@router.post("/customer-health")
def customer_health_dashboard(payload: CustomerDashRequest, db:Session = Depends(get_db)):

    summary = customer_health(payload, db)
    histogram = customer_health_histogram(payload, db)

    return {
        "healthy": summary["healthy"],
        "warning": summary["warning"],
        "critical": summary["critical"],
        "histogram": histogram
    }

@router.post("/smart-alerts")
def smart_alerts(payload: CustomerDashRequest, db:Session = Depends(get_db) ):
    alerts = []
    inactive_count = get_inactive_customer(payload, db)

    if inactive_count:
        alerts.append({
            "level": "info",
            "text": f"{inactive_count:,} customers inactive for 7+ days",
            "count": inactive_count
        })

    risk_count = get_risk_customers(payload, db)

    if risk_count:
        alerts.append({
            "level": "warning",
            "text": f"{risk_count:,} high outstanding-risk customers",
            "count": risk_count
        })

    return alerts

@router.post("/top-customers")
def top_customers(payload: CustomerDashRequest,db:Session = Depends(get_db)):
    return get_top_customers(payload, db)

@router.post("/top-100-customers")
def top_100_customers(
    payload: CustomerDashRequest,
    db:Session = Depends(get_db),
    page: int = 1,
    page_size: int = 100
):
    return get_top_100_customers(payload, db, page, page_size)

@router.post("/outstanding-recovery")
def outstanding_recovery(
    payload: CustomerDashRequest,
    db:Session = Depends(get_db),
    page: int = 1,
    page_size: int = 10
):
    return  get_outstanding_recovery(payload, db, page, page_size)