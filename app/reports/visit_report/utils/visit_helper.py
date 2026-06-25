from app.reports.visit_report.schemas.visit_schema import VisitPlanRequest
from app.utils.helper import validate_mandatory


def build_query_parts(payload: VisitPlanRequest):
    where_fragments = []
    params = {}

    where_fragments.append("DATE(vp.visit_start_time) BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("vp.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    return where_fragments, params

def prepare_dashboard_context(payload):
    validate_mandatory(payload)

    where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    return {
        "where_sql": where_sql,
        "params": params,
    }