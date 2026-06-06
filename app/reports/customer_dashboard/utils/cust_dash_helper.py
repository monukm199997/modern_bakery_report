from app.reports.customer_dashboard.schemas.schemas import CustomerDashRequest
from app.utils.helper import quantity_expr_sql, validate_mandatory, choose_granularity
from sqlalchemy import text
from datetime import datetime, timedelta, date
from app.reports.sales_dashboard.utils.sales_dash_helper import return_prepare_dashboard_context
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL as Base_JOIN
from app.reports.customer_dashboard.utils.query_helper import (
    TOTAL_CUSTOMER_IN_CATEGORY,
    TOTAL_CUSTOMER_IN_CHANNEL,
    TOTAL_CUSTOMER_IN_REGION,
    TOTAL_CUSTOMER_IN_ROUTE,
    BASE_SQL,
)

def previous_period_range(from_date: str, to_date: str):

    start = datetime.strptime(from_date, "%Y-%m-%d").date()
    end = datetime.strptime(to_date, "%Y-%m-%d").date()

    days = (end - start).days + 1

    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    return (
        prev_start.strftime("%Y-%m-%d"),
        prev_end.strftime("%Y-%m-%d")
    )

def build_query_parts(payload: CustomerDashRequest):
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

def prepare_dashboard_context(payload: CustomerDashRequest):
    validate_mandatory(payload)

    joins, where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else "ROUND(SUM(id.item_total)::numeric, 2)"
    )

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "value_expr": value_expr,
    }

def get_active_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        SELECT COUNT(DISTINCT customer_id)
        FROM invoice_headers ih
        LEFT JOIN salesman s ON s.id = ih.salesman_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
    """
    return db.execute(text(sql), ctx['params']).scalar() or 0

def get_new_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql = f"""
        SELECT COUNT(*)
        FROM agent_customers
        WHERE created_at::date
        BETWEEN :from_date AND :to_date
    """
    return db.execute(text(sql), ctx['params']).scalar() or 0

def get_at_risk_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                customer_id,
                MAX(invoice_date) AS last_sale
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            {ctx['join_sql']}
            GROUP BY customer_id
        ) t
        WHERE CURRENT_DATE - last_sale > 30
    """
    return db.execute(text(sql), ctx['params']).scalar() or 0

def get_inactive_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql = f"""
        SELECT COUNT(*)
        FROM (
            SELECT
                customer_id,
                MAX(invoice_date) AS last_sale
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            {ctx['join_sql']}
            GROUP BY customer_id
        ) t
        WHERE CURRENT_DATE - last_sale > 90
    """
    return db.execute(text(sql), ctx['params']).scalar() or 0

def get_avg_sales_value(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql = f"""
        SELECT
            COALESCE(
                {ctx['value_expr']} /
                NULLIF(COUNT(DISTINCT customer_id), 0),
                0
            )
        FROM invoice_headers ih
        LEFT JOIN invoice_details id ON id.header_id = ih.id
        LEFT JOIN salesman s ON s.id = ih.salesman_id
        LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
    """
    return db.execute(text(sql), ctx['params']).scalar() or 0

def get_customer_growth(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        SELECT
            TO_CHAR(created_at,'YYYY-MM') AS month,
            COUNT(*) AS value
        FROM agent_customers
        WHERE created_at::date
        BETWEEN :from_date AND :to_date
        GROUP BY month
        ORDER BY month
    """
    rows = db.execute(text(sql),ctx['params']).mappings().all()
    return [
        {
            "month": r["month"],
            "value": int(r["value"])
        }
        for r in rows
    ]

def get_customer_coverage(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql = text(f"""
        WITH total_customers AS (
            SELECT COUNT(*) AS total
            FROM agent_customers
        )
        SELECT
            TO_CHAR(ih.invoice_date,'YYYY-MM') AS month,
            ROUND(
                COUNT(DISTINCT customer_id) * 100.0 /
                (SELECT total FROM total_customers),
                2
            ) AS value
        FROM invoice_headers ih
        LEFT JOIN salesman s ON s.id = ih.salesman_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY month
        ORDER BY month
    """)
    rows = db.execute(sql, ctx['params']).mappings().all()
    return [
        {
            "month": r["month"],
            "value": float(r["value"])
        }
        for r in rows
    ]

def get_sales_returns(payload, db):
    ctx = prepare_dashboard_context(payload)
    re_ctx  = return_prepare_dashboard_context(payload)
    sql = f"""
        SELECT
            TO_CHAR(ih.invoice_date,'YYYY-MM') AS month,
            {ctx['value_expr']} AS sales
        {Base_JOIN}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY month
    """

    return_sql =f"""
        SELECT
            TO_CHAR(rh.created_at,'YYYY-MM') AS month,
            {re_ctx['value_expr']} AS returns
        FROM return_header rh
        LEFT JOIN return_details rd ON rd.header_id = rh.id
        LEFT JOIN salesman s ON s.id = rh.salesman_id
        LEFT JOIN item_uoms iu
                ON iu.item_id = rd.item_id
                AND iu.uom_id = rd.uom_id
        {re_ctx['join_sql']}
        WHERE {re_ctx['where_sql']}
        GROUP BY month
    """
    sales = db.execute(text(sql),ctx['params']).mappings().all()
    returns = db.execute(text(return_sql),re_ctx['params']).mappings().all()
    data = {}
    for row in sales:
        data[row["month"]] = {
            "sales": float(row["sales"] or 0),
            "returns": 0
        }
    for row in returns:
        data.setdefault(
            row["month"],
            {"sales": 0, "returns": 0}
        )
        data[row["month"]]["returns"] = float(
            row["returns"] or 0
        )
    return [
        {
            "month": month,
            "sales": values["sales"],
            "returns": values["returns"]
        }
        for month, values in sorted(data.items())
    ]

def customer_health(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        WITH customer_last_order AS (
            SELECT
                ih.customer_id,
                MAX(ih.invoice_date) AS last_order_date
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        )

        SELECT
            COUNT(*) FILTER (
                WHERE CURRENT_DATE - last_order_date <= 30
            ) AS healthy,

            COUNT(*) FILTER (
                WHERE CURRENT_DATE - last_order_date
                BETWEEN 31 AND 60
            ) AS warning,

            COUNT(*) FILTER (
                WHERE CURRENT_DATE - last_order_date > 60
            ) AS critical

        FROM customer_last_order
    """
    row = db.execute(text(sql), ctx["params"]).mappings().first()
    return {
        "healthy": int(row["healthy"] or 0),
        "warning": int(row["warning"] or 0),
        "critical": int(row["critical"] or 0)
    }

def customer_health_histogram(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        WITH customer_last_order AS (
            SELECT
                ih.customer_id,
                MAX(ih.invoice_date) AS last_order_date
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        )

        SELECT
            CASE
                WHEN CURRENT_DATE - last_order_date <= 30
                    THEN '0-30d'
                WHEN CURRENT_DATE - last_order_date <= 60
                    THEN '31-60d'
                WHEN CURRENT_DATE - last_order_date <= 90
                    THEN '61-90d'
                ELSE '90+d'
            END AS bucket,

            COUNT(*) AS value

        FROM customer_last_order
        GROUP BY bucket
        ORDER BY bucket
    """
    rows = db.execute(text(sql), ctx["params"]).mappings().all()
    return [
        {
            "label": row["bucket"],
            "value": int(row["value"])
        }
        for row in rows
    ]

def get_inactive_customer(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        WITH customer_last_order AS (
            SELECT
                ih.customer_id,
                MAX(ih.invoice_date) AS last_order_date
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        )
        SELECT COUNT(*)
        FROM customer_last_order
        WHERE last_order_date <
              CURRENT_DATE - INTERVAL '7 days'
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def get_risk_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql =f"""
        WITH customer_last_order AS (
            SELECT
                ih.customer_id,
                MAX(ih.invoice_date) AS last_order_date
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        )
        SELECT COUNT(*)
        FROM agent_customers ac
        LEFT JOIN customer_last_order clo
            ON clo.customer_id = ac.id
        WHERE
            COALESCE(ac.credit_limit,0) > 0
            AND (
                clo.last_order_date IS NULL
                OR clo.last_order_date <
                   CURRENT_DATE - INTERVAL '30 days'
            )
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def get_top_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    sql = f"""
        SELECT
            ac.osa_code AS customer_code,
            ac.name AS customer_name,
            {ctx['value_expr']} AS value
        {Base_JOIN}
        JOIN agent_customers ac ON ac.id = ih.customer_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            ac.osa_code,
            ac.name
        ORDER BY value DESC
        LIMIT 10
    """
    rows = db.execute(text(sql),ctx["params"]).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_region_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            {TOTAL_CUSTOMER_IN_REGION}
            {ctx['value_expr']} AS value
            {Base_JOIN}
            {ctx['join_sql']}
            LEFT JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY r.region_name
            ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_route_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            {TOTAL_CUSTOMER_IN_ROUTE}
            {ctx['value_expr']} AS value
        {Base_JOIN}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY rt.route_name
        ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_channel_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            {TOTAL_CUSTOMER_IN_CHANNEL}
            {ctx['value_expr']} AS value
            {Base_JOIN}
            JOIN agent_customers ac ON ac.id = ih.customer_id
            JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY oc.outlet_channel
            ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_categories_customers(payload, db):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            {TOTAL_CUSTOMER_IN_CATEGORY}
            {ctx['value_expr']} AS value
            {Base_JOIN}
            JOIN agent_customers ac ON ac.id = ih.customer_id
            JOIN customer_categories cc ON cc.id = ac.category_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY cc.customer_category_name
            ORDER BY total_customers DESC
        """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_top_100_customers(payload, db, page, page_size):
    ctx = prepare_dashboard_context(payload)
    prev_from, prev_to = previous_period_range(
        payload.from_date,
        payload.to_date
    )
    offset = (page - 1) * page_size
    query = f"""
        WITH current_sales AS (
            SELECT
                ih.customer_id,
                {ctx['value_expr']}AS revenue,
                COUNT(DISTINCT ih.id) AS orders,
                MAX(ih.invoice_date) AS last_order
            {Base_JOIN}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        ),
        previous_sales AS (
            SELECT
                ih.customer_id,
                {ctx['value_expr']} AS revenue
            {BASE_SQL}
            WHERE ih.invoice_date
                BETWEEN :prev_from_date
                AND :prev_to_date
            GROUP BY ih.customer_id
        ),
        lifetime_orders AS (
            SELECT
                customer_id,
                COUNT(*) AS total_orders
            FROM invoice_headers
            GROUP BY customer_id
        )
        SELECT
            ac.id,
            ac.osa_code,
            ac.name,
            COALESCE(cs.revenue,0) AS revenue,
            COALESCE(ps.revenue,0) AS previous_revenue,
            COALESCE(cs.orders,0) AS orders,
            cs.last_order,
            COALESCE(ac.credit_limit,0) AS outstanding,
            COALESCE(lo.total_orders,0) AS lifetime_orders
        FROM current_sales cs
        JOIN agent_customers ac ON ac.id = cs.customer_id
        LEFT JOIN previous_sales ps ON ps.customer_id = cs.customer_id
        LEFT JOIN lifetime_orders lo ON lo.customer_id = cs.customer_id
        ORDER BY revenue DESC
        LIMIT :limit
        OFFSET :offset
        """
    count_query = f"""
        SELECT COUNT(*)
        FROM (
            SELECT ih.customer_id
            {Base_JOIN}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        ) x
    """
    params = {
        **ctx["params"],
        "prev_from_date": prev_from,
        "prev_to_date": prev_to,
        "limit": page_size,
        "offset": offset
    }
    total_records = db.execute(text(count_query), ctx["params"]).scalar()
    rows = db.execute(text(query),params).mappings().all()
    customers = []
    for row in rows:
        revenue = float(row["revenue"] or 0)
        previous_revenue = float(row["previous_revenue"] or 0)
        orders = int(row["orders"] or 0)
        lifetime_orders = int(row["lifetime_orders"] or 0)
        avg_billing = (revenue / orders if orders > 0 else 0)
        growth_pct = None
        if previous_revenue > 0:
            growth_pct = round(((revenue - previous_revenue) / previous_revenue) * 100, 1)

        last_order_days = None
        if row["last_order"]:
            last_order_days = (date.today() - row["last_order"]).days

        collection_efficiency = None
        if lifetime_orders > 0:
            collection_efficiency = round((orders / lifetime_orders) * 100, 0)

        health_score = 0
        if last_order_days is not None:
            health_score = max(0,int(100 - (last_order_days * 100 / 120)))

        customers.append({
            "customer_code": row["osa_code"],
            "customer_name": row["name"],
            "revenue": revenue,
            "growth_pct": growth_pct,
            "avg_billing": round(avg_billing, 2),
            "last_order_days": last_order_days,
            "outstanding": float(
                row["outstanding"] or 0
            ),
            "collection_efficiency":
                collection_efficiency,
            "health_score": health_score
        })

    return {
        "total_records": total_records,
        "page": page,
        "page_size": page_size,
        "customers": customers
    }

def get_outstanding_recovery(payload, db, page, page_size):
    ctx = prepare_dashboard_context(payload)
    offset = (page - 1) * page_size
    count_sql = f"""
        SELECT COUNT(*)
        FROM agent_customers ac
        WHERE COALESCE(ac.credit_limit,0) > 0
    """
    sql = f"""
        WITH customer_last_order AS (
            SELECT
                ih.customer_id,
                MAX(ih.invoice_date) AS last_order
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            LEFT JOIN tbl_route rt ON rt.id = ih.route_id
            WHERE {ctx['where_sql']}
            GROUP BY ih.customer_id
        ),
        customer_salesman AS (
            SELECT DISTINCT ON (ih.customer_id)
                ih.customer_id,
                s.name AS salesman_name,
                rt.route_name
            FROM invoice_headers ih
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            LEFT JOIN tbl_route rt ON rt.id = s.route_id
            WHERE {ctx['where_sql']}
            ORDER BY
                ih.customer_id,
                ih.invoice_date DESC
        )
        SELECT
            ac.id,
            ac.osa_code,
            ac.name,
            COALESCE(cs.route_name,'-') AS route,
            COALESCE(cs.salesman_name,'-') AS salesman,
            clo.last_order,
            COALESCE(ac.credit_limit,0) AS outstanding
        FROM agent_customers ac
        LEFT JOIN customer_last_order clo ON clo.customer_id = ac.id
        LEFT JOIN customer_salesman cs ON cs.customer_id = ac.id
        WHERE COALESCE(ac.credit_limit,0) > 0
        ORDER BY outstanding DESC
        LIMIT :limit
        OFFSET :offset
        """
    params = {
        **ctx["params"],
        "limit": page_size,
        "offset": offset
    }
   
    total_records = db.execute(text(count_sql)).scalar()
    rows = db.execute(text(sql),params).mappings().all()
    result = []
    for row in rows:
        last_order = row["last_order"]
        if last_order:
            days_since_order = (
                date.today() - last_order
            ).days

            health = max(0,int(100 - (days_since_order * 100 / 120)))
        else:
            health = 0
        result.append({
            "customer_code": row["osa_code"],
            "customer_name": row["name"],
            "route": row["route"],
            "salesman": row["salesman"],
            "last_order": (
                str(last_order)
                if last_order
                else None
            ),
            "outstanding": float(
                row["outstanding"] or 0
            ),
            "health": health
        })

    return {
        "total_records": total_records,
        "page": page,
        "page_size": page_size,
        "rows": result
    }

def get_trend_line(payload, db):
    ctx = prepare_dashboard_context(payload)
    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )
    query = f"""
        SELECT
            {period_label_sql} AS period_label,
            {ctx['value_expr']} AS value
        {Base_JOIN}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY {period_label_sql},{order_by_sql}
        ORDER BY {order_by_sql}
        """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return {"granularity": granularity, "sales_trend_line": result}
