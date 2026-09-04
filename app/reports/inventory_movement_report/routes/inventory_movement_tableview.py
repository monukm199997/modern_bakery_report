from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.reports.inventory_movement_report.schemas.inventory_movement_schema import (
    InventoryMovementRequest,
)
from app.reports.inventory_movement_report.utils.inventory_movement_helper import (
    prepare_inventory_movement_context,
)
from app.utils.constant import ROWS_PER_PAGE
from app.reports.inventory_movement_report.utils.inventory_movement_sql_query import (
    UNLOAD_DATA_JOIN,
    LOAD_DATA_JOIN,
    SALES_DATA_JOIN,
    VAN_RETURN_DATA_JOIN,
    RETURN_DATA_JOIN,
    FINAL_SELECT,
    SALESMAN_CODE,
    SALESMAN_NAME,
    ITEM_NAME,
    ITEM_CODE,
    ITEM_CATEGORY,
    GROUP_UNLOAD,
    GROUP_LOAD,
    GROUP_SALES,
    GROUP_VAN_RETURN,
    GROUP_RETURN,
    SALESMAN_SELECT,
    FINAL_KEYS,
    JOIN_CONDITION,
    LOAD_JOIN_CONDITION,
    SALES_JOIN_CONDITION,
    VAN_RETURN_JOIN_CONDITION,
    RETURN_JOIN_CONDITION,
    _GROUP_UNLOAD,
    _GROUP_LOAD,
    _GROUP_SALES,
    _GROUP_VAN_RETURN,
    _GROUP_RETURN,
    _SALESMAN_SELECT,
    _FINAL_KEYS,
    _JOIN_CONDITION,
    _LOAD_JOIN_CONDITION,
    _SALES_JOIN_CONDITION,
    _VAN_RETURN_JOIN_CONDITION,
    _RETURN_JOIN_CONDITION,


)

router = APIRouter(
    tags=["Inventory Movement Report"], dependencies=[Depends(get_current_user)]
)


def build_inventory_movement_query(ctx):
    item_wise = ctx["item_wise"]
    if item_wise:
        group_unload = GROUP_UNLOAD
        group_load = GROUP_LOAD
        group_sales = GROUP_SALES
        group_van_return = GROUP_VAN_RETURN
        group_return = GROUP_RETURN
        salesmen_select = SALESMAN_SELECT
        final_keys = FINAL_KEYS
        unload_join_condition = JOIN_CONDITION
        load_join_condition = LOAD_JOIN_CONDITION
        sales_join_condition = SALES_JOIN_CONDITION
        van_return_join_condition = VAN_RETURN_JOIN_CONDITION
        return_join_condition = RETURN_JOIN_CONDITION

        item_select = f"""
            {ITEM_CODE}
            {ITEM_NAME}
            {ITEM_CATEGORY}
        """
    else:
        group_unload = _GROUP_UNLOAD
        group_load = _GROUP_LOAD
        group_sales = _GROUP_SALES
        group_van_return = _GROUP_VAN_RETURN
        group_return = _GROUP_RETURN
        salesmen_select = _SALESMAN_SELECT
        final_keys = _FINAL_KEYS
        unload_join_condition = _JOIN_CONDITION
        load_join_condition = _LOAD_JOIN_CONDITION
        sales_join_condition = _SALES_JOIN_CONDITION
        van_return_join_condition = _VAN_RETURN_JOIN_CONDITION
        return_join_condition = _RETURN_JOIN_CONDITION

        item_select = ""


    query = f"""
        WITH unload_data AS (
            SELECT
                uh.salesman_id,
                su.osa_code AS salesman_code,
                su.name AS salesman_name,
                {"ud.item_id," if item_wise else ""}
                {"i.name AS item_name," if item_wise else ""}
                {"i.code AS item_code," if item_wise else ""}   
                {"i.category_id AS category_id," if item_wise else ""}
                {"ic.category_name AS item_category," if item_wise else ""}

                {ctx['unload_quantity']} AS open_stock
            FROM {UNLOAD_DATA_JOIN}
            WHERE {ctx['unload_where']}
            GROUP BY {group_unload}
        ),
        load_data AS (
            SELECT
                lh.salesman_id,
                sl.osa_code AS salesman_code,
                sl.name AS salesman_name,
                {"ld.item_id," if item_wise else ""}
                {"i.name AS item_name," if item_wise else ""}
                {"i.code AS item_code," if item_wise else ""}
                {"i.category_id AS category_id," if item_wise else ""}
                {"ic.category_name AS item_category," if item_wise else ""}
                {ctx['load_quantity']} AS load_qty
            FROM {LOAD_DATA_JOIN}
            WHERE {ctx['load_where']}
            GROUP BY {group_load}
        ),
        sales_data AS (
            SELECT
                ih.salesman_id,
                si.osa_code AS salesman_code,
                si.name AS salesman_name,
                {"id.item_id," if item_wise else ""}
                {"i.name AS item_name," if item_wise else ""}
                {"i.code AS item_code," if item_wise else ""}
                {"i.category_id AS category_id," if item_wise else ""}
                {"ic.category_name AS item_category," if item_wise else ""}
                {ctx['sales_quantity']} AS sold_qty
            FROM {SALES_DATA_JOIN}
            WHERE {ctx['sales_where']}
            GROUP BY {group_sales}
        ),
        van_return_data AS (
            SELECT
                vrh.salesman_id,
                svr.osa_code AS salesman_code,
                svr.name AS salesman_name,
                {"vrd.item_id," if item_wise else ""}
                {"i.name AS item_name," if item_wise else ""}
                {"i.code AS item_code," if item_wise else ""}
                {"i.category_id AS category_id," if item_wise else ""}
                {"ic.category_name AS item_category," if item_wise else ""}
                {ctx['van_return_quantity']} AS van_return_qty
            FROM {VAN_RETURN_DATA_JOIN}
            WHERE {ctx['van_return_where']}
            GROUP BY {group_van_return}
        ),
        return_data AS (
            SELECT
                rh.salesman_id,
                sr.osa_code AS salesman_code,
                sr.name AS salesman_name,
                {"rd.item_id," if item_wise else ""}
                {"i.name AS item_name," if item_wise else ""}
                {"i.code AS item_code," if item_wise else ""}
                {"i.category_id AS category_id," if item_wise else ""}
                {"ic.category_name AS item_category," if item_wise else ""}
                {ctx['return_quantity']} AS return_qty
            FROM {RETURN_DATA_JOIN}
            WHERE {ctx['return_where']}
            GROUP BY {group_return}
        ),
        salesmen AS (
            {salesmen_select}
        )
        SELECT
             {final_keys}
            {SALESMAN_CODE}
            {SALESMAN_NAME}
            {item_select}
            {FINAL_SELECT}
        FROM salesmen s
        LEFT JOIN unload_data u ON {unload_join_condition}
        LEFT JOIN load_data l ON {load_join_condition}
        LEFT JOIN sales_data sd ON {sales_join_condition}
        LEFT JOIN van_return_data vr ON {van_return_join_condition}
        LEFT JOIN return_data r ON {return_join_condition}
    """
    return query


@router.post("/inventory-movement-tableview")
def inventory_movement_tableview(
    payload: InventoryMovementRequest,
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_inventory_movement_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE
    ctx["params"]["limit"] = ROWS_PER_PAGE
    ctx["params"]["offset"] = offset

    base_query = build_inventory_movement_query(ctx)
    count_query = f"""
        SELECT COUNT(*) 
        FROM ({base_query}) AS count_data
    """

    data_query = f"""
        {base_query}
        LIMIT :limit OFFSET :offset
    """
    total_rows = db.execute(text(count_query), ctx["params"]).scalar() or 0
    rows = db.execute(text(data_query), ctx["params"]).fetchall()
    result = [dict(r._mapping) for r in rows]
    total_pages = (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
    base_url = str(request.url).split("?")[0]
    next_page = None
    previous_page = None
    if page < total_pages:
        next_page = f"{base_url}?page={page + 1}&page_size={ROWS_PER_PAGE}"

    if page > 1:
        previous_page = f"{base_url}?page={page - 1}&page_size={ROWS_PER_PAGE}"

    return {
        "total_rows": total_rows,
        "total_pages": total_pages,
        "current_page": page,
        "next_page": next_page,
        "previous_page": previous_page,
        "rows": result,
    }
