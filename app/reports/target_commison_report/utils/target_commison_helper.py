from app.reports.target_commison_report.schemas.schemas import SalesAchievementSchema
from app.utils.helper import validate_mandatory
from datetime import datetime


# ---------------------------------------------------------------------------
# document_type buckets
# Anything NOT in either list is ignored by the report. Keep these exhaustive.
# ---------------------------------------------------------------------------
SALES_DOC_TYPES = ["ZVCS", "YDO", "YDI", "YSCR", "ZSCS", "ZFCD", "YFCD"]
RETURN_DOC_TYPES = ["YRSC", "ZRVS"]


# ---------------------------------------------------------------------------
# Measures (amount only — target_commison stores amount, not quantity)
#
# Column names are fixed here (never taken from user input), so interpolating
# them into SQL below is safe.
#
# CONFIRM which detail column matches the printed report's "Sales":
#   net_total (default), item_total, itemvalue, or gross_total.
# ---------------------------------------------------------------------------
SALES_VALUE_EXPR = "sdd.net_total::numeric"
TARGET_EXPR = "tc.total_target_amount"


# ---------------------------------------------------------------------------
# shared filters
# These MUST be applied identically to sales, returns AND targets, otherwise
# the per-salesman merge in compute_grouped_rows splits one salesman into
# mismatched rows. Assumes aliases s (salesman), rt (route), sup (supervisor)
# exist in the query.
# ---------------------------------------------------------------------------
def _apply_filters(payload: SalesAchievementSchema, where: list, params: dict):
    if payload.company_ids:
        where.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where.append("rt.id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.super_wiser_ids:
        where.append("sup.id = ANY(:super_wiser_ids)")
        params["super_wiser_ids"] = payload.super_wiser_ids


# ---------------------------------------------------------------------------
# sales / returns context
# Same source table (sales_documents_header + _detail); the only difference
# between sales and returns is the document_type set.
# ---------------------------------------------------------------------------
def _prepare_doc_context(payload: SalesAchievementSchema, doc_types: list):
    where = [
        "sdh.invoice_date >= CAST(:from_date AS date)",
        "sdh.invoice_date <= CAST(:to_date AS date)",
        "sdh.deleted_at IS NULL",                       # CONFIRM: exclude soft-deleted docs
        "sdh.document_type = ANY(:doc_types)",
    ]
    params = {
        "from_date": payload.from_date,
        "to_date": payload.to_date,
        "doc_types": doc_types,
    }
    _apply_filters(payload, where, params)
    return {
        "where_sql": " AND ".join(where),
        "params": params,
        "value_expr": SALES_VALUE_EXPR,
    }


def prepare_sales_context(payload: SalesAchievementSchema):
    return _prepare_doc_context(payload, SALES_DOC_TYPES)


def prepare_returns_context(payload: SalesAchievementSchema):
    return _prepare_doc_context(payload, RETURN_DOC_TYPES)


# ---------------------------------------------------------------------------
# target context
# Targets live in target_commison keyed by start_month / start_year.
# from_date and to_date are guaranteed to be in the same month (schema).
# ---------------------------------------------------------------------------
def prepare_target_context(payload: SalesAchievementSchema):
    from_dt = datetime.strptime(payload.from_date, "%Y-%m-%d")

    joins = [
        "LEFT JOIN tbl_route  rt  ON rt.id = tc.route_id",
        "LEFT JOIN tbl_region rg  ON rg.id = rt.region_id",
        "LEFT JOIN salesman   s   ON s.id  = tc.salesman_id",
        "LEFT JOIN users      sup ON sup.id = s.superwiser_id AND sup.role = 108",
    ]
    where = [
        "tc.start_month = :month",
        "tc.start_year = :year",
    ]
    params = {
        "month": from_dt.month,
        "year": from_dt.year,
    }
    _apply_filters(payload, where, params)

    joins = list(dict.fromkeys(joins))
    return {
        "join_sql": "\n".join(joins),
        "where_sql": " AND ".join(where),
        "params": params,
        "target_expr": TARGET_EXPR,
    }


# ---------------------------------------------------------------------------
# single entry point used by the routes
# ---------------------------------------------------------------------------
def prepare_all_contexts(payload: SalesAchievementSchema):
    """Validate once, then build all three contexts."""
    validate_mandatory(payload)
    return {
        "sales": prepare_sales_context(payload),
        "returns": prepare_returns_context(payload),
        "target": prepare_target_context(payload),
    }


# ---------------------------------------------------------------------------
# grouping resolution (Company -> Region -> Route)
# Priority (most specific wins): Route > Region > Company.
# Supervisor is a filter only, not a grouping dimension.
# ---------------------------------------------------------------------------
def resolve_group_by(payload: SalesAchievementSchema) -> str:
    if payload.route_ids:
        return "route_code"
    if payload.region_ids:
        return "region"
    return "company"