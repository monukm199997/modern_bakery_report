from app.reports.sales_dashboard.schemas.schemas import SalesDashboardKpisRequest
from app.utils.helper import validate_mandatory, choose_granularity, quantity_expr_sql
from datetime import datetime
from sqlalchemy import text
from app.reports.customer_sales_report.utils.sql_query_helper import (
    OPTIONAL_JOINS_SQL_1,
)
from app.reports.sales_dashboard.utils.sql_query_helper import (
    SALES_ITEM_JOINS_SQL,
    SALES_REGION_JOINS_SQL,
    SALES_BASE_SQL,
    SALES_BASE_SQL_1,
    RETURN_ITEM_JOINS_SQL,
    RETURN_REGION_JOINS_SQL,
    RETURN_BASE_SQL,
    RETURN_CHANNEL_JOINS_SQL,
    TREND_DATA_SELECT_SQL,
    PREVIOUS_WEEK_WHERE_SQL,
    SELECT,
    FROM_CLAUSE,
)


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
    validate_mandatory(payload)

    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )

    joins, where_fragments, params = sales_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else "ROUND(SUM(id.item_total)::numeric, 2)"
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

def return_build_query_parts(payload: SalesDashboardKpisRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("rh.created_at BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = rh.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = rh.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("rh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params

def return_quantity_expr_sql():
    return """
    ROUND(
        SUM(
            rd.item_quantity 
        )::numeric,
        2
    )
    """

def return_prepare_dashboard_context(payload: SalesDashboardKpisRequest):
    validate_mandatory(payload)

    joins, where_fragments, params = return_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = return_quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else "ROUND(SUM(rd.total)::numeric, 2)"
    )

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "value_expr": value_expr,
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

def order_quantity_expr_sql():
    return """
    ROUND(
        SUM(
            od.quantity 
        )::numeric,
        2
    )
    """

def order_prepare_dashboard_context(payload: SalesDashboardKpisRequest):
    validate_mandatory(payload)

    joins, where_fragments, params = order_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = order_quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else "SUM(od.total)"
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

def delivery_quantity_expr_sql():
    return """
    ROUND(
        SUM(
            dd.quantity 
        )::numeric,
        2
    )
    """

def delivery_prepare_dashboard_context(payload: SalesDashboardKpisRequest):
    validate_mandatory(payload)

    joins, where_fragments, params = delivery_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = delivery_quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else "ROUND(SUM(dd.total)::numeric, 2)"
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

    where_fragments.append("lh.created_at BETWEEN :from_date AND :to_date")
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

def load_quantity_expr_sql():
    return """
    ROUND(
        SUM(
            ld.qty 
        )::numeric,
        2
    )
    """

def load_prepare_dashboard_context(payload: SalesDashboardKpisRequest):
    validate_mandatory(payload)

    joins, where_fragments, params = load_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = load_quantity_expr_sql()
    

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

def unload_quantity_expr_sql():
    return """
    ROUND(
        SUM(
            uld.qty 
        )::numeric,
        2
    )
    """

def unload_prepare_dashboard_context(payload: SalesDashboardKpisRequest):
    validate_mandatory(payload)

    joins, where_fragments, params = unload_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = unload_quantity_expr_sql()
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
                {OPTIONAL_JOINS_SQL_1}
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
    return_ctx = return_prepare_dashboard_context(payload)
    segment = get_segment_config(payload.segment_by)

    return {
        "sales_ctx": sales_ctx,
        "return_ctx": return_ctx,
        "segment": segment
    }

def get_sales_performance_data(db, payload):

    ctx = prepare_channel_performance_context(payload)
    sales_ctx = ctx["sales_ctx"]
    return_ctx = ctx["return_ctx"]
    segment = ctx["segment"]

    query = f"""
        WITH sales_data AS (
            SELECT
                COALESCE(
                    {segment['field']},
                    'Others'
                ) AS segment,
                {sales_ctx['value_expr']} AS sales
            {SALES_BASE_SQL}
            {segment['sales_join']}
            {sales_ctx['join_sql']}
            WHERE {sales_ctx['where_sql']}
            GROUP BY 1
        ),
        return_data AS (
            SELECT
                COALESCE(
                    {segment.get('return_field', segment['field'])},
                    'Others'
                ) AS segment,
                {return_ctx['value_expr']} AS returns
            {RETURN_BASE_SQL}
            {segment['return_join']}
            {return_ctx['join_sql']}
            WHERE {return_ctx['where_sql']}
            GROUP BY 1
        ),
        current_week_sales AS (
            SELECT
                COALESCE(
                    {segment['field']},
                    'Others'
                ) AS segment,
                {sales_ctx['value_expr']} AS current_sales
            {SALES_BASE_SQL_1}
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
                {sales_ctx['value_expr']} AS previous_sales
            {SALES_BASE_SQL_1}
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
                    {sales_ctx['value_expr']} AS daily_sales
                {SALES_BASE_SQL_1}
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
            "leader_share_percentage": (
                leader['share_percentage']
                if leader else 0
            ),
            "top_sales": round(total_sales, 2),

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

def visit_plan_build_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("vp.created_at BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = vp.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = vp.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("vp.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params
