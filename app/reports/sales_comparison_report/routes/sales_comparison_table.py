from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.common.apply_payload_permissions import apply_payload_permissions
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)
from app.reports.sales_comparison_report.utils.sales_comparison_helper import (
    prepare_comparison_context,
)

router = APIRouter(tags=["Sales Comparison Report"], dependencies=[Depends(get_current_user)],)


@router.post("/table")
def sales_comparison_table(
    payload: SalesComparisonRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_comparison_context(payload)

    query = f"""
        SELECT
            {ctx["select_sql"]}
        {ctx["from_sql"]}
        WHERE {ctx["where_sql"]}
        {ctx["group_by_sql"]}
    """

    rows = db.execute(text(query), ctx["params"]).mappings().all()

    return {
        "search_type": payload.search_type,
        "drill_down_fields": payload.drill_down_fields or [],
        "periods": {
            "current": {
                "from_date": payload.current_from_date,
                "to_date": payload.current_to_date,
            },
            "previous": {
                "from_date": payload.previous_from_date,
                "to_date": payload.previous_to_date,
            },
        },
        "total_records": len(rows),
        "data": [dict(row) for row in rows],
    }
