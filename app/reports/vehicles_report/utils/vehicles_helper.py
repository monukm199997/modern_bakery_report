from app.reports.vehicles_report.schemas.vehicles_schema import VehiclesRequest
from app.utils.helper import validate_mandatory, choose_granularity


def build_query_parts(payload: VehiclesRequest):
    where_fragments = []
    params = {}

    where_fragments.append("tt.trip_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids
  
    if payload.route_ids:
        where_fragments.append("rt.id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    if payload.salesman_ids:
        where_fragments.append("s.id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids
    
    return where_fragments, params


def prepare_dashboard_context(payload: VehiclesRequest):
    validate_mandatory(payload)

    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )
    where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)

    return {
        "granularity": granularity,
        "period_label_sql": period_label_sql,
        "order_by_sql": order_by_sql,
        "where_sql": where_sql,
        "params": params,
    }