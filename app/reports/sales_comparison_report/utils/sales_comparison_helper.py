from datetime import date, timedelta
import calendar
from typing import List, Tuple, Dict

from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)

def get_periods(report_by: str, selected_date: date):
    if report_by == "day":
        current_from = selected_date
        current_to = selected_date
        previous_from = selected_date - timedelta(days=1)
        previous_to = selected_date - timedelta(days=1)

    elif report_by == "month":
        current_from = selected_date.replace(day=1)
        last_day = calendar.monthrange(selected_date.year, selected_date.month)[1]
        current_to = selected_date.replace(day=last_day)

        prev_month_anchor = current_from - timedelta(days=1)
        previous_from = prev_month_anchor.replace(day=1)
        last_day_prev = calendar.monthrange(
            prev_month_anchor.year, prev_month_anchor.month
        )[1]
        previous_to = prev_month_anchor.replace(day=last_day_prev)

    elif report_by == "year":
        current_from = date(selected_date.year, 1, 1)
        current_to = date(selected_date.year, 12, 31)
        previous_from = date(selected_date.year - 1, 1, 1)
        previous_to = date(selected_date.year - 1, 12, 31)

    else:
        raise ValueError("Invalid report_by")

    return current_from, current_to, previous_from, previous_to


# ─────────────────────────────────────────────────────────────────
# QUERY PARTS
# ─────────────────────────────────────────────────────────────────
def build_query_parts(
    payload: SalesComparisonRequest,
    prev_from: date,
    current_to: date,
) -> Tuple[List[str], List[str], Dict]:
    where_fragments: List[str] = []
    params: Dict = {}

    where_fragments.append("ih.invoice_date BETWEEN :prev_from AND :current_to")
    params["prev_from"] = prev_from
    params["current_to"] = current_to

    if payload.company_ids:
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.salesman_ids:
        where_fragments.append("ih.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids

    return where_fragments, params


def value_expressions(search_type: str) -> Tuple[str, str]:
    current_cond = "ih.invoice_date BETWEEN :current_from AND :current_to"
    prev_cond = "ih.invoice_date BETWEEN :prev_from AND :prev_to"

    if search_type.lower() == "quantity":
        def qty(cond: str) -> str:
            return f"""
            ROUND(
                SUM(
                    CASE
                        WHEN {cond} AND iu.upc IS NOT NULL
                        THEN id.quantity::numeric * iu.upc::numeric
                        ELSE 0
                    END
                ),
                6
            )
            """
        current_expr = qty(current_cond)
        prev_expr = qty(prev_cond)
    else:
        current_expr = f"SUM(CASE WHEN {current_cond} THEN id.item_total ELSE 0 END)"
        prev_expr    = f"SUM(CASE WHEN {prev_cond}    THEN id.item_total ELSE 0 END)"

    return current_expr, prev_expr

def prepare_dashboard_context(
    payload: SalesComparisonRequest,
    current_from: date,
    current_to: date,
    prev_from: date,
    prev_to: date,
) -> Dict:

    where_fragments, params = build_query_parts(payload, prev_from, current_to)

    params.update(
        {
            "current_from": current_from,
            "current_to": current_to,
            "prev_from": prev_from,
            "prev_to": prev_to,
        }
    )
    current_expr, prev_expr = value_expressions(payload.search_type)
    return {
        "where_sql": " AND ".join(where_fragments),
        "params": params,
        "current_expr": current_expr,
        "prev_expr": prev_expr,
    }


def compute_comparison(current: float, previous: float) -> Dict[str, float]:
 
    current = float(current or 0)
    previous = float(previous or 0)
    difference = round(current - previous, 2)
    if difference == -0.0:
        difference = 0.0

    if previous > 0:
        growth = round(((current - previous) / previous) * 100, 2)
    else:
        growth = 100.0 if current > 0 else 0.0

    if growth == -0.0:
        growth = 0.0

    return {
        "current_sales": round(current, 2),
        "previous_sales": round(previous, 2),
        "difference": difference,
        "growth_percent": growth,
    }

def format_period_label(report_by: str, period_from, period_to) -> str:
    if report_by == "day":
        return f"{period_from:%d %b %Y}" 
    if report_by == "month":
        return f"{period_from:%b %Y}"          
    if report_by == "year":
        return f"{period_from:%Y}" 
    return f"{period_from:%b %d, %Y} – {period_to:%b %d, %Y}" 
