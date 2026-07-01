from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_new_report.schemas.sales_schema import SalesReportRequest
from app.reports.sales_new_report.utils.sales_helper import prepare_sales_report_context
router = APIRouter(tags=["Sales New Report"], dependencies=[Depends(get_current_user)])



@router.post("/sales-new-tableview")
def get_sales_report_table(payload: SalesReportRequest, db: Session = Depends(get_db)):
    ctx = prepare_sales_report_context(payload)

    query = f"""
        SELECT
            {ctx["select_sql"]}
        FROM sales_documents_header sdh
        JOIN sales_documents_detail sdd ON sdd.header_id = sdh.id
        LEFT JOIN salesman sm ON sm.id = sdh.salesman_id
        LEFT JOIN item_uoms iu
                ON iu.item_id = sdd.item_id
                AND iu.uom_id = sdd.uom
        LEFT JOIN users sup ON sup.id = sm.superwiser_id AND sup.role = 108
        LEFT JOIN items i ON i.id = sdd.item_id
        LEFT JOIN agent_customers ac ON ac.id = sdh.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN tbl_route rt ON rt.id = sdh.route_id
        WHERE {ctx["where_sql"]}
        {ctx["group_by_sql"]}
    """
    rows = db.execute(text(query), ctx["params"]).mappings().all()
    return {
        "search_type": payload.search_type,
        "drill_down_fields": payload.drill_down_fields or [],
        "total_records": len(rows),
        "data": [dict(row) for row in rows],
    }