from app.reports.customer_sales_report.schemas.schemas import CustomerSalesReportRequest
from app.common.helper import validate_mandatory, choose_granularity, quantity_expr_sql


def build_query_parts(payload: CustomerSalesReportRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("ih.invoice_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.display_quantity and payload.display_quantity.lower() == "without_free_good":
        where_fragments.append("id.item_total <> 0")

    if payload.company_ids:
        joins.append("JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("ih.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params




def prepare_dashboard_context(payload: CustomerSalesReportRequest):
    validate_mandatory(payload)

    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )

    joins, where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity"
        else "SUM(id.item_total)"
    )

    return {
        "granularity": granularity,
        "period_label_sql": period_label_sql,
        "order_by_sql": order_by_sql,
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "value_expr": value_expr,
    }

