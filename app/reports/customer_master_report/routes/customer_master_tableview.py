from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.utils.constant import ROWS_PER_PAGE
from app.reports.customer_master_report.schemas.customer_master_schema import CustomerMasterRequest
from app.reports.customer_master_report.utils.customer_master_helper import prepare_dashboard_context
from app.reports.customer_master_report.utils.customer_master_sql_query import SELECT_QUERY, JOIN_QUERY

router = APIRouter(tags=["Customer Master Report"], dependencies=[Depends(get_current_user)])

@router.post("/customer-master-tableview")
def customer_master_tableview(
    payload: CustomerMasterRequest, 
    request: Request, 
    page: int = Query(1, ge=1), 
    db:Session = Depends(get_db),
    current_user = Depends(get_current_user)
    ):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_dashboard_context(payload)
    
    base_sql= f"""
        {JOIN_QUERY}
        WHERE {ctx['where_sql']}
    """
    count_sql = f"""
            SELECT COUNT(*)
            {base_sql}
        """
    total_rows = db.execute(text(count_sql), ctx['params']).scalar() or 0
    offset = (page - 1) * ROWS_PER_PAGE
    ctx['params']["limit"] = ROWS_PER_PAGE
    ctx['params']["offset"] = offset

    query = f"""
        SELECT
            {SELECT_QUERY}
        {base_sql}
        ORDER BY dateof_creation
        LIMIT :limit OFFSET :offset
    """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    total_pages = (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
    base_url = str(request.url).split("?")[0]

    return {
        "total_rows": total_rows,
        "total_pages": total_pages,
        "current_page": page,
        "next_page": f"{base_url}?page={page + 1}" if page < total_pages else None,
        "previous_page": f"{base_url}?page={page - 1}" if page > 1 else None,
        "rows": result,
    }