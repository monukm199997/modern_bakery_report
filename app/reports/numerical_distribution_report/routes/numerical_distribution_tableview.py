from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.reports.numerical_distribution_report.schemas.numerical_distribution_schema import (
    NumericalDistributionRequest,
)

from app.reports.numerical_distribution_report.utils.numerical_distribution_helper import (
    prepare_numerical_distribution_context,
)
from app.utils.constant import ROWS_PER_PAGE

router = APIRouter(tags=["Numerical Distribution Report"])

@router.post("/numerical-distribution-tableview")
def numerical_distribution_tableview(
    request: Request,
    payload: NumericalDistributionRequest,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_numerical_distribution_context(payload)

    offset = (page - 1) * ROWS_PER_PAGE

    count_sql = f"""
    SELECT COUNT(*)
    FROM
    (
        SELECT
            {ctx["select"]}
        {ctx["from"]}
        WHERE
            {ctx["where"]}
        GROUP BY
            {ctx["group_by"]}
    ) t
    """
    total_records = db.execute(text(count_sql),ctx["params"],).scalar()

    sql = f"""
        SELECT
            {ctx["select"]}
        {ctx["from"]}
        WHERE
            {ctx["where"]}
        GROUP BY
            {ctx["group_by"]}
        ORDER BY
            {ctx["order_by"]}
        LIMIT :limit OFFSET :offset
    """

    params = dict(ctx["params"])
    params["limit"] = ROWS_PER_PAGE
    params["offset"] = offset

    rows = db.execute(text(sql),params,).mappings().all()

    data = [dict(r) for r in rows]

    total_pages = ((total_records + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE if total_records else 0)
    base_url = str(request.url).split("?")[0]
    next_page = None
    previous_page = None
    if page < total_pages:
        next_page = f"{base_url}?page={page + 1}&page_size={ROWS_PER_PAGE}"

    if page > 1:
        previous_page = f"{base_url}?page={page - 1}&page_size={ROWS_PER_PAGE}"

    return {
        "pagination": {
            "total_records": total_records,
            "page_size": ROWS_PER_PAGE,
            "total_pages": total_pages,
            "page": page,
            "next_page": next_page,
            "previous_page": previous_page,
        },
        "data": data,
    }