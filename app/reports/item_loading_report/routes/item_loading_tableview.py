from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.item_loading_report.schemas.item_loading_schema import ItemLoadingRequest
from app.reports.item_loading_report.utils.item_loading_helper import prepare_dashboard_context
from app.utils.constant import ROWS_PER_PAGE
from app.reports.item_loading_report.utils.item_loading_sql_query_helper import (
    ORDER_DATA_JOIN,
    RECIEVE_DATA_JOIN,
    FINAL_SELECT,
    DISPLAY_UOM,
    DISPLAY_UPC,
)

router = APIRouter(tags=["Item Loading Report"], dependencies=[Depends(get_current_user)])

def build_item_loading_query(ctx, *, order_by: bool = False):
    query = f"""
        WITH ordered_data AS (
            SELECT
                aoh.salesman_id
                {ctx["order_select_sql"]},
                {DISPLAY_UOM} AS uom,
                {DISPLAY_UPC} AS upc,
                {ctx["order_value"]} AS ordered_qty,
                MAX(aoh.comment) AS remarks_by_stores
            FROM {ORDER_DATA_JOIN}
            {ctx["order_join_sql"]}
            WHERE {ctx["order_where_sql"]}
            GROUP BY {ctx["order_group_sql"]}
        ),
        received_data AS (
            SELECT
                lh.salesman_id
                {ctx["receive_select_sql"]},
                {ctx["load_volue"]} AS received_qty
            FROM {RECIEVE_DATA_JOIN}
            {ctx["receive_join_sql"]}
            WHERE {ctx["receive_where_sql"]}
            GROUP BY {ctx["receive_group_sql"]}
        )
        SELECT
            s.id AS salesman_id,
            s.osa_code AS salesman_code,
            s.name AS saleman
            {ctx["final_select_sql"]},
            o.uom,
            o.upc,
            {FINAL_SELECT}
        FROM ordered_data o
        LEFT JOIN received_data r ON {ctx["join_condition_sql"]}
        LEFT JOIN salesman s ON s.id = o.salesman_id
    """

    if order_by:
        query += """
        ORDER BY s.osa_code, s.name
        """

    return query



@router.post("/item-loading-tableview")
def get_item_loading_rows( 
    request: Request,
    payload: ItemLoadingRequest,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    ):
    ctx = prepare_dashboard_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE
    ctx["params"]["limit"] = ROWS_PER_PAGE
    ctx["params"]["offset"] = offset

    base_query = build_item_loading_query(ctx)
    count_query = f"""
        SELECT COUNT(*) 
        FROM ({base_query}) AS count_data
    """

    data_query = f"""
        {base_query}
        ORDER BY s.osa_code, s.name
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