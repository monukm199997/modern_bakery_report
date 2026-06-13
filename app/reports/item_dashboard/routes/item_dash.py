from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.item_dashboard.schemas.item_dash_schema import ItemDashboardRequest
from app.reports.item_dashboard.utils.item_dash_helper import (
    total_items,
    active_items,
    total_stock,
    inventory_value,
    out_of_stock,
    stocked_skus,
    low_stock,
    over_stock,
    fast_movers,
    dead_stock,
    get_stock_health_route,
    get_route_stock_distribution,
    get_purchase_trend,
    get_sales_trend,
    choose_granularity,
    get_fast_slow_movers,
    get_sales_categories,
    get_item_aging,
    get_low_stock_alert,
    get_top_selling_items,
    get_reorder_forecast,
    get_consumption_trend,
)
router = APIRouter(tags=["Item Dashboard"], dependencies= [Depends(get_current_user)])

@router.post("/kpis")
def item_dashboard(payload: ItemDashboardRequest, db:Session = Depends(get_db)):
    total = total_items(db)
    active = active_items(db)
    stocked = stocked_skus(payload, db)
    stock = total_stock(payload, db)
    inventory = inventory_value(payload, db)
    out_stock = out_of_stock(payload, db)
    low = low_stock(payload, db)
    over = over_stock(payload, db)
    fast = fast_movers(payload, db)
    dead = dead_stock(payload, db)

    rate = 0
    if total:
        rate = round(active * 100 / total, 1)

    return {
        "total_items": total,
        "stocked_skus": stocked,
        "active_items": active,
        "total_stock": stock,
        "inventory_value": inventory,
        "active_rate": rate,
        "out_of_stock": out_stock,
        "low_stock": low,
        "overstocked": over,
        "fast_movers": fast,
        "dead_stock": dead,
    }

@router.post("composition")
def get_composition(payload:ItemDashboardRequest, db:Session = Depends(get_db)):
    
    total = total_items(db)
    active = active_items(db)
    inactive = total - active

    active_pct = 0
    inactive_pct = 0

    active_pct = round(active * 100 / total, 1)
    inactive_pct = round(inactive * 100 / total, 1)

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "active_pct": active_pct,
        "inactive_pct": inactive_pct
    }

@router.post("/stock-health-route")
def stock_health_route(
    payload: ItemDashboardRequest, db:Session = Depends(get_db), page: int = 1, page_size: int = 10):

    return get_stock_health_route(payload, db, page, page_size)

@router.post("/route-stock-distribution")
def route_stock_distribution(payload: ItemDashboardRequest, db:Session = Depends(get_db), limit: int = 100):
    return get_route_stock_distribution(payload, db, limit)

@router.post("/stock-movement-trend")
def stock_movement_trend(payload: ItemDashboardRequest, db:Session = Depends(get_db)):
    purchase_rows = get_purchase_trend(payload, db)
    sales_rows = get_sales_trend(payload, db)
    result={}

    for row in purchase_rows:
        result[row["period"]]={
        "sort_date":row["sort_date"],
        "purchase":row["purchase"],
        "sales":0
        }

    for row in sales_rows:
        if row["period"] not in result:
            result[row["period"]]={
            "sort_date":row["sort_date"],
            "purchase":0,
            "sales":row["sales"]
            }
        else:
            result[row["period"]]["sales"]=row["sales"]

    ordered=sorted(result.items(),key=lambda x:x[1]["sort_date"])

    data = []
    for period, values in ordered:

        data.append({
            "period": period,
            "purchase": values["purchase"],
            "sales": values["sales"]

    })

    granularity, _, _ = choose_granularity(
    payload.from_date,
    payload.to_date,
    "ih.invoice_date"
    )

    return {
        "granularity": granularity,
        "data": data
    }

@router.post("/fast-slow-movers")
def fast_slow_movers(payload: ItemDashboardRequest, db:Session = Depends(get_db), limit: int = 10):
  return get_fast_slow_movers(payload, db, limit)

@router.post("/sales-category")
def sales_category(payload: ItemDashboardRequest, db:Session = Depends(get_db), page:int=1, page_size:int=10):
   return get_sales_categories(payload, db, page, page_size)

@router.post("/item-aging")
def item_aging(payload:ItemDashboardRequest, db:Session = Depends(get_db)):
   return get_item_aging(payload, db)

@router.post("/low-stock-alerts")
def low_stock_alerts(
    payload: ItemDashboardRequest,
    db: Session = Depends(get_db),
    page: int = 1,
    page_size: int = 10,
    threshold: int = 10
):
 return get_low_stock_alert(payload, db, page, page_size, threshold)

@router.post("/top-selling-items")
def top_selling_items(
    payload: ItemDashboardRequest,
    db:Session = Depends(get_db),
    page: int = 1,
    page_size: int = 10
):
    return get_top_selling_items(payload, db, page, page_size)

@router.post("/reorder-forecast")
def reorder_forecast(
    payload: ItemDashboardRequest,
    db:Session = Depends(get_db),
    page:int=1,
    page_size:int=5
):
    return get_reorder_forecast(payload, db, page, page_size)

@router.post("/consumption-trend")
def consumption_trend(payload: ItemDashboardRequest, db:Session = Depends(get_db)):
  return get_consumption_trend(payload, db)

