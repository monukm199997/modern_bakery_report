from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.reports.group_level_report.schemas.group_schema import GroupLevelTableRequest
from app.reports.group_level_report.utils.group_level_helper import (
    prepare_group_level_context,
    _build_group_level_query,
)

router = APIRouter(tags=["Group Level Report"])


def get_group_level_page(
    payload: GroupLevelTableRequest,
    db: Session,
):
    ctx = prepare_group_level_context(payload)

    page = payload.page
    page_size = payload.page_size

    params = dict(ctx["params"])
    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size

    query = _build_group_level_query(
        ctx,
        extra_select="COUNT(*) OVER() AS total_records",
        tail="LIMIT :limit OFFSET :offset",
    )
    result = db.execute(text(query), params).mappings().all()
    rows = [dict(row) for row in result]

    total_records = rows[0]["total_records"] if rows else 0
    for row in rows:
        row.pop("total_records", None)

    total_pages = (total_records + page_size - 1) // page_size

    return {
        "pagination": {
            "total_records": total_records,
            "page_size": page_size,
            "total_pages": total_pages,
            "page": page,
            "next_page": page + 1 if page < total_pages else None,
            "previous_page": page - 1 if page > 1 else None,
        },
        "data": rows,
    }


@router.post("/group-level/table")
def group_level_table(
    payload: GroupLevelTableRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, db, current_user)
    return get_group_level_page(payload, db)
