from fastapi import APIRouter, Depends, Query, Request
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
from app.utils.constant import ROWS_PER_PAGE

router = APIRouter(tags=["Sales Comparison Report"], dependencies=[Depends(get_current_user)],)


@router.post("/table")
def sales_comparison_table(
    payload: SalesComparisonRequest,
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_comparison_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE

    query = f"""
        SELECT
            {ctx["select_sql"]}
        {ctx["from_sql"]}
        WHERE {ctx["where_sql"]}
        {ctx["group_by_sql"]}
        LIMIT :limit
        OFFSET :offset
    """
    params = {
        **ctx["params"],
        "limit": ROWS_PER_PAGE,
        "offset": offset,
    }

    rows = db.execute(text(query), params).mappings().all()

    count_query = f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                {ctx["select_sql"]}
            {ctx["from_sql"]}
            WHERE {ctx["where_sql"]}
            {ctx["group_by_sql"]}
        ) AS count_data
    """

    total_rows = db.execute(text(count_query), ctx["params"]).scalar() or 0
    total_pages = (
        (total_rows + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE
        if total_rows > 0
        else 0
    )
    base_url = str(request.url).split("?")[0]

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
        "pagination": {
            "total_rows": total_rows,
            "total_pages": total_pages,
            "current_page": page,
            "page_size": ROWS_PER_PAGE,
            "next_page": (
                f"{base_url}?page={page + 1}"
                if page < total_pages
                else None
            ),
            "prev_page": (
                f"{base_url}?page={page - 1}"
                if page > 1
                else None
            ),
        },
        "data": [dict(row) for row in rows],
    }
