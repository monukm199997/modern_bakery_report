from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.item_loading_report.schemas.item_loading_schema import ItemLoadingRequest
from app.reports.item_loading_report.utils.item_loading_helper import prepare_dashboard_context
from app.utils.constant import ROWS_PER_PAGE

router = APIRouter(tags=["Item Loading Report"], dependencies=[Depends(get_current_user)])
@router.post("/item-loading-tableview")
def item_report_tableview(
    request: Request,
    payload: ItemLoadingRequest,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    ctx = prepare_dashboard_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE
    ctx["params"]["limit"] = ROWS_PER_PAGE
    ctx["params"]["offset"] = offset

    base_query = f"""
        WITH ordered_data AS (
            SELECT
                aoh.salesman_id,
                {ctx['order_value']} AS ordered_qty,
                MAX(aoh.comment) AS remarks_by_stores
            FROM agent_order_headers aoh
            LEFT JOIN agent_order_details aod
                ON aod.header_id = aoh.id
                AND aod.deleted_at IS NULL
            JOIN agent_customers ac
                ON ac.id = aoh.customer_id
                AND ac.is_driver = 1
            LEFT JOIN salesman s
                ON s.id = aoh.salesman_id
            LEFT JOIN tbl_route rt
                ON rt.id = aoh.route_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = aod.item_id
                AND iu.uom_id = aod.uom_id
            WHERE {ctx['order_where_sql']}
            GROUP BY aoh.salesman_id
        ),
        received_data AS (
            SELECT
                lh.salesman_id,
                {ctx['load_volue']} AS received_qty
            FROM tbl_load_header lh
            LEFT JOIN tbl_load_details ld
                ON ld.header_id = lh.id
                AND ld.deleted_at IS NULL
            LEFT JOIN salesman s2
                ON s2.id = lh.salesman_id
            LEFT JOIN tbl_route rt2
                ON rt2.id = lh.route_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = ld.item_id
                AND iu.uom_id = ld.uom
            WHERE {ctx["receive_where_sql"]}
            GROUP BY lh.salesman_id
        )
        SELECT
            s.id AS salesman_id,
            s.osa_code AS salesman_code,
            s.name AS salesman_name,
            COALESCE(o.ordered_qty, 0) AS salesman_ordered_qty,
            COALESCE(r.received_qty, 0) AS received_qty,
            COALESCE(o.ordered_qty, 0) - COALESCE(r.received_qty, 0) AS diff,
            o.remarks_by_stores
        FROM ordered_data o
        LEFT JOIN received_data r
            ON r.salesman_id = o.salesman_id
        LEFT JOIN salesman s
            ON s.id = o.salesman_id
    """

    count_query = f"""
        SELECT COUNT(*) AS total_rows
        FROM (
            {base_query}
        ) AS count_data
    """

    data_query = f"""
        {base_query}
        ORDER BY salesman_code, salesman_name
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