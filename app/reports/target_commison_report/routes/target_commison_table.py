
from calendar import monthrange
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.target_commison_report.schemas.schemas import (
    SalesAchievementSchema,
)
from app.reports.target_commison_report.utils.target_commison_helper import (
    prepare_all_contexts,
    resolve_group_by,
)
from app.reports.target_commison_report.routes.target_commison_export import (
    fetch_sales_data,
    fetch_returns_data,
    fetch_target_data,
    compute_grouped_rows,
)


router = APIRouter(tags=["Target Commission Report"], dependencies=[Depends(get_current_user)])


def _round(value, ndigits=2):
    """Round numerics for the API; leave non-numeric values untouched."""
    if value is None:
        return 0
    return round(float(value), ndigits)


def _salesman_row(region: str, item: dict) -> dict:
    return {
        "row_type": "salesman",
        "region": region,
        "route": item["route_code"] or "",
        "code": item["osa_code"] or "",
        "salesman": item["salesman"] or "",
        "daily": {
            "sales": _round(item["daily_sales"]),
            "returns": _round(item["daily_returns"]),
            "return_pct": _round(item["daily_ret_pct"]),
            "net_sales": _round(item["daily_net"]),
            "target": _round(item["daily_target"]),
            "achievement_pct": _round(item["daily_ach"]),
        },
        "cumulative": {
            "sales": _round(item["cumulative_sales"]),
            "returns": _round(item["cumulative_returns"]),
            "return_pct": _round(item["mtd_ret_pct"]),
            "net_sales": _round(item["cumulative_net"]),
            "target": _round(item["mtd_target"]),
            "achievement_pct": _round(item["cumulative_ach"]),
        },
        "monthly": {
            "projected": _round(item["projected_sales"]),
            "target": _round(item["monthly_target"]),
            "achievement_pct": _round(item["projected_ach"]),
        },
    }


def _build_total(
    label: str,
    region: str,
    row_type: str,
    daily_sales: float,
    daily_returns: float,
    daily_net: float,
    daily_target: float,
    mtd_sales: float,
    mtd_returns: float,
    mtd_net: float,
    mtd_target: float,
    projected: float,
    monthly_target: float,
) -> dict:
    daily_ret_pct = (daily_returns / daily_sales * 100) if daily_sales else 0
    mtd_ret_pct = (mtd_returns / mtd_sales * 100) if mtd_sales else 0
    daily_ach = (daily_net / daily_target * 100) if daily_target else 0
    mtd_ach = (mtd_net / mtd_target * 100) if mtd_target else 0
    month_ach = (projected / monthly_target * 100) if monthly_target else 0

    return {
        "row_type": row_type,
        "region": region,
        "label": label,
        "daily": {
            "sales": _round(daily_sales),
            "returns": _round(daily_returns),
            "return_pct": _round(daily_ret_pct),
            "net_sales": _round(daily_net),
            "target": _round(daily_target),
            "achievement_pct": _round(daily_ach),
        },
        "cumulative": {
            "sales": _round(mtd_sales),
            "returns": _round(mtd_returns),
            "return_pct": _round(mtd_ret_pct),
            "net_sales": _round(mtd_net),
            "target": _round(mtd_target),
            "achievement_pct": _round(mtd_ach),
        },
        "monthly": {
            "projected": _round(projected),
            "target": _round(monthly_target),
            "achievement_pct": _round(month_ach),
        },
    }


@router.post("/sales-achievement-table")
def sales_achievement_table(
    payload: SalesAchievementSchema,
    db: Session = Depends(get_db),
):
    from_dt = datetime.strptime(payload.from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(payload.to_date, "%Y-%m-%d")

    total_days = monthrange(from_dt.year, from_dt.month)[1]
    current_day = to_dt.day

    ctxs = prepare_all_contexts(payload)
    sales_data = fetch_sales_data(db, ctxs["sales"], payload.to_date)
    return_data = fetch_returns_data(db, ctxs["returns"], payload.to_date)
    target_data = fetch_target_data(db, ctxs["target"])

    # Grouping is decided by the most specific filter applied:
    # Route > Region > Company. If none are applied, default to Company.
    group_by = resolve_group_by(payload)
    total_row_type = f"{group_by}_total"

    grouped_data = compute_grouped_rows(
        sales_data, return_data, target_data,
        group_by=group_by,
        total_days=total_days,
        current_day=current_day,
    )

    rows = []

    # Grand total accumulators
    g = {
        "daily_sales": 0, "daily_returns": 0, "daily_net": 0,
        "daily_target": 0,
        "mtd_sales": 0, "mtd_returns": 0, "mtd_net": 0,
        "mtd_target": 0,
        "projected": 0, "monthly_target": 0,
    }

    for group_value, items in grouped_data.items():
        # Per-group accumulators
        t = {
            "daily_sales": 0, "daily_returns": 0, "daily_net": 0,
            "daily_target": 0,
            "mtd_sales": 0, "mtd_returns": 0, "mtd_net": 0,
            "mtd_target": 0,
            "projected": 0, "monthly_target": 0,
        }

        for item in items:
            rows.append(_salesman_row(group_value, item))
            t["daily_sales"] += item["daily_sales"]
            t["daily_returns"] += item["daily_returns"]
            t["daily_net"] += item["daily_net"]
            t["daily_target"] += item["daily_target"]
            t["mtd_sales"] += item["cumulative_sales"]
            t["mtd_returns"] += item["cumulative_returns"]
            t["mtd_net"] += item["cumulative_net"]
            t["mtd_target"] += item["mtd_target"]
            t["projected"] += item["projected_sales"]
            t["monthly_target"] += item["monthly_target"]

        rows.append(_build_total(
            label=f"{group_value} TOTAL",
            region=group_value,
            row_type=total_row_type,
            daily_sales=t["daily_sales"],
            daily_returns=t["daily_returns"],
            daily_net=t["daily_net"],
            daily_target=t["daily_target"],
            mtd_sales=t["mtd_sales"],
            mtd_returns=t["mtd_returns"],
            mtd_net=t["mtd_net"],
            mtd_target=t["mtd_target"],
            projected=t["projected"],
            monthly_target=t["monthly_target"],
        ))

        # Fold group totals into grand total
        for k in g:
            g[k] += t[k]

    rows.append(_build_total(
        label="GRAND TOTAL",
        region="",
        row_type="grand_total",
        daily_sales=g["daily_sales"],
        daily_returns=g["daily_returns"],
        daily_net=g["daily_net"],
        daily_target=g["daily_target"],
        mtd_sales=g["mtd_sales"],
        mtd_returns=g["mtd_returns"],
        mtd_net=g["mtd_net"],
        mtd_target=g["mtd_target"],
        projected=g["projected"],
        monthly_target=g["monthly_target"],
    ))

    return {
        "meta": {
            "from_date": payload.from_date,
            "to_date": payload.to_date,
            "total_days_in_month": total_days,
            "current_day": current_day,
            "row_count": len(rows),
            "group_by": group_by,  # "company", "region", or "route" — tells the frontend what the "region" field on each row actually represents
        },
        "rows": rows,
    }
