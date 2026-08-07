from app.reports.sales_dashboard.schemas.schemas import SalesDashboardKpisRequest
from datetime import datetime
from sqlalchemy import text
from app.reports.sales_dashboard.utils.sql_query_helper import (
    SALES_ITEM_JOINS_SQL,
    SALES_REGION_JOINS_SQL,
    SALES_BASE_SQL,
    SALES_OVERVIEW_JOIN_SQL,
    RETURN_ITEM_JOINS_SQL,
    RETURN_REGION_JOINS_SQL,
    RETURN_CHANNEL_JOINS_SQL,
    TREND_DATA_SELECT_SQL,
    PREVIOUS_WEEK_WHERE_SQL,
    SELECT,
    FROM_CLAUSE,
    SALES_CUSTOMER_CHANNEL_JOIN_SQL,
    TOTAL_RETURN_REVENUE,
    TOTAL_RETURN_VOLUME,
    TOTAL_SALES_REVENUE,
    TOTAL_SALES_VOLUME,
    ORDER_VOLUME,
    ORDER_REVENUE,
    DELIVERY_VOLUME,
    DELIVERY_REVENUE,
    LOAD_QUANTITY,
    UNLOAD_QUANTITY,
)


def get_gross_sales(payload):
    sales_revenue = TOTAL_SALES_REVENUE
    sales_volume = TOTAL_SALES_VOLUME
    if payload.search_type.lower() == "quantity":
        return sales_volume
    return sales_revenue

def get_returns(payload):
    return_revenue = TOTAL_RETURN_REVENUE
    return_volume = TOTAL_RETURN_VOLUME
    if payload.search_type.lower() == "quantity":
        return return_volume
    return return_revenue

def get_grossSales_returns(payload):
    sales = get_gross_sales(payload)
    returns = get_returns(payload)
    net_sales = f"({sales} - {returns})"
    return sales, returns, net_sales

def sales_build_query_parts(payload: SalesDashboardKpisRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("ih.invoice_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params

def prepare_dashboard_context(payload: SalesDashboardKpisRequest):

    joins, where_fragments, params = sales_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    gross_sales, returns, net_sales = get_grossSales_returns(payload)

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "gross_sales": gross_sales,
        "returns": returns,
        "net_sales": net_sales,
    }

def order_build_query_parts(payload: SalesDashboardKpisRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("oh.created_at BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = oh.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = oh.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("oh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params

def order_prepare_dashboard_context(payload: SalesDashboardKpisRequest):

    joins, where_fragments, params = order_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = ORDER_VOLUME
    revenue = ORDER_REVENUE
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else revenue
    )

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "value_expr": value_expr,
    }

def delivery_build_query_parts(payload: SalesDashboardKpisRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("dh.created_at BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = dh.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = dh.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("dh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params

def delivery_prepare_dashboard_context(payload: SalesDashboardKpisRequest):

    joins, where_fragments, params = delivery_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = DELIVERY_VOLUME
    revenue = DELIVERY_REVENUE
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else revenue
    )

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "value_expr": value_expr,
    }

def load_build_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("lh.accept_time >= :from_date AND lh.accept_time < (CAST(:to_date AS DATE) + INTERVAL '1 day')")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = lh.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = lh.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("lh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params

def load_prepare_dashboard_context(payload: SalesDashboardKpisRequest):

    joins, where_fragments, params = load_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = LOAD_QUANTITY
    
    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "quantity": quantity,
    }

def unload_build_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("ulh.unload_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ulh.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ulh.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ulh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params


def unload_prepare_dashboard_context(payload: SalesDashboardKpisRequest):
  
    joins, where_fragments, params = unload_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = UNLOAD_QUANTITY
    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "quantity": quantity,
    }

def get_segment_config(segment_by: str):
    configs = {
        "customer_channel": {
            "sales_join": f"""
                {SALES_CUSTOMER_CHANNEL_JOIN_SQL}
            """,
            "return_join": f"""
                {RETURN_CHANNEL_JOINS_SQL}
            """,
            "field": "oc.outlet_channel",
        },
        "product_category": {
            "sales_join": f"""
                {SALES_ITEM_JOINS_SQL}
            """,
            "return_join": f"""
                {RETURN_ITEM_JOINS_SQL}
            """,
            "field": "ic.category_name",
        },
        "sales_region": {
            "sales_join": f"""
                {SALES_REGION_JOINS_SQL}
            """,
            "return_join": f"""
               {RETURN_REGION_JOINS_SQL}
            """,
            "field": "r.region_name",
        },
        "route": {
            "sales_join": """
                LEFT JOIN tbl_route sales_rt ON sales_rt.id = ih.route_id
            """,

            "return_join": """
                LEFT JOIN tbl_route ret_rt ON ret_rt.id = rh.route_id
            """,
            "field": "sales_rt.route_name",
            "return_field": "ret_rt.route_name"
        },
    }
    return configs[segment_by]

def prepare_channel_performance_context(payload):

    sales_ctx = prepare_dashboard_context(payload)
    segment = get_segment_config(payload.segment_by)

    return {
        "sales_ctx": sales_ctx,
        "segment": segment
    }

def get_sales_performance_data(db, payload):

    ctx = prepare_channel_performance_context(payload)
    sales_ctx = ctx["sales_ctx"]
    segment = ctx["segment"]

    query = f"""
        WITH sales_data AS (
            SELECT
                COALESCE(
                    {segment['field']},
                    'Others'
                ) AS segment,
                {sales_ctx['gross_sales']} AS sales,
                {sales_ctx['returns']} AS returns
            {SALES_BASE_SQL}
            {segment['sales_join']}
            {sales_ctx['join_sql']}
            WHERE {sales_ctx['where_sql']}
            GROUP BY 1
        ),
        current_week_sales AS (
            SELECT
                COALESCE(
                    {segment['field']},
                    'Others'
                ) AS segment,
                {sales_ctx['gross_sales']} AS current_sales
            {SALES_OVERVIEW_JOIN_SQL}
            {segment['sales_join']}
            {sales_ctx['join_sql']}
            WHERE ih.invoice_date >= CURRENT_DATE - INTERVAL '7 day'
            GROUP BY 1
        ),
        previous_week_sales AS (
            SELECT
                COALESCE(
                    {segment['field']},
                    'Others'
                ) AS segment,
                {sales_ctx['gross_sales']} AS previous_sales
            {SALES_OVERVIEW_JOIN_SQL}
            {segment['sales_join']}
            {sales_ctx['join_sql']}
            {PREVIOUS_WEEK_WHERE_SQL}
            GROUP BY 1
        ),
        trend_data AS (
            {TREND_DATA_SELECT_SQL}
            ) AS trend_7d
            FROM (
                SELECT
                    COALESCE(
                        {segment['field']},
                        'Others'
                    ) AS segment,
                    DATE(ih.invoice_date) AS sales_date,
                    {sales_ctx['gross_sales']} AS daily_sales
                {SALES_OVERVIEW_JOIN_SQL}
                {segment['sales_join']}
                {sales_ctx['join_sql']}
                WHERE ih.invoice_date >= CURRENT_DATE - INTERVAL '7 day'
                GROUP BY 1, 2
            ) x
            GROUP BY 1
        )
        SELECT
          {SELECT}
        {FROM_CLAUSE}
    """
    params = {**sales_ctx['params'], 'limit': payload.limit}

    rows = db.execute(text(query),params).fetchall()
    segments = [dict(r._mapping) for r in rows]
    total_sales = sum(x['sales'] for x in segments)
    leader = segments[0] if segments else None

    response = {
        "summary": {
            "leader": leader['segment'] if leader else None,

            "top_sales": leader['sales'] if leader else 0,
            
            "avg_returns": round(
                sum(x['returns'] for x in segments)
                / len(segments),
                2
            ) if segments else 0,

            "concentration": (
                leader['share_percentage']
                if leader else 0
            )
        },

        "segments": segments
    }

    return response
