from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_dashboard.schemas.schemas import (
    SalesDashboardKpisRequest,
    SalesDashboardRequest,
    SalesDashboardPerfomanceRequest,
)
from app.reports.sales_dashboard.utils.sales_dash_helper import (
    prepare_dashboard_context,
    return_prepare_dashboard_context,
    order_prepare_dashboard_context,
    delivery_prepare_dashboard_context,
    load_prepare_dashboard_context,
    unload_prepare_dashboard_context,
    return_quantity_expr_sql,
    quantity_expr_sql,
    order_quantity_expr_sql,
    get_sales_performance_data,
)
from app.reports.customer_sales_report.utils.sql_query_helper import (
    BASE_SQL,
    OPTIONAL_JOINS_SQL_1,
)
from app.reports.sales_dashboard.utils.sql_query_helper import (
    RETURN_BASE_SQL,
    ORDER_BASE_SQL,
    DELIVERY_BASE_SQL,
    SALES_BASE_SQL,
    ROUTE_COUNT,
    SALESMAN_COUNT,
    FROM_CLAUSE_1,
    SELECT_1,
    SALES_OVERVIEW_JOIN_SQL,
    RETURN_OVERVIEW_JOIN_SQL,
    VAN_ROUTE_SELECT_SQL,
    VAN_ROUTE_GROUP_BY,
    LOADED_DATA_JOIN_SQL,
    UNLOADED_DATA_JOIN_SQL,
    ORDER_JOIN_SQL,
)

router = APIRouter(tags=["Sales Dashboard"], dependencies= [Depends(get_current_user)])

@router.post("/kpis")
def sales_dashboard_kpis(
    payload: SalesDashboardKpisRequest, db: Session = Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    re_ctx = return_prepare_dashboard_context(payload)
    or_ctx = order_prepare_dashboard_context(payload)
    del_ctx = delivery_prepare_dashboard_context(payload)
    TOTAL_SALES_SQL = f"""
        (
            SELECT
                {ctx['value_expr']}
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
        ) AS total_sales
        """
    TOTAL_SALES_FREE_GOOD_SQL = f"""
        (
            SELECT
                {ctx['value_expr']}
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
                AND id.item_total = 0
        ) AS total_sales_free_good
        """
    TOTAL_RETURNED_SALES_SQL = f"""
        (
            SELECT
                {re_ctx['value_expr']}
            {RETURN_BASE_SQL}
            {re_ctx['join_sql']}
            WHERE {re_ctx['where_sql']}
        ) AS total_returned_sales
        """
    TOTAL_ORDERED = f"""
        (
        SELECT
            {or_ctx['value_expr']}
            {ORDER_BASE_SQL}
            {or_ctx['join_sql']}
            WHERE {or_ctx['where_sql']}
        ) AS total_ordered
    """
    TOTAL_DELIVERY_SQL = f"""
        (
        SELECT
            {del_ctx['value_expr']}
            {DELIVERY_BASE_SQL}
            {del_ctx['join_sql']}
            WHERE {del_ctx['where_sql']}
        ) AS total_delivery
    """
    query = f"""
        SELECT
        {TOTAL_SALES_SQL},
        {TOTAL_SALES_FREE_GOOD_SQL},
        {TOTAL_RETURNED_SALES_SQL},
        {TOTAL_ORDERED},
        {TOTAL_DELIVERY_SQL}
    """
    rows = db.execute(text(query), ctx["params"]).fetchone()
    result = {
        "total_sales": rows.total_sales,
        "total_sales_free_good": rows.total_sales_free_good,
        "total_returned_sales": rows.total_returned_sales,
        "total_ordered": rows.total_ordered,
        "total_delivery": rows.total_delivery,
    }
    return result

@router.post("/revenue-split")
def revenue_split_by_customer_channel(
    payload: SalesDashboardKpisRequest, db: Session = Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            oc.outlet_channel AS channel,
            {ctx['value_expr']} AS total_revenue
        {BASE_SQL}
        {OPTIONAL_JOINS_SQL_1}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY oc.outlet_channel
        ORDER BY total_revenue DESC
    """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    channels = [dict(r._mapping) for r in rows]
    net_sales = sum(float(x["total_revenue"] or 0) for x in channels)
    for item in channels:
        item["channel"] = item["channel"] or "Others"
        item["total_revenue"] = round(float(item["total_revenue"] or 0), 2)
        item["percentage"] = (
            round((item["total_revenue"] / net_sales) * 100, 1) if net_sales > 0 else 0
        )
    result = {"net_sales_mtd": round(net_sales, 2), "channels": channels}
    return result

@router.post("/sales-overview")
def sales_overview(payload: SalesDashboardRequest, db: Session = Depends(get_db)):
    quantity = return_quantity_expr_sql()
    return_quantity = (
        quantity if payload.search_type.lower() == "quantity" else "SUM(rd.total)"
    )
    quantity = quantity_expr_sql()
    sales_quantity = (
        quantity if payload.search_type.lower() == "quantity" else "SUM(id.item_total)"
    )
    if payload.view_type == "year":
        period_sql = "EXTRACT(YEAR FROM date_col)"
        label_sql = "TO_CHAR(date_col, 'YYYY')"
        sales_filter = """
            EXTRACT(YEAR FROM ih.invoice_date) = :year
        """
        return_filter = """
            EXTRACT(YEAR FROM rh.created_at) = :year
        """
        params = {"year": int(payload.select_date)}

    else:
        year, month = payload.select_date.split("-")

        period_sql = "EXTRACT(MONTH FROM date_col)"
        label_sql = "TO_CHAR(date_col, 'Mon-YYYY')"

        sales_filter = """
            EXTRACT(YEAR FROM ih.invoice_date) = :year
            AND EXTRACT(MONTH FROM ih.invoice_date) = :month
        """
        return_filter = """
            EXTRACT(YEAR FROM rh.created_at) = :year
            AND EXTRACT(MONTH FROM rh.created_at) = :month
        """
        params = {"year": int(year), "month": int(month)}

    sales_period = period_sql.replace("date_col", "ih.invoice_date")
    sales_label = label_sql.replace("date_col", "ih.invoice_date")

    return_period = period_sql.replace("date_col", "rh.created_at")
    return_label = label_sql.replace("date_col", "rh.created_at")

    query = f"""
        WITH sales_data AS (
            SELECT
                {sales_period} AS period_no,
                {sales_label} AS period,
                {sales_quantity} AS sales
            {SALES_OVERVIEW_JOIN_SQL}
            WHERE {sales_filter}
            GROUP BY 1, 2
        ),
        return_data AS (
            SELECT
                {return_period} AS period_no,
                {return_label} AS period,
                {return_quantity} AS returns
            {RETURN_OVERVIEW_JOIN_SQL}
            WHERE {return_filter}
            GROUP BY 1, 2
        )
        SELECT
            s.period,
            s.sales,
            COALESCE(r.returns, 0) AS returns
        FROM sales_data s
        LEFT JOIN return_data r
            ON r.period_no = s.period_no
        ORDER BY s.period_no
    """
    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.post("/sales-performance")
def sales_performance(
    payload: SalesDashboardPerfomanceRequest, db: Session = Depends(get_db)
):
    return get_sales_performance_data(db, payload)

@router.post("/region-sales-kpis")
def region_sales_performance(
    payload: SalesDashboardKpisRequest, db: Session = Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            WITH region_sales AS (
                SELECT
                    r.region_name AS region,
                    {ctx['value_expr']} AS sales,
                    {ROUTE_COUNT},
                    {SALESMAN_COUNT}
                {SALES_BASE_SQL}
                {ctx['join_sql']}
                LEFT JOIN tbl_region r ON r.id = rt.region_id
                WHERE {ctx['where_sql']}
                GROUP BY r.region_name
            ),
            current_week AS (
                SELECT
                    r.region_name AS region,
                    {ctx['value_expr']} AS current_sales
                {FROM_CLAUSE_1}
                WHERE ih.invoice_date >= CURRENT_DATE - INTERVAL '7 day'
                GROUP BY r.region_name
            ),
            previous_week AS (
                SELECT
                    r.region_name AS region,
                    {ctx['value_expr']} AS previous_sales
                {FROM_CLAUSE_1}
                WHERE ih.invoice_date BETWEEN
                    CURRENT_DATE - INTERVAL '14 day'
                    AND
                    CURRENT_DATE - INTERVAL '8 day'
                GROUP BY r.region_name
            )
            SELECT
            {SELECT_1}
            FROM region_sales r
            LEFT JOIN current_week c ON c.region = r.region
            LEFT JOIN previous_week p ON p.region = r.region
            ORDER BY r.sales DESC
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

@router.post("/live-van-route")
def live_van_route(payload:SalesDashboardKpisRequest, db:Session = Depends(get_db)):
    sales_ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            {VAN_ROUTE_SELECT_SQL}
            {sales_ctx['value_expr']} AS value
        {SALES_BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        {sales_ctx['join_sql']}
        WHERE {sales_ctx['where_sql']}
        GROUP BY 
            {VAN_ROUTE_GROUP_BY}
        ORDER BY
            ih.salesman_id,
            ih.invoice_time
        """
    rows = db.execute(text(query), sales_ctx['params']).fetchall()
    grouped = {}

    for row in rows:
        salesman_id = row.salesman_id

        if salesman_id not in grouped:
            grouped[salesman_id] = {
                "id": row.van_id,
                "salesman": row.salesman,
                "stops": []
            }

        grouped[salesman_id]["stops"].append({
            "customer": row.customer_name,
            "time": row.invoice_time.strftime("%H:%M"),
            "value": float(row.value or 0),
            "lat": float(row.latitude or 0),
            "lng": float(row.longitude or 0)
        })

    fleet = []
    for van in grouped.values():
        stops = van["stops"]
        if not stops:
            continue
        stops[-1]["status"] = "active"

        for stop in stops[:-1]:
            stop["status"] = "done"

        fleet.append({
            "id": van["id"],
            "salesman": van["salesman"],
            "stops": stops,
            "total_sales":
                sum(s["value"] for s in stops)
        })

    return fleet

@router.post("/van-load-utilization")
def van_load_utilization(payload:SalesDashboardKpisRequest, db:Session = Depends(get_db)):
    load_ctx = load_prepare_dashboard_context(payload)
    unload_ctx = unload_prepare_dashboard_context(payload)
    sales_ctx = prepare_dashboard_context(payload)
    params = {
            **load_ctx["params"],
            **unload_ctx["params"],
            **sales_ctx["params"]
    }

    query = f"""
        WITH loaded_data AS (
            SELECT
                lh.salesman_id,
                {load_ctx['quantity']} AS loaded
            {LOADED_DATA_JOIN_SQL}
            {load_ctx['join_sql']}
            WHERE {load_ctx['where_sql']}
            GROUP BY
               lh.salesman_id
        ),
         sold_data AS (
            SELECT
                ih.salesman_id,
                {sales_ctx['value_expr']} AS sold
            {SALES_BASE_SQL}
            {sales_ctx['join_sql']}
            WHERE {sales_ctx['where_sql']}
            GROUP BY ih.salesman_id
        ),
        unload_data AS (
            SELECT
                ulh.salesman_id,
                {unload_ctx['quantity']} AS unloaded
            {UNLOADED_DATA_JOIN_SQL}
            {unload_ctx['join_sql']}
            WHERE {unload_ctx['where_sql']}
            GROUP BY
                ulh.salesman_id
        )
        SELECT
            s.osa_code AS van_code,
            s.name AS salesman,
            COALESCE(l.loaded, 0) AS loaded,
            COALESCE(sd.sold, 0) AS sold,
            COALESCE(u.unloaded, 0) AS unloaded
        FROM salesman s
        LEFT JOIN loaded_data l ON l.salesman_id = s.id
        LEFT JOIN sold_data sd ON sd.salesman_id = s.id
        LEFT JOIN unload_data u ON u.salesman_id = s.id
    """
    rows = db.execute(text(query), params).fetchall()
    result = []
    for row in rows:
        loaded = float(row.loaded or 0)
        sold = float(row.sold or 0)
        unloaded = float(row.unloaded or 0)
        result.append({
            "van_code": row.van_code,
            "salesman": row.salesman,
            "loaded": loaded,
            "sold": sold,
            "unload": unloaded,
            "in_van": max(loaded - sold - unloaded, 0),
            "load_percentage":
                round((sold / loaded) * 100, 2)
                if loaded else 0
        })
    return result

@router.post("/sales-team-performance")
def sales_team_performance(payload:SalesDashboardKpisRequest, db:Session = Depends(get_db)):
    load_ctx = load_prepare_dashboard_context(payload)
    unload_ctx = unload_prepare_dashboard_context(payload)
    sales_ctx = prepare_dashboard_context(payload)
    amount = "ROUND(SUM(id.item_total)::numeric, 2)"
    quantity = quantity_expr_sql()
    params = {
            **load_ctx["params"],
            **unload_ctx["params"],
            **sales_ctx["params"]
        }
    query = f"""
        WITH loaded_data AS (
            SELECT
                lh.salesman_id,
                {load_ctx['quantity']} AS loaded
            {LOADED_DATA_JOIN_SQL}
            {load_ctx['join_sql']}
            WHERE {load_ctx['where_sql']}
            GROUP BY
               lh.salesman_id
        ),
         sold_data AS (
            SELECT
                ih.salesman_id,
                {quantity} AS sales_qty,
                {amount} AS amount
            {SALES_BASE_SQL}
            {sales_ctx['join_sql']}
            WHERE {sales_ctx['where_sql']}
            GROUP BY ih.salesman_id
        ),
        unload_data AS (
            SELECT
                ulh.salesman_id,
                {unload_ctx['quantity']} AS unloaded
            {UNLOADED_DATA_JOIN_SQL}
            {unload_ctx['join_sql']}
            WHERE {unload_ctx['where_sql']}
            GROUP BY
                ulh.salesman_id
        )
        SELECT
            s.osa_code AS van_code,
            s.name AS salesman,
            rt.route_name,
            COALESCE(l.loaded, 0) AS loaded,
            COALESCE(sd.sales_qty, 0) AS sales_qty,
            COALESCE(sd.amount, 0) AS amount,
            COALESCE(u.unloaded, 0) AS unloaded
        FROM salesman s
        LEFT JOIN tbl_route rt ON rt.id = s.route_id
        LEFT JOIN loaded_data l ON l.salesman_id = s.id
        LEFT JOIN sold_data sd ON sd.salesman_id = s.id
        LEFT JOIN unload_data u ON u.salesman_id = s.id
    """

    rows = db.execute(text(query), params).fetchall()
    result = []
    for row in rows:
        loaded = float(row.loaded or 0)
        sales_qty = float(row.sales_qty or 0)
        amount = float(row.amount or 0)
        unloaded = float(row.unloaded or 0)
        result.append({
            "van_code": row.van_code,
            "salesman": row.salesman,
            "route_name": row.route_name,
            "loaded": loaded,
            "sales_qty": sales_qty,
            "amount": amount,
            "unload": unloaded,
        })
    return result


@router.post("/recent-order")
def recent_order(payload:SalesDashboardKpisRequest, db:Session = Depends(get_db)):
    order_ctx = order_prepare_dashboard_context(payload)
    quantity = order_quantity_expr_sql()
    amount = "ROUND(SUM(od.total)::numeric, 2)"

    query = f"""
            SELECT
            oh.order_code,
            ac.name AS customer,
            s.name AS salesman,
            {quantity} AS qty,
            TO_CHAR(oh.created_at, 'HH24:MI') AS time,
            {amount} AS amount,
            'CREATED' AS status
        {ORDER_JOIN_SQL}
        {order_ctx['join_sql']}
        WHERE {order_ctx['where_sql']}
        GROUP BY
            oh.order_code,
            ac.name,
            s.name,
            oh.created_at
        ORDER BY oh.created_at DESC
        LIMIT 6
    """
    rows = db.execute(text(query), order_ctx['params']).fetchall()
    response = []

    for row in rows:
        data = dict(row._mapping)
        response.append({
            "order_code": data["order_code"],
            "customer": data["customer"],
            "salesman": data["salesman"],
            "qty": int(data["qty"] or 0),
            "time": data["time"],
            "amount": float(data["amount"] or 0),
            "status": data["status"]
        })
    return response