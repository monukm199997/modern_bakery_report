from fastapi import APIRouter, Depends, Query,Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.reports.team_master_report.schemas.team_master_schema import TeamMasterRequest
from app.reports.team_master_report.utils.team_master_helper import prepare_dashboard_context
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.utils.constant import ROWS_PER_PAGE
router = APIRouter(tags=["Team Master Report"], dependencies=[Depends(get_current_user)])

@router.post("/team-master-tableview")
def get_team_master_tableview(
    payload: TeamMasterRequest,
    request: Request, 
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)

    base_sql = f"""
        FROM salesman s
        LEFT JOIN tbl_route rt ON s.route_id = rt.id
        LEFT JOIN tbl_vehicle v ON v.id = rt.vehicle_id
        LEFT JOIN tbl_region r ON rt.region_id = r.id
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
            v.vehicle_code,
            v.number_plat,
            rt.route_code,
            rt.route_name,
            s.osa_code AS salesman_code,
            s.name AS salesman_name,
            s.dateof_join,
            r.region_name
        {base_sql}
        ORDER BY rt.route_code, s.osa_code
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