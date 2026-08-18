from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.reports.sales_team_dashboard.schemas.sales_team_dash_schema import SalesTeamDashboardSchema

from app.reports.sales_team_dashboard.utils.sales_team_dash_helper import (
    get_total_salesman,
    get_active_salesman,
    get_visit_customer,
    get_sales_period,
    get_visit_overview,
    get_Visit_heatmap,
    get_top_sales_by_salesman,
    get_top_customer_visit_salesman,
    get_region_performance,
    get_route_performance,
    get_sales_growth,
    get_customer_retention,
    get_orders_vs_invoices
)

router = APIRouter(tags=["Sales Team Dashboard"]) #dependencies= [Depends(get_current_user)])


@router.post("/kpis")
def kpis(
    payload: SalesTeamDashboardSchema, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    total_salesman = get_total_salesman(db)
    active_salesman = get_active_salesman(db)
    customer_visit = get_visit_customer(payload, db)
    sales_period = get_sales_period(payload, db)
    return {
        "total_salesman": total_salesman,
        "active_salesman": active_salesman,
        "customer_visit": customer_visit,
        "sales_period": sales_period,
        }

@router.post("/visit-overview")
def visit_overview(
    payload: SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_visit_overview(payload, db)

@router.post("/Visit-heatmap")
def visit_heatmap(
    payload:SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_Visit_heatmap(payload, db)

@router.post("/top-sales-by-salesman")
def top_sales_by_salesman(
    payload:SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_top_sales_by_salesman(payload, db)

@router.post("/top-customer-visit-by-salesman")
def top_customer_visit_by_salesman(
    payload:SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_top_customer_visit_salesman(payload, db)

@router.post("/region-performance")
def region_performance(
    payload:SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_region_performance(payload, db)

@router.post("/route-performance")
def route_performance(
    payload:SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_route_performance(payload, db)

@router.post("/sales-growh")
def sales_growth(
    payload:SalesTeamDashboardSchema, 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_sales_growth(payload, db)

@router.post("/customer-retention")
def customer_retention(
    payload: SalesTeamDashboardSchema,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_customer_retention(payload, db)

@router.post("/orders-vs-invoices")
def orders_vs_invoices(
    payload: SalesTeamDashboardSchema,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
  payload = apply_payload_permissions(payload, db, current_user)
  return get_orders_vs_invoices(payload, db)


