from app.reports.team_master_report.schemas.team_master_schema import TeamMasterRequest
from app.utils.helper import validate_mandatory


def build_query_parts(payload: TeamMasterRequest):
    where_fragments = []
    params = {}

    where_fragments.append("s.company_id = ANY(:company_ids)")
    params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids
        
    return where_fragments, params

def prepare_dashboard_context(payload):

    where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    return {
        "where_sql": where_sql,
        "params": params,
    }