from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context, get_level_config
from app.utils.constant import ROWS_PER_PAGE
from app.reports.sales_report.utils.sql_query_helper import JOINS_SQL
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions

router = APIRouter(tags=["Sales Report"])

@router.post("/sales-report-tableview")
def sales_report_tableview(
    payload: SalesReportRequest,
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    ):
    # payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE

    level_config = get_level_config(payload)
    level_id_col = level_config["level_id_col"]
    level_name_col = level_config["level_name_col"]
    level_label = level_config["level_label"]
    level_join = level_config["level_join"]
   
    joins = [j.strip() for j in ctx["join_sql"].split("\n") if j.strip()]
    joins.extend([j.strip() for j in level_join.split("\n") if j.strip()])
    joins = list(dict.fromkeys(joins))
    join_sql = "\n".join(joins)

    from_sql = f"""
        {JOINS_SQL}
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

