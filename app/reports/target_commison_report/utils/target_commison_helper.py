from app.reports.target_commison_report.schemas.schemas import SalesAchievementSchema
from app.utils.helper import validate_mandatory
from datetime import datetime


# ---------- shared quantity expressions ----------

def invoice_quantity_expr() -> str:
    """Quantity * UPC for invoice_details rows."""
    return """
        CASE
            WHEN iu.upc IS NULL THEN 0
            ELSE id.quantity::numeric * iu.upc::numeric
        END
    """


def return_quantity_expr() -> str:
    """Quantity * UPC for return_details rows."""
    return """
        CASE
            WHEN iu.upc IS NULL THEN 0
            ELSE rd.item_quantity::numeric * iu.upc::numeric
        END
    """


# ---------- generic builder for sales + returns ----------

def _build_txn_query_parts(
    payload: SalesAchievementSchema,
    date_column: str,
    route_alias_source: str,
):
    """
    Build joins / where / params for transaction-style queries
    (invoices, returns). The tbl_route join is ALWAYS added so that
    rt.* / rg.* references in the main SELECT never fail.

    date_column         : e.g. "ih.invoice_date" or "rh.created_at"
    route_alias_source  : the table.column to link tbl_route to,
                          e.g. "ih.route_id" or "rh.route_id"
    """
    joins = [
        f"LEFT JOIN tbl_route rt ON rt.id = {route_alias_source}",
        "LEFT JOIN tbl_region rg ON rg.id = rt.region_id",
    ]
    where_fragments = []
    params = {}


    where_fragments.append(
        f"{date_column} >= CAST(:from_date AS date) "
        f"AND {date_column} < CAST(:to_date AS date) + INTERVAL '1 day'"
    )
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.channel_ids:
        where_fragments.append("s.channel_id = ANY(:channel_ids)")
        params["channel_ids"] = payload.channel_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params


def prepare_sales_context(payload: SalesAchievementSchema):
    joins, where_fragments, params = _build_txn_query_parts(
        payload,
        date_column="ih.invoice_date",
        route_alias_source="ih.route_id",
    )
    return {
        "join_sql": "\n".join(joins),
        "where_sql": " AND ".join(where_fragments),
        "params": params,
        "quantity": invoice_quantity_expr(),
    }


def prepare_returns_context(payload: SalesAchievementSchema):
    joins, where_fragments, params = _build_txn_query_parts(
        payload,
        date_column="rh.created_at",
        route_alias_source="rh.route_id",
    )
    return {
        "join_sql": "\n".join(joins),
        "where_sql": " AND ".join(where_fragments),
        "params": params,
        "quantity": return_quantity_expr(),
    }


# ---------- target builder ----------

def prepare_target_context(payload: SalesAchievementSchema):
    """
    Targets live in target_commison keyed by start_month / start_year.
    We assume from_date and to_date are in the same month (validated
    in the schema).
    """
    from_dt = datetime.strptime(payload.from_date, "%Y-%m-%d")

    joins = [
        "LEFT JOIN tbl_route rt ON rt.id = tc.route_id",
        "LEFT JOIN tbl_region rg ON rg.id = rt.region_id",
        "LEFT JOIN salesman s ON s.id = tc.salesman_id",
    ]
    where_fragments = [
        "tc.start_month = :month",
        "tc.start_year = :year",
    ]
    params = {
        "month": from_dt.month,
        "year": from_dt.year,
    }

    if payload.company_ids:
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.channel_ids:
        where_fragments.append("s.channel_id = ANY(:channel_ids)")
        params["channel_ids"] = payload.channel_ids

    joins = list(dict.fromkeys(joins))
    return {
        "join_sql": "\n".join(joins),
        "where_sql": " AND ".join(where_fragments),
        "params": params,
    }


# ---------- single entry point used by the route ----------

def prepare_all_contexts(payload: SalesAchievementSchema):
    """Validate once, then build all three contexts."""
    validate_mandatory(payload)
    return {
        "sales": prepare_sales_context(payload),
        "returns": prepare_returns_context(payload),
        "target": prepare_target_context(payload),
    }
