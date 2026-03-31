from app.reports.customer_load_unload.schemas.schema import LoadUnloadReportRequest
def sales_query_parts(payload: LoadUnloadReportRequest):
    where_fragments = []
    params = {}

    where_fragments.append("ih.invoice_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.display_quantity and payload.display_quantity.lower() == "without_free_good":
        where_fragments.append("id.item_total <> 0")

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    if payload.salesman_ids:
        where_fragments.append("ih.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids


    return where_fragments, params


def load_query_parts(payload: LoadUnloadReportRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("lh.created_at BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.display_quantity and payload.display_quantity.lower() == "without_free_good":
        where_fragments.append("ld.price <> 0")

    if payload.route_ids:
        where_fragments.append("lh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    if payload.salesman_ids:
        where_fragments.append("ih.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params

