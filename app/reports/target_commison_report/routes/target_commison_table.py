from calendar import monthrange
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
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


router = APIRouter(tags=["Target Commission Report"], dependencies=[Depends(get_current_user)])


# =====================================================================
# DATA ACCESS  (sales + returns come from the same table, split by
# document_type inside ctx['where_sql']; ctx['value_expr'] is the amount
# column, ctx['target_expr'] the target amount column)
# =====================================================================

def _fetch_doc_data(db: Session, ctx: dict, to_date: str):
    sql = f"""
        SELECT
            co.company_name AS company,
            rg.region_name  AS region,
            rt.route_code   AS route_code,
            s.id            AS salesman_id,
            s.name          AS salesman_name,
            s.osa_code      AS osa_code,
            COALESCE(ROUND(
                SUM(CASE
                    WHEN sdh.invoice_date = CAST(:daily_date AS date)
                    THEN {ctx['value_expr']}
                    ELSE 0
                END)::numeric, 6
            ), 0) AS daily_value,
            COALESCE(ROUND(SUM({ctx['value_expr']})::numeric, 6), 0) AS cumulative_value
        FROM sales_documents_header sdh
        LEFT JOIN sales_documents_detail sdd
               ON sdd.header_id = sdh.id AND sdd.deleted_at IS NULL
        LEFT JOIN salesman    s   ON s.id  = sdh.salesman_id
        LEFT JOIN tbl_company co  ON co.id = s.company_id
        LEFT JOIN tbl_route   rt  ON rt.id = sdh.route_id
        LEFT JOIN tbl_region  rg  ON rg.id = rt.region_id
        LEFT JOIN users       sup ON sup.id = s.superwiser_id AND sup.role = 108
        WHERE {ctx['where_sql']}
        GROUP BY co.company_name, rg.region_name, rt.route_code,
                 s.id, s.name, s.osa_code
        ORDER BY co.company_name, rg.region_name, s.name
    """
    params = {**ctx["params"], "daily_date": to_date}
    return db.execute(text(sql), params).mappings().all()


def fetch_sales_data(db: Session, ctx: dict, to_date: str):
    return _fetch_doc_data(db, ctx, to_date)


def fetch_returns_data(db: Session, ctx: dict, to_date: str):
    return _fetch_doc_data(db, ctx, to_date)


def fetch_target_data(db: Session, ctx: dict):
    sql = f"""
        SELECT
            co.company_name AS company,
            rg.region_name  AS region,
            s.id            AS salesman_id,
            s.name          AS salesman_name,
            s.osa_code      AS osa_code,
            rt.route_code   AS route_code,
            COALESCE(SUM({ctx['target_expr']}), 0) AS target
        FROM target_commison tc
        {ctx['join_sql']}
        LEFT JOIN tbl_company co ON co.id = s.company_id
        WHERE {ctx['where_sql']}
        GROUP BY co.company_name, rg.region_name, s.id, s.name, s.osa_code,
                 rt.route_code
    """
    return db.execute(text(sql), ctx["params"]).mappings().all()


# =====================================================================
# AGGREGATION
# =====================================================================

def compute_grouped_rows(sales_data, return_data, target_data,
                         group_by: str,
                         total_days: int, current_day: int):

    def key_of(r):
        return (r.get(group_by) or "(Unknown)", r["salesman_id"])

    sales_map = {key_of(r): r for r in sales_data}
    return_map = {key_of(r): r for r in return_data}
    target_map = {key_of(r): r for r in target_data}

    all_keys = set(sales_map) | set(return_map) | set(target_map)

    def pick(key, field):
        for m in (sales_map, return_map, target_map):
            row = m.get(key)
            if row and row.get(field):
                return row[field]
        return ""

    grouped = defaultdict(list)

    for key in all_keys:
        group_value, salesman_id = key
        sales_row = sales_map.get(key, {})
        ret_row = return_map.get(key, {})
        tgt_row = target_map.get(key, {})

        daily_sales = float(sales_row.get("daily_value", 0) or 0)
        cumulative_sales = float(sales_row.get("cumulative_value", 0) or 0)
        daily_returns = float(ret_row.get("daily_value", 0) or 0)
        cumulative_returns = float(ret_row.get("cumulative_value", 0) or 0)
        monthly_target = float(tgt_row.get("target", 0) or 0)

        daily_net = daily_sales - daily_returns
        cumulative_net = cumulative_sales - cumulative_returns

        daily_target = monthly_target / total_days if total_days else 0
        mtd_target = monthly_target * current_day / total_days if total_days else 0

        daily_ach = (daily_net / daily_target * 100) if daily_target else 0
        cumulative_ach = (cumulative_net / mtd_target * 100) if mtd_target else 0

        projected_sales = (
            (cumulative_net / current_day) * total_days if current_day else 0
        )
        projected_ach = (
            (projected_sales / monthly_target * 100) if monthly_target else 0
        )

        # Return %
        daily_ret_pct = (daily_returns / daily_sales * 100) if daily_sales else 0
        mtd_ret_pct = (
            cumulative_returns / cumulative_sales * 100
            if cumulative_sales else 0
        )

        grouped[group_value].append({
            "route_code": pick(key, "route_code"),
            "osa_code": pick(key, "osa_code"),
            "salesman": pick(key, "salesman_name"),
            "daily_sales": daily_sales,
            "daily_returns": daily_returns,
            "daily_ret_pct": daily_ret_pct,
            "daily_net": daily_net,
            "daily_target": daily_target,
            "daily_ach": daily_ach,
            "cumulative_sales": cumulative_sales,
            "cumulative_returns": cumulative_returns,
            "mtd_ret_pct": mtd_ret_pct,
            "cumulative_net": cumulative_net,
            "mtd_target": mtd_target,
            "cumulative_ach": cumulative_ach,
            "projected_sales": projected_sales,
            "monthly_target": monthly_target,
            "projected_ach": projected_ach,
        })

    for group_value in grouped:
        grouped[group_value].sort(key=lambda x: (x["salesman"] or "").lower())

    return grouped


# =====================================================================
# CANONICAL PIPELINE  (shared by this table view AND the export route)
# =====================================================================

def get_sales_achievement_data(db: Session, payload: SalesAchievementSchema):
    """
    Run the full report pipeline once and return (grouped_data, meta).

    This is the single source of truth for the report's data. The table
    endpoint below turns it into JSON; the export route turns the same
    grouped_data into an Excel workbook.
    """
    from_dt = datetime.strptime(payload.from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(payload.to_date, "%Y-%m-%d")

    total_days = monthrange(from_dt.year, from_dt.month)[1]
    current_day = to_dt.day

    ctxs = prepare_all_contexts(payload)
    sales_data = fetch_sales_data(db, ctxs["sales"], payload.to_date)
    return_data = fetch_returns_data(db, ctxs["returns"], payload.to_date)
    target_data = fetch_target_data(db, ctxs["target"])

    group_by = resolve_group_by(payload)
    grouped_data = compute_grouped_rows(
        sales_data, return_data, target_data,
        group_by=group_by,
        total_days=total_days,
        current_day=current_day,
    )

    meta = {
        "from_date": payload.from_date,
        "to_date": payload.to_date,
        "total_days_in_month": total_days,
        "current_day": current_day,
        "group_by": group_by,
    }
    return grouped_data, meta


# =====================================================================
# JSON ROW BUILDERS
# =====================================================================

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


# =====================================================================
# TABLE ENDPOINT
# =====================================================================

@router.post("/sales-achievement-table")
def sales_achievement_table(
    payload: SalesAchievementSchema,
    db: Session = Depends(get_db),
):
    grouped_data, meta = get_sales_achievement_data(db, payload)

    group_by = meta["group_by"]
    total_row_type = f"{group_by}_total"

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
        "meta": {**meta, "row_count": len(rows)},
        "rows": rows,
    }