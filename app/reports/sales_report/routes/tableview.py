from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context

router = APIRouter(tags=["Sales Report - TableView"])

@router.post("/sales-report-tableview")
def sales_report_tableview(
    payload: SalesReportRequest,
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
    ):
    ctx = prepare_dashboard_context(payload)

    ROWS_PER_PAGE = 50
    offset = (page - 1) * ROWS_PER_PAGE

    if payload.item_ids:
        level_id_col = "id.item_id"
        level_name_col = "it.name"
        level_label = "item_name"
        level_join = ""

    elif payload.item_category_ids:
        level_id_col = "it.category_id"
        level_name_col = "cat.category_name"
        level_label = "item_category"
        level_join = ""

    elif payload.customer_channel_ids:
        level_id_col = "ac.outlet_channel_id"
        level_name_col = "ch.outlet_channel"
        level_label = "channel_name"
        level_join = """
            
            LEFT JOIN outlet_channel ch ON ch.id = ac.outlet_channel_id
        """

    elif payload.salesman_ids:
        level_id_col = "ih.salesman_id"
        level_name_col = "sm.name"
        level_label = "salesman_name"
        level_join = "LEFT JOIN salesman sm ON sm.id = ih.salesman_id"

    elif payload.route_ids:
        level_id_col = "ih.route_id"
        level_name_col = "rt.route_name"
        level_label = "route_name"
        level_join = ""

    elif payload.region_ids:
        level_id_col = "rt.region_id"
        level_name_col = "r.region_name"
        level_label = "region_name"
        level_join = """
            LEFT JOIN tbl_region r ON r.id = rt.region_id
        """

    elif payload.company_ids:
        level_id_col = "ih.company_id"
        level_name_col = "c.company_name"
        level_label = "company_name"
        level_join = "LEFT JOIN tbl_company c ON c.id = ih.company_id"

    else:
        level_id_col = "ih.company_id"
        level_name_col = "c.company_name"
        level_label = "company_name"
        level_join = "LEFT JOIN tbl_company c ON c.id = ih.company_id"

    joins = [j.strip() for j in ctx["join_sql"].split("\n") if j.strip()]
    joins.extend([j.strip() for j in level_join.split("\n") if j.strip()])
    joins = list(dict.fromkeys(joins))
    join_sql = "\n".join(joins)

    from_sql = f"""
        FROM invoice_headers ih
        JOIN invoice_details id ON id.header_id = ih.id
        JOIN items it ON it.id = id.item_id
        LEFT JOIN item_categories cat ON cat.id = it.category_id
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        {join_sql}
    """

    where_sql = f"WHERE {ctx['where_sql']}"

    data_sql = f"""
        SELECT
            it.code AS item_code,
            it.name AS item_name,
            cat.category_name AS item_category,
            ih.invoice_date,
            {level_name_col} AS {level_label},
            {ctx["value_expr"]} AS value
        {from_sql}
        LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
        {where_sql}
        GROUP BY
            id.item_id,
            ih.invoice_date,
            {level_id_col},
            {level_name_col},
            it.code,
            it.name,
            cat.category_name
        ORDER BY ih.invoice_date, it.name
        LIMIT :limit OFFSET :offset
    """


    count_sql = f"""
        SELECT COUNT(*) FROM (
            SELECT
                id.item_id,
                ih.invoice_date,
                {level_id_col}
            {from_sql}
            {where_sql}
            GROUP BY
                id.item_id,
                ih.invoice_date,
                {level_id_col}
        ) t
    """

    params = dict(ctx["params"])
    params["limit"] = ROWS_PER_PAGE
    params["offset"] = offset
    rows = db.execute(text(data_sql), params).fetchall()
    rows_data = [dict(r._mapping) for r in rows]

    total_rows = db.execute(text(count_sql), ctx["params"]).scalar()
    total_pages = (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE

    base_url = str(request.url).split("?")[0]
    return {
        "pagination": {
            "total_rows": total_rows,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": ROWS_PER_PAGE,
            "next_page": f"{base_url}?page={page + 1}" if page < total_pages else None,
            "prev_page": f"{base_url}?page={page - 1}" if page > 1 else None,
        },
        "rows_data": rows_data
    }

