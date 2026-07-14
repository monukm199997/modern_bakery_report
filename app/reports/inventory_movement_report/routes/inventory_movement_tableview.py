from fastapi import APIRouter, Request, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.inventory_movement_report.schemas.inventory_movement_schema import InventoryMovementRequest
from app.reports.inventory_movement_report.utils.inventory_movement_helper import prepare_inventory_movement_context
from app.utils.constant import ROWS_PER_PAGE
from app.reports.inventory_movement_report.utils.inventory_movement_sql_query import (
    UNLOAD_DATA_JOIN,
    LOAD_DATA_JOIN,
    SALES_DATA_JOIN,
    VAN_RETURN_DATA_JOIN,
    RETURN_DATA_JOIN,
    FINAL_SELECT,
    SALESMAN_CODE,
    SALESMAN_NAME
)

router = APIRouter(tags=["Inventory Movement Report"], dependencies=[Depends(get_current_user)])

def build_inventory_movement_query(ctx):

    query = f"""
        WITH unload_data AS (
            SELECT
                uh.salesman_id,
                su.osa_code AS salesman_code,
                su.name AS salesman_name,
                {ctx['unload_quantity']} AS open_stock
            FROM {UNLOAD_DATA_JOIN}
            WHERE {ctx['unload_where']}
            GROUP BY uh.salesman_id, su.osa_code, su.name
        ),
        load_data AS (
            SELECT
                lh.salesman_id,
                sl.osa_code AS salesman_code,
                sl.name AS salesman_name,
                {ctx['load_quantity']} AS load_qty
            FROM {LOAD_DATA_JOIN}
            WHERE {ctx['load_where']}
            GROUP BY lh.salesman_id, sl.osa_code, sl.name
        ),
        sales_data AS (
            SELECT
                ih.salesman_id,
                si.osa_code AS salesman_code,
                si.name AS salesman_name,
                {ctx['sales_quantity']} AS sold_qty
            FROM {SALES_DATA_JOIN}
            WHERE {ctx['sales_where']}
            GROUP BY ih.salesman_id, si.osa_code, si.name
        ),
        van_return_data AS (
            SELECT
                vrh.salesman_id,
                svr.osa_code AS salesman_code,
                svr.name AS salesman_name,
                {ctx['van_return_quantity']} AS van_return_qty
            FROM {VAN_RETURN_DATA_JOIN}
            WHERE {ctx['van_return_where']}
            GROUP BY vrh.salesman_id, svr.osa_code, svr.name
        ),
        return_data AS (
            SELECT
                rh.salesman_id,
                sr.osa_code AS salesman_code,
                sr.name AS salesman_name,
                {ctx['return_quantity']} AS return_qty
            FROM {RETURN_DATA_JOIN}
            WHERE {ctx['return_where']}
            GROUP BY rh.salesman_id, sr.osa_code, sr.name
        ),
        salesmen AS (
            SELECT salesman_id FROM unload_data
            UNION
            SELECT salesman_id FROM load_data
            UNION
            SELECT salesman_id FROM sales_data
            UNION
            SELECT salesman_id FROM van_return_data
            UNION
            SELECT salesman_id FROM return_data            
        )
        SELECT
            s.salesman_id,
            {SALESMAN_CODE}
            {SALESMAN_NAME}
            {FINAL_SELECT}
        FROM salesmen s
        LEFT JOIN unload_data u ON u.salesman_id = s.salesman_id
        LEFT JOIN load_data l ON l.salesman_id = s.salesman_id
        LEFT JOIN sales_data sd ON sd.salesman_id = s.salesman_id
        LEFT JOIN van_return_data vr ON vr.salesman_id = s.salesman_id
        LEFT JOIN return_data r ON r.salesman_id = s.salesman_id
    """
    return query


@router.post("/inventory-movement-tableview")
def inventory_movement_tableview(payload:InventoryMovementRequest,request:Request, page: int = Query(1, ge=1), db:Session = Depends(get_db)):
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
