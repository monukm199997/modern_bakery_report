from fastapi import HTTPException
from app.reports.item_loading_report.schemas.item_loading_schema import (
    ItemLoadingRequest,
)
from app.utils.helper import validate_mandatory
from app.reports.item_loading_report.utils.item_loading_sql_query_helper import (
    DRILL_DOWN_MAP,
    ORDER_QUANTITY,
    LOAD_QUANTITY,
)


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
    return ORDER_QUANTITY


def load_quantity():
    return LOAD_QUANTITY


def prepare_dashboard_context(payload: ItemLoadingRequest):

    selected_fields = [field.lower() for field in (payload.drill_down_fields or [])]

    order_select_cols = []
    receive_select_cols = []
    final_select_cols = []

    order_group_cols = ["aoh.salesman_id"]
    receive_group_cols = ["lh.salesman_id"]

    order_joins = []
    receive_joins = []

    join_conditions = ["o.salesman_id = r.salesman_id"]

    for field in selected_fields:
        if field not in DRILL_DOWN_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid drill_down_field: {field}",
            )

        config = DRILL_DOWN_MAP[field]

        order_select_cols.append(config["order_select"])
        receive_select_cols.append(config["receive_select"])
        final_select_cols.append(config["final_select"])

        order_group_cols.append(config["order_group_by"])
        receive_group_cols.append(config["receive_group_by"])

        join_conditions.append(config["join_on"])

        if config.get("order_joins"):
            order_joins.append(config["order_joins"])

        if config.get("receive_joins"):
            receive_joins.append(config["receive_joins"])

    order_qty = order_quantity()
    load_qty = load_quantity()

    search_type = payload.search_type.lower()

    if search_type == "quantity":
        order_value = order_qty
        load_value = load_qty
    else:
        order_value = "SUM(aod.net_total)"
        load_value = "SUM(ld.qty * ld.price)"

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

    order_where.extend(
        [
            "aoh.deleted_at IS NULL",
            "aod.deleted_at IS NULL",
            "aoh.status = '1'",
            "ac.is_driver = 1",
        ]
    )

    receive_where.extend(
        [
            "lh.deleted_at IS NULL",
            "ld.deleted_at IS NULL",
        ]
    )

    params = {**order_params, **receive_params}

    return {
        "order_where_sql": " AND ".join(order_where),
        "receive_where_sql": " AND ".join(receive_where),
        "order_value": order_value,
        "load_volue": load_value,
        "order_select_sql": (
            ",\n" + ",\n".join(order_select_cols) if order_select_cols else ""
        ),
        "receive_select_sql": (
            ",\n" + ",\n".join(receive_select_cols) if receive_select_cols else ""
        ),
        "final_select_sql": (
            ",\n" + ",\n".join(final_select_cols) if final_select_cols else ""
        ),
        "order_group_sql": ",\n".join(order_group_cols),
        "receive_group_sql": ",\n".join(receive_group_cols),
        "order_join_sql": "\n".join(dict.fromkeys(order_joins)),
        "receive_join_sql": "\n".join(dict.fromkeys(receive_joins)),
        "join_condition_sql": " AND ".join(join_conditions),
        "params": params,
    }
