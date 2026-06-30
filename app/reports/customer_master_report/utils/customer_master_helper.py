from app.reports.customer_master_report.schemas.customer_master_schema import CustomerMasterRequest
from app.utils.helper import validate_mandatory


def build_query_parts(payload: CustomerMasterRequest):
    where_fragments = []
    params = {}

    where_fragments.append("s.company_id = ANY(:company_ids)")
    params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("ac.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ac.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    return where_fragments, params

def prepare_dashboard_context(payload):

    where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    return {
        "where_sql": where_sql,
        "params": params,
    }