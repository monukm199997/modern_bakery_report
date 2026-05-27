from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)
from app.reports.sales_comparison_report.utils.sales_comparison_helper import (
    get_periods,
    prepare_dashboard_context,
    compute_comparison,
    format_period_label,
)

router = APIRouter(tags=["Sales Comparison Report"], dependencies = [Depends(get_current_user)])

TOP_N = 5

@router.post("/kpis")
def kpis(
    payload: SalesComparisonRequest,
    db: Session = Depends(get_db),
):
    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    kpi_sql = f"""
        SELECT
            COALESCE({current_expr}, 0) AS current_sales,
            COALESCE({prev_expr},    0) AS previous_sales
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {where_sql}
    """
    kpi_row = db.execute(text(kpi_sql), params).first()
    kpi = compute_comparison(
        kpi_row._mapping["current_sales"] if kpi_row else 0,
        kpi_row._mapping["previous_sales"] if kpi_row else 0,
    )
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label = format_period_label(payload.report_by, prev_from, prev_to)

    return {
        "period": {
            "current": current_label,
            "previous": prev_label,
        },
        "kpi": kpi,
    }

@router.post("/top-items")
def top_items(payload: SalesComparisonRequest, db:Session = Depends(get_db)):

    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    top_items_sql = f"""
        SELECT
            i.name AS item,
            COALESCE({current_expr}, 0) AS current_sales,
            COALESCE({prev_expr},    0) AS previous_sales
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        LEFT JOIN items i ON i.id = id.item_id
        WHERE {where_sql}
        GROUP BY i.name
        ORDER BY current_sales DESC NULLS LAST
        LIMIT :top_n
    """
    rows = db.execute(text(top_items_sql), {**params, "top_n": TOP_N})
    top_items = [
        {
            "item": r._mapping["item"],
            **compute_comparison(r._mapping["current_sales"], r._mapping["previous_sales"]),
        }
        for r in rows
    ]
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label = format_period_label(payload.report_by, prev_from, prev_to)

    return  {
        "period": {
            "current": current_label,
            "previous": prev_label,
        },
        "top_items": top_items,
    }

@router.post("/top-categories")
def top_categories(payload:SalesComparisonRequest, db:Session = Depends(get_db)):

    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )
    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    top_categories_sql = f"""
        SELECT
            ic.category_name AS category,
            COALESCE({current_expr}, 0) AS current_sales,
            COALESCE({prev_expr},    0) AS previous_sales
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        WHERE {where_sql}
        GROUP BY ic.category_name
        ORDER BY current_sales DESC NULLS LAST
        LIMIT :top_n
    """
    rows = db.execute(text(top_categories_sql), {**params, "top_n": TOP_N})
    top_categories = [
        {
            "category": r._mapping["category"],
            **compute_comparison(r._mapping["current_sales"], r._mapping["previous_sales"]),
        }
       
        for r in rows
    ]
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label = format_period_label(payload.report_by, prev_from, prev_to)

    return {
        "period": {
            "current": current_label,
            "previous": prev_label,
        },
        "top_categories": top_categories,
    }

@router.post("/top-salesman")
def top_salesman(payload: SalesComparisonRequest, db:Session = Depends(get_db)):

    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    top_salesmen_sql = f"""
        SELECT
            s.osa_code || '-' || s.name AS salesman,
            COALESCE({current_expr}, 0) AS current_sales,
            COALESCE({prev_expr},    0) AS previous_sales
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {where_sql}
        GROUP BY s.osa_code, s.name
        ORDER BY current_sales DESC NULLS LAST
        LIMIT :top_n
    """
    rows = db.execute(text(top_salesmen_sql), {**params, "top_n": TOP_N})
    top_salesman = [
        {
            "salesman": r._mapping["salesman"],
            **compute_comparison(r._mapping["current_sales"], r._mapping["previous_sales"]),
        }
        for r in rows
    ]
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label = format_period_label(payload.report_by, prev_from, prev_to)

    return  {
        "period": {
            "current": current_label,
            "previous": prev_label,
        },
        "top_salesmen": top_salesman,
    }

@router.post("/top-routes")
def top_routes(payload:SalesComparisonRequest, db:Session = Depends(get_db)):

    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    top_routes_sql = f"""
        SELECT
            rt.route_name AS route,
            COALESCE({current_expr}, 0) AS current_sales,
            COALESCE({prev_expr},    0) AS previous_sales
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {where_sql}
        GROUP BY rt.route_name
        ORDER BY current_sales DESC NULLS LAST
        LIMIT :top_n
    """
    rows = db.execute(text(top_routes_sql), {**params, "top_n": TOP_N})
    top_routes = [
        {
            "route": r._mapping["route"],
            **compute_comparison(r._mapping["current_sales"], r._mapping["previous_sales"]),
        }
        for r in rows
    ]
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label = format_period_label(payload.report_by, prev_from, prev_to)

    return {
        "period": {
            "current": current_label,
            "previous": prev_label,
        },
        "top_routes": top_routes,
    }

@router.post("/trenline")
def trend_line(payload:SalesComparisonRequest, db:Session = Depends(get_db)):

    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]
    
    if payload.report_by == "month":
        bucket_expr = "EXTRACT(DAY FROM ih.invoice_date)::int"
        bucket_label_expr = "TO_CHAR(ih.invoice_date, 'DD')"
    elif payload.report_by == "year":
        bucket_expr = "EXTRACT(MONTH FROM ih.invoice_date)::int"
        bucket_label_expr = "TO_CHAR(ih.invoice_date, 'Mon')"
    else:  
        bucket_expr = "EXTRACT(EPOCH FROM ih.invoice_date)::bigint"
        bucket_label_expr = "TO_CHAR(ih.invoice_date, 'DD Mon YYYY')"

    trend_sql = f"""
        SELECT
            {bucket_expr} AS bucket_key,
            MIN({bucket_label_expr}) AS bucket_label,
            COALESCE({current_expr}, 0) AS current_sales,
            COALESCE({prev_expr},    0) AS previous_sales
       {BASE_SQL}
       LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {where_sql}
        GROUP BY bucket_key
        ORDER BY bucket_key
    """
    trend = [
        {
            "bucket": r._mapping["bucket_label"],
            **compute_comparison(r._mapping["current_sales"], r._mapping["previous_sales"]),
        }
        for r in db.execute(text(trend_sql), params)
    ]

    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label = format_period_label(payload.report_by, prev_from, prev_to)

    return {
        "period": {
            "current": current_label,
            "previous": prev_label,
        },
        "trend": trend,
    }
