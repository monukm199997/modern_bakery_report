from app.reports.numerical_distribution_report.schemas.numerical_distribution_schema import NumericalDistributionRequest
from app.reports.numerical_distribution_report.utils.numerical_distribution_sql_query import (
    DRILL_DOWN_MAP,
    HIERARCHY_MAP,
    ITEM_COLUMNS,
    BASE_FROM,
)


def build_sales_document_filters(payload: NumericalDistributionRequest):
    where = []
    params = {}

    where.append("sdh.invoice_date BETWEEN :from_date AND :to_date")

    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        where.append("sm.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where.append("sdh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    return where, params


def prepare_numerical_distribution_context(payload):

    where, params = build_sales_document_filters(payload)

    # Report specific filters
    where.extend([
        "sdh.deleted_at IS NULL",
        "sdd.deleted_at IS NULL",
        "sdh.document_type IN ('ZVCS','YDO','YDI','YSCR','ZSCS','ZFCD','YFCD','YSDR')",
    ])

    select_parts = []
    group_by_parts = []
    order_by_parts = []

    if payload.route_ids:
        cfg = HIERARCHY_MAP["route"]
    elif payload.region_ids:
        cfg = HIERARCHY_MAP["region"]
    else:
        cfg = None

    if cfg:
        select_parts.extend(cfg["select"])
        group_by_parts.extend(cfg["group_by"])
        order_by_parts.extend(cfg["order_by"])

    if payload.drill_down_fields:
        for drill in payload.drill_down_fields:
            if drill in DRILL_DOWN_MAP:
                cfg = DRILL_DOWN_MAP[drill]
                select_parts.extend(cfg["select"])
                group_by_parts.extend(cfg["group_by"])
                order_by_parts.extend(cfg["order_by"])


    select_parts.extend(ITEM_COLUMNS["select"])
    group_by_parts.extend(ITEM_COLUMNS["group_by"])
    order_by_parts.extend(ITEM_COLUMNS["order_by"])

    return {
        "select": ",\n".join(dict.fromkeys(select_parts)),
        "from": BASE_FROM,
        "where": "\nAND ".join(where),
        "group_by": ",\n".join(dict.fromkeys(group_by_parts)),
        "order_by": ",\n".join(dict.fromkeys(order_by_parts)),
        "params": params,
    }