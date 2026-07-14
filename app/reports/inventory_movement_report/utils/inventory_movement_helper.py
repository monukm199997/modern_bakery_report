from app.reports.inventory_movement_report.schemas.inventory_movement_schema import InventoryMovementRequest
from datetime import timedelta
from app.reports.inventory_movement_report.utils.inventory_movement_sql_query import (
    UNLOAD_QUANTITY,
    LOAD_QUANTITY,
    SALES_QUANTITY,
    RETURN_QUANTITY,
    VAN_RETURN_QUANTITY,
)



def build_common_filters(
    payload: InventoryMovementRequest,
    date_col: str,
    route_col: str,
    salesman_alias: str,
    route_alias: str,
    customer_alias: str = None,
    use_route_channel: bool = False,
    previous_day: bool = False,
):
    where_fragments = []
    params = {}

    if previous_day:
        where_fragments.append(f"{date_col}::date = :previous_date")
        params["previous_date"] = payload.from_date - timedelta(days=1)
    else:
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

    if payload.channel_ids:
        if use_route_channel:
            where_fragments.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM agent_customers ac
                    WHERE ac.route_id = {route_col}
                    AND ac.outlet_channel_id = ANY(:channel_ids)
                )
                """
            )
        else:
            where_fragments.append(
                f"{customer_alias}.outlet_channel_id = ANY(:channel_ids)"
            )

        params["channel_ids"] = payload.channel_ids


    return where_fragments, params

def get_unload_quantity():
    return UNLOAD_QUANTITY

def get_load_quantity():
    return LOAD_QUANTITY

def get_sales_quantity():
    return SALES_QUANTITY

def get_return_quantity():
    return RETURN_QUANTITY

def get_van_return_quantity():
    return VAN_RETURN_QUANTITY


def prepare_inventory_movement_context(payload:InventoryMovementRequest):

    unload_quantity = get_unload_quantity()
    load_quantity = get_load_quantity()
    sales_quantity = get_sales_quantity()
    return_quantity = get_return_quantity()
    van_return_quantity = get_van_return_quantity()

    unload_where, unload_params = build_common_filters(
        payload=payload,
        date_col="uh.unload_date",
        route_col="uh.route_id",
        salesman_alias="su",
        route_alias="ru",
        customer_alias=None,
        use_route_channel=True,
        previous_day=True,
    )

    load_where, load_params = build_common_filters(
        payload=payload,
        date_col="lh.created_at",
        route_col="lh.route_id",
        salesman_alias="sl",
        route_alias="rl",
        customer_alias=None,
        use_route_channel=True,
    )

    sales_where, sales_params = build_common_filters(
        payload=payload,
        date_col="ih.invoice_date",
        route_col="ih.route_id",
        salesman_alias="si",
        route_alias="ri",
        customer_alias="aci",
    )

    van_return_where, van_return_params = build_common_filters(
        payload=payload,
        date_col="vrh.created_at",
        route_col="vrh.route_id",
        salesman_alias="svr",
        route_alias="rvr",
        customer_alias="acvr",
    )

    return_where, return_params = build_common_filters(
        payload=payload,
        date_col="rh.created_at",
        route_col="rh.route_id",
        salesman_alias="sr",
        route_alias="rr",
        customer_alias="acr",
    )

    unload_where.extend(
        [
            "uh.deleted_at IS NULL",
            "ud.deleted_at IS NULL",
            "document_type = 'carryover'",
        ]
    )

    load_where.extend(
        [
            "lh.deleted_at IS NULL",
            "ld.deleted_at IS NULL",
        ]
    )

    van_return_where.extend(
        [
            "vrh.deleted_at IS NULL",
            "vrd.deleted_at IS NULL",
            "sap_status = '1'"
        ]
    )

    return_where.extend(
        [
            "rh.deleted_at IS NULL",
            "rd.deleted_at IS NULL",
            "sap_status = '1'"
        ]
    )

    sales_where.extend(
        [
            "ih.deleted_at IS NULL",
            "id.deleted_at IS NULL",
            "sap_status = '1'",
        ]
    )

    params = {**unload_params, **load_params, **sales_params, **return_params, **van_return_params}

    return{
        "unload_where": " AND ".join(unload_where),
        "load_where": " AND ".join(load_where),
        "sales_where": " AND ".join(sales_where),
        "van_return_where": " AND ".join(van_return_where),
        "return_where": " AND ".join(return_where),
        "unload_quantity": unload_quantity,
        "load_quantity": load_quantity,
        "sales_quantity": sales_quantity,
        "return_quantity": return_quantity,
        "van_return_quantity": van_return_quantity,
        "params": params,
    }

