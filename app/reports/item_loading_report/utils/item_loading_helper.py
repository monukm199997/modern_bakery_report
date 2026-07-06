from app.reports.item_loading_report.schemas.item_loading_schema import ItemLoadingRequest
from app.utils.helper import validate_mandatory

def build_common_filters(
    payload: ItemLoadingRequest,
    date_col: str,
    route_col: str,
    salesman_alias: str,
    route_alias: str,
):
    where_fragments = []
    params = {}

    where_fragments.append(f"{date_col}::date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        where_fragments.append(f"{salesman_alias}.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append(f"{route_alias}.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append(f"{route_col} = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.supervisor_ids:
        where_fragments.append(f"{salesman_alias}.superwiser_id = ANY(:supervisor_ids)")
        params["supervisor_ids"] = payload.supervisor_ids

    return where_fragments, params

def order_quantity():
    return """
    ROUND(
        SUM(
            CASE
                WHEN iu.upc IS NULL THEN 0
                ELSE aod.quantity::numeric * iu.upc::numeric
            END
        ),
        3
    )
    """

def load_quantity():
    return """
    ROUND(
        SUM(
            CASE
                WHEN iu.upc IS NULL THEN 0
                ELSE ld.qty::numeric * iu.upc::numeric
            END
        ),
        3
    )
    """

def prepare_dashboard_context(payload):
    # validate_mandatory(payload)

    order_qty = order_quantity()
    order_value = (
        order_qty if payload.search_type.lower() == "quantity"
        else "SUM(aod.net_total)"
    )

    load_qty = load_quantity()
    load_value = (
        load_qty if payload.search_type.lower() == "quantity"
        else "SUM(ld.qty * ld.price)"
    )

    order_where, order_params = build_common_filters(
        payload=payload,
        date_col="aoh.created_at",
        route_col="aoh.route_id",
        salesman_alias="s",
        route_alias="rt",
    )

    receive_where, receive_params = build_common_filters(
        payload=payload,
        date_col="lh.created_at",
        route_col="lh.route_id",
        salesman_alias="s2",
        route_alias="rt2",
    )

    order_where.extend([
        "aoh.deleted_at IS NULL",
        "aod.deleted_at IS NULL",
        "aoh.status = '1'",
        "ac.is_driver = 1",
    ])

    receive_where.extend([
        "lh.deleted_at IS NULL",
        "ld.deleted_at IS NULL",
    ])

    params = {**order_params, **receive_params}

    return {
        "order_where_sql": " AND ".join(order_where),
        "receive_where_sql": " AND ".join(receive_where),
        "order_value": order_value,
        "load_volue": load_value,
        "params": params,
    }

