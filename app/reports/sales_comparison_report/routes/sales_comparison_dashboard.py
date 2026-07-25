from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.common.apply_payload_permissions import apply_payload_permissions
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)
from app.reports.sales_comparison_report.utils.sales_comparison_helper import (
    BASE_FROM_SQL,
    build_comparison_metric_columns,
    build_filters,
    compute_comparison,
)


router = APIRouter(tags=["Sales Comparison Report"], dependencies=[Depends(get_current_user)])

TOP_N = 10


def _run_group_query(payload: SalesComparisonRequest, db: Session, label_sql: str, group_by_sql: str, order_column: str = "current_revenue"):
    metric_cols = build_comparison_metric_columns(payload.search_type)
    where, params = build_filters(payload)

    query = f"""
        SELECT
            {label_sql},
            {", ".join(metric_cols)}
        {BASE_FROM_SQL}
        WHERE {" AND ".join(where)}
        GROUP BY {group_by_sql}
        ORDER BY {order_column} DESC NULLS LAST
        LIMIT :top_n
    """

    rows = db.execute(text(query), {**params, "top_n": TOP_N}).mappings().all()
    return [dict(row) for row in rows]


@router.post("/kpis")
def comparison_kpis(
    payload: SalesComparisonRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, db, current_user)
    metric_cols = build_comparison_metric_columns(payload.search_type)
    where, params = build_filters(payload)

    query = f"""
        SELECT
            {", ".join(metric_cols)}
        {BASE_FROM_SQL}
        WHERE {" AND ".join(where)}
    """

    row = db.execute(text(query), params).mappings().first() or {}

    response = {
        "periods": {
            "current": {"from_date": payload.current_from_date, "to_date": payload.current_to_date},
            "previous": {"from_date": payload.previous_from_date, "to_date": payload.previous_to_date},
        },
        "search_type": payload.search_type,
    }

    if payload.search_type in ["amount", "both"]:
        response["revenue"] = compute_comparison(
            row.get("current_revenue"),
            row.get("previous_revenue"),
        )

    if payload.search_type in ["quantity", "both"]:
        response["volume"] = compute_comparison(
            row.get("current_volume"),
            row.get("previous_volume"),
        )

    return response


@router.post("/top-customers")
def top_customers(
    payload: SalesComparisonRequest, 
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    rows = _run_group_query(
        payload,
        db,
        "ac.osa_code AS customer_code, ac.name AS customer",
        "ac.osa_code, ac.name",
    )
    return {"top_customers": rows}


@router.post("/top-items")
def top_items(
    payload: SalesComparisonRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    rows = _run_group_query(
        payload,
        db,
        "i.code AS item_code, i.name AS item",
        "i.code, i.name",
    )
    return {"top_items": rows}


@router.post("/top-salesmen")
def top_salesmen(
    payload: SalesComparisonRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    rows = _run_group_query(
        payload,
        db,
        "sm.osa_code AS salesman_code, sm.name AS salesman",
        "sm.osa_code, sm.name",
    )
    return {"top_salesmen": rows}


@router.post("/top-routes")
def top_routes(
    payload: SalesComparisonRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
      ):
    payload = apply_payload_permissions(payload, db, current_user)
    rows = _run_group_query(
        payload,
        db,
        "rt.route_code AS route_code, rt.route_name AS route",
        "rt.route_code, rt.route_name",
    )
    return {"top_routes": rows}


@router.post("/top-customer-groups")
def top_customer_groups(
    payload: SalesComparisonRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    rows = _run_group_query(
        payload,
        db,
        "ac.cust_group AS customer_group",
        "ac.cust_group",
    )
    return {"top_customer_groups": rows}
