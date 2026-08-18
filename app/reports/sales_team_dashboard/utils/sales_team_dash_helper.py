from sqlalchemy import text
from datetime import timedelta
from app.reports.sales_team_dashboard.utils.sale_team_sql_query import (
    REVENUE_NET_SALES,
    VOLUME_NET_SALES,
    JOIN_BASE_SQL,
    VISIT_OVERVIEW_SELECT,
    SALES_GROWTH_QUERY,
    CUSTOMER_RETENTION_QUERY,
    ORDERS_VS_INVOICES_QUERY
)


def sales_build_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("ih.invoice_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        # joins.append("LEFT JOIN tbl_route rt ON rt.id = ih.route_id")
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

def prepare_dashboard_context(payload):

    joins, where_fragments, params = sales_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    volume = VOLUME_NET_SALES
    revenue = REVENUE_NET_SALES

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "volume": volume,
        "revenue": revenue,
    }

def visit_build_query_parts(payload):

    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("vp.visit_start_time IS NOT NULL")

    where_fragments.append("vp.visit_start_time::date BETWEEN :from_date AND :to_date")

    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("LEFT JOIN salesman s ON s.id = vp.salesman_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")

        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = vp.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("vp.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.salesman_ids:
        where_fragments.append("vp.salesman_id = ANY(:salesman_ids)")

        params["salesman_ids"] = payload.salesman_ids

    joins = list(dict.fromkeys(joins))

    return joins, where_fragments, params

def prepare_dashboard_visit_context(payload):

    joins, where_fragments, params = visit_build_query_parts(payload)

    join_sql = "\n".join(joins)
    where_sql = " AND ".join(where_fragments)

    return {"join_sql": join_sql, "where_sql": where_sql, "params": params}

def sales_curr_prev_query(
    payload,
    from_param="from_date",
    to_param="to_date",
    from_date=None,
    to_date=None,
    include_date_filter=True,
):
    joins = []
    where_fragments = []
    params = {}

    from_date = (from_date if from_date is not None else payload.from_date)
    to_date = (to_date if to_date is not None else payload.to_date)

    if include_date_filter:
        where_fragments.append(
            f"ih.invoice_date BETWEEN :{from_param} AND :{to_param}"
        )

        params[from_param] = from_date
        params[to_param] = to_date

    if payload.company_ids:
        # joins.append("LEFT JOIN salesman s ON s.id = ih.salesman_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.salesman_ids:
        where_fragments.append("ih.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids

    joins = list(dict.fromkeys(joins))

    return (
        joins,
        where_fragments,
        params,
    )

def prepare_curr_perv_context(
    payload,
    from_date=None,
    to_date=None,
    include_date_filter=True,   
):
    joins, where_fragments, params = (
        sales_curr_prev_query(
            payload,
            from_date=from_date,
            to_date=to_date,
            include_date_filter=include_date_filter,
        )
    )

    where_sql = ""

    if where_fragments:
        where_sql = " AND " + " AND ".join(
            where_fragments
        )

    join_sql = "\n".join(
        joins
    )

    volume = VOLUME_NET_SALES
    revenue = REVENUE_NET_SALES

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "volume": volume,
        "revenue": revenue,
    }

def visit_curr_prev_query(
    payload,
):
    joins = []
    where_fragments = []
    params = {}

    if payload.company_ids:
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = (payload.company_ids)

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = vp.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = (payload.region_ids)

    if payload.route_ids:
        where_fragments.append("vp.route_id = ANY(:route_ids)")
        params["route_ids"] = (payload.route_ids)

    if payload.salesman_ids:
        where_fragments.append("vp.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = (payload.salesman_ids)

    joins = list(dict.fromkeys(joins))

    return (
        joins,
        where_fragments,
        params,
    )

def prepare_visit_retention_context(payload):

    joins, where_fragments, params = (visit_curr_prev_query(payload))
    where_sql = ""
    if where_fragments:
        where_sql = (
            " AND "
            + " AND ".join(
                where_fragments
            )
        )

    join_sql = "\n".join(
        joins
    )

    return {
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
    }

def order_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}

    if payload.company_ids:
        where_fragments.append("os.company_id = ANY(:company_ids)")
        params["company_ids"] = (payload.company_ids)

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route ort ON ort.id = aoh.route_id")
        where_fragments.append("ort.region_id = ANY(:region_ids)")
        params["region_ids"] = (payload.region_ids)

    if payload.route_ids:
        where_fragments.append("aoh.route_id = ANY(:route_ids)")
        params["route_ids"] = (payload.route_ids)

    if payload.salesman_ids:
        where_fragments.append("aoh.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = (payload.salesman_ids)

    return (
        list(dict.fromkeys(joins)),
        where_fragments,
        params,
    )

def invoice_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}
    if payload.company_ids:
        where_fragments.append("ins.company_id = ANY(:company_ids)")
        params["company_ids"] = (payload.company_ids)

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route irt ON irt.id = ih.route_id")
        where_fragments.append("irt.region_id = ANY(:region_ids)")
        params["region_ids"] = (payload.region_ids)

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = (payload.route_ids)

    if payload.salesman_ids:
        where_fragments.append("ih.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = (payload.salesman_ids)

    return (
        list(dict.fromkeys(joins)),
        where_fragments,
        params,
    )


def get_total_salesman(db):
    query = """
        SELECT COUNT(*)
        FROM salesman
        WHERE deleted_at IS NULL
    """
    return db.execute(text(query)).scalar() or 0

def get_active_salesman(db):
    query = """
        SELECT COUNT(*)
        FROM salesman
        WHERE deleted_at IS NULL
        AND status = 1
    """
    return db.execute(text(query)).scalar() or 0

def get_visit_customer(payload, db):
    ctx = prepare_dashboard_visit_context(payload)
    query = f"""
            SELECT COUNT(DISTINCT customer_id) AS customers_visited
        FROM visit_plan vp
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
    """
    return db.execute(text(query), ctx["params"]).scalar() or 0

def get_sales_period(payload, db):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
        {ctx['revenue']} as sales
        {JOIN_BASE_SQL}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
    """
    print(query)
    return db.execute(text(query), ctx["params"]).scalar() or 0

def get_visit_overview(payload, db):
    ctx = prepare_dashboard_visit_context(payload)

    query = f"""
        SELECT 
          {VISIT_OVERVIEW_SELECT}
        FROM visit_plan vp
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            vp.salesman_id,
            s.name
        ORDER BY
        total_visits DESC,
        salesman_name ASC
    """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_Visit_heatmap(payload,db):
    ctx = prepare_dashboard_visit_context(payload)
    query = f"""
        SELECT
            vp.salesman_id,
            COALESCE(s.name, 'Unknown') AS salesman_name,
            EXTRACT(
            ISODOW FROM vp.visit_start_time
            )::integer AS weekday,
            COUNT(vp.id) AS visit_count
        FROM visit_plan vp
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            vp.salesman_id,
            s.name,
            EXTRACT(ISODOW FROM vp.visit_start_time)
        ORDER BY
            vp.salesman_id,
            weekday
    """
    rows = db.execute(text(query), ctx['params']).mappings().all()

    weekday_names = {
        1: "mon",
        2: "tue",
        3: "wed",
        4: "thu",
        5: "fri",
        6: "sat",
        7: "sun",
    }
    salesman_map = {}
    for row in rows:
        salesman_id = row["salesman_id"]

        if salesman_id not in salesman_map:
            salesman_map[salesman_id] = {
                "salesman_id": salesman_id,
                "salesman_name": row["salesman_name"],
                "mon": 0,
                "tue": 0,
                "wed": 0,
                "thu": 0,
                "fri": 0,
                "sat": 0,
                "sun": 0,
                "total": 0,
            }
        weekday = int(row["weekday"] or 0)
        count = int(row["visit_count"] or 0)
        if weekday in weekday_names:
            day_name = weekday_names[weekday]
            salesman_map[salesman_id][day_name] = count
            salesman_map[salesman_id]["total"] += count

    result = sorted(
    salesman_map.values(),
    key=lambda x: x["total"],
    reverse=True,
    )   

    return result

def get_top_sales_by_salesman(payload, db, limit=10):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            ih.salesman_id,
            COALESCE(s.name, 'Unknown') AS salesman_name,
            COALESCE(s.osa_code,'') AS salesman_code,
            {ctx['revenue']} as sales
        {JOIN_BASE_SQL}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            ih.salesman_id,
            s.name,
            s.osa_code
        HAVING {ctx['revenue']}>0
        ORDER BY
        sales DESC,
        salesman_name ASC
        LIMIT :top_sales_limit
    """
    ctx["params"]["top_sales_limit"] = limit
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_top_customer_visit_salesman(payload, db, limit = 10):
    ctx = prepare_dashboard_visit_context(payload)
    query = f"""
        SELECT
            vp.salesman_id,
            COALESCE(s.name, 'Unknown') AS salesman_name,
            COALESCE(s.osa_code, '') AS salesman_code,
            COUNT(DISTINCT vp.customer_id) AS customers_visit
        FROM visit_plan vp
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            vp.salesman_id,
            s.name,
            s.osa_code
        ORDER BY
            customers_visit DESC,
            salesman_name ASC
    """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_region_performance(payload, db):
    ctx = prepare_dashboard_visit_context(payload)
    query = f"""
        SELECT
            r.id AS region_id,
            COALESCE(r.region_code, '') AS region_code,
            COALESCE(r.region_name, 'Unknown') AS region_name,
            COUNT(vp.id) AS total_visits
        FROM visit_plan vp
        LEFT JOIN tbl_route rt ON rt.id = vp.route_id
        LEFT JOIN tbl_region r ON r.id = rt.region_id
        LEFT JOIN salesman s ON s.id = vp.salesman_id
        WHERE {ctx['where_sql']}
        GROUP BY
            r.id,
            r.region_code,
            r.region_name
        ORDER BY
            total_visits DESC,
            region_name ASC
    """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_route_performance(payload, db):
    ctx = prepare_dashboard_visit_context(payload)
    query = f"""
        SELECT
            rt.id AS route_id,
            COALESCE(rt.route_code, '') AS route_code,
            COALESCE(rt.route_name, 'Unknown') AS route_name,
            COUNT(vp.id) AS total_visits
        FROM visit_plan vp
        LEFT JOIN tbl_route rt ON rt.id = vp.route_id
        LEFT JOIN salesman s ON s.id = vp.salesman_id
        WHERE {ctx['where_sql']}
        GROUP BY
            rt.id,
            rt.route_code,
            rt.route_name
        ORDER BY
            total_visits DESC,
            route_name ASC
    """
    rows = db.execute(text(query), ctx['params']).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

def get_sales_growth(payload, db):

    current_from = payload.from_date
    current_to = payload.to_date

    period_days = (current_to - current_from).days + 1

    previous_to = (current_from - timedelta(days=1))
    previous_from = (previous_to - timedelta(days=period_days - 1))

    current_ctx = prepare_curr_perv_context(payload, from_date=current_from, to_date=current_to, include_date_filter=False,)
    previous_ctx = prepare_curr_perv_context(payload, from_date=previous_from, to_date=previous_to, include_date_filter=False,)

    current_where_sql = (
        current_ctx["where_sql"]
        .replace(
            ":from_date",
            ":current_from_date",
        )
        .replace(
            ":to_date",
            ":current_to_date",
        )
    )

    previous_where_sql = (
        previous_ctx["where_sql"]
        .replace(
            ":from_date",
            ":previous_from_date",
        )
        .replace(
            ":to_date",
            ":previous_to_date",
        )
    )

    query = SALES_GROWTH_QUERY.format(
        current_join_sql=current_ctx["join_sql"],
        current_where_sql=current_where_sql,
        previous_join_sql=previous_ctx["join_sql"],
        previous_where_sql=previous_where_sql,
    )

    params = {}

    params.update(current_ctx["params"])

    previous_params = (previous_ctx["params"])


    params["current_from_date"] = (current_from)
    params["current_to_date"] = (current_to)

    params["previous_from_date"] = (previous_from)
    params["previous_to_date"] = (previous_to)


    params.pop("from_date", None,)

    params.pop("to_date",None,)

    for key, value in previous_params.items():

        if key not in (
            "from_date",
            "to_date",
        ):
            params[key] = value

    rows = (
        db.execute(text(query), params,).mappings().all())

    result = []

    for row in rows:
        current_sales = (row["current_sales"] or 0)
        previous_sales = (row["previous_sales"] or 0)

        current_sales = float(current_sales)
        previous_sales = float(previous_sales)

        if previous_sales == 0:
            growth = None

        else:
            growth = round(((current_sales - previous_sales)/ previous_sales) * 100, 1,)

        result.append(
            {
                "salesman_id": row["salesman_id"],
                "salesman_name": row["salesman_name"],
                "salesman_code": row["salesman_code"],
                "current_sales": current_sales,
                "previous_sales": previous_sales,
                "growth": growth,
            }
        )

    return {
        "current_period": {
            "from_date": current_from,
            "to_date": current_to,
        },

        "previous_period": {
            "from_date": previous_from,
            "to_date": previous_to,
        },

        "data": result,
    }

def get_customer_retention(payload, db):
    current_from = payload.from_date
    current_to = payload.to_date
    period_days = (current_to - current_from).days + 1
    previous_to = (current_from - timedelta(days=1))
    previous_from = (previous_to - timedelta(days=period_days - 1))

    context = prepare_visit_retention_context(payload)

    current_join_sql = context["join_sql"]
    previous_join_sql = context["join_sql"]
    current_where_sql = context["where_sql"]
    previous_where_sql = context[ "where_sql"]

    query = CUSTOMER_RETENTION_QUERY.format(
        current_join_sql=current_join_sql,
        previous_join_sql=previous_join_sql,
        current_where_sql=current_where_sql,
        previous_where_sql=previous_where_sql,
    )

    params = dict(context["params"])
    params["current_from_date"] = (current_from)
    params["current_to_date"] = (current_to)
    params["previous_from_date"] = (previous_from)
    params["previous_to_date"] = (previous_to)

    rows = (db.execute(text(query), params,).mappings().all())

    result = []

    for row in rows:

        previous_customers = int(row["previous_customers"]or 0)
        returning_customers = int(row["returning_customers"]or 0)

        if previous_customers > 0:
            retention = round((returning_customers / previous_customers) * 100, 1,)

        else:
            retention = 0.0
        result.append({
            "salesman_id": row["salesman_id"],
            "salesman_name": row["salesman_name"],
            "salesman_code": row["salesman_code"],
            "previous_customers": (previous_customers),
            "returning_customers": (returning_customers),
            "retention": retention,
        })

    return {
        "current_period": {
            "from_date": current_from,
            "to_date": current_to,
        },

        "previous_period": {
            "from_date": previous_from,
            "to_date": previous_to,
        },

        "data": result,
    }

def get_orders_vs_invoices(payload, db):

    (order_joins, order_where, order_params,) = order_query_parts(payload)
    (invoice_joins, invoice_where, invoice_params,) = invoice_query_parts(payload)

    order_join_sql = "\n".join(order_joins)
    invoice_join_sql = "\n".join(invoice_joins)

    order_where_sql = ""

    if order_where:
        order_where_sql = ( "AND " + "\nAND ".join(order_where))

    invoice_where_sql = ""

    if invoice_where:
        invoice_where_sql = ("AND " + "\nAND ".join(invoice_where))

    query = ORDERS_VS_INVOICES_QUERY.format(
        order_join_sql=order_join_sql,
        order_where_sql=order_where_sql,
        invoice_join_sql=invoice_join_sql,
        invoice_where_sql=invoice_where_sql,
    )

    params = {
        "from_date": payload.from_date,
        "to_date": payload.to_date,
    }

    params.update(order_params)
    params.update(invoice_params)

    rows = (db.execute(text(query), params,).mappings().all())
    result = []
    for row in rows:

        orders = int(row["orders"] or 0)
        invoices = int(row["invoices"] or 0)

        if orders > 0:
            invoice_order_percentage = round(
                (invoices / orders) * 100, 1,)
        else:
            invoice_order_percentage = None

        result.append({
            "salesman_id": row["salesman_id"],
            "salesman_name": row["salesman_name"],
            "salesman_code": row["salesman_code"],
            "orders": orders,
            "invoices": invoices,
            "invoice_order_percentage": (invoice_order_percentage),
        })

    return {
        "data": result
    }


