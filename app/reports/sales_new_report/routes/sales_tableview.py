from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_new_report.schemas.sales_schema import SalesReportRequest
from app.reports.sales_new_report.utils.sales_helper import prepare_sales_report_context,sales_quantity, return_quantity

router = APIRouter(tags=["Sales New Report"], dependencies=[Depends(get_current_user)])

quantity = sales_quantity()
re_quantity = return_quantity()

@router.post("/sales-new-tableview")
def get_sales_report_table(payload: SalesReportRequest, db: Session = Depends(get_db)):
    ctx = prepare_sales_report_context(payload)

    query = f"""
        WITH sales_data AS (
            SELECT
                {ctx["sales_select_sql"]}
                COALESCE(SUM(id.net_total), 0) AS gross_sales_amount,
                COALESCE({quantity}, 0) AS gross_sales_qty
            FROM sales_documents_header ih
            JOIN sales_documents_detail id ON id.header_id = ih.id
            LEFT JOIN salesman sm ON sm.id = ih.salesman_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            JOIN users sw ON sw.id = sm.superwiser_id AND sw.role = 108
            LEFT JOIN items i ON i.id = id.item_id
            LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            LEFT JOIN tbl_route rt ON rt.id = ih.route_id
            WHERE {ctx["sales_where_sql"]}
            {ctx["sales_group_by_sql"]}
        ),

        return_data AS (
            SELECT
                {ctx["return_select_sql"]}
                COALESCE(SUM(rd.net_total), 0) AS return_amount,
                COALESCE({re_quantity}, 0) AS return_qty
            FROM return_header rh
            JOIN return_details rd ON rd.header_id = rh.id
            LEFT JOIN salesman sm ON sm.id = rh.salesman_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = rd.item_id
                AND iu.uom_id = rd.uom_id
            JOIN users sw ON sw.id = sm.superwiser_id AND sw.role = 108
            LEFT JOIN items i ON i.id = rd.item_id
            LEFT JOIN agent_customers ac ON ac.id = rh.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            LEFT JOIN tbl_route rt ON rt.id = rh.route_id
            WHERE {ctx["return_where_sql"]}
            {ctx["return_group_by_sql"]}
        )

        SELECT
            {ctx["final_select_sql"]}
        FROM sales_data s
        FULL OUTER JOIN return_data r
            ON {ctx["join_on_sql"]}
    """

    rows = db.execute(text(query), ctx["params"]).mappings().all()

    return {
        "search_type": payload.search_type,
        "drill_down_fields": payload.drill_down_fields or [],
        "total_records": len(rows),
        "data": [dict(row) for row in rows],
    }