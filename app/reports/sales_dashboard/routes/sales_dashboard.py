from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
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
    get_sales_performance_data,
    visit_plan_build_query_parts,
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
    TOTAL_AND_COMPLETE_STOPS,
    VISIT_BASE_JOIN,
    VISIT_SELECT_FIELS,
    VISITE_JOINS_SQL,
    VISIT_GROUP_BY,
    VAN_INFO,
    VAN_INFO_GROUP_BY,
    VISIT_FINAL_SELECT,
)

router = APIRouter(tags=["Sales Dashboard"])


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
            FROM invoice_headers ih
            JOIN invoice_details id
                ON id.header_id = ih.id
            WHERE {sales_filter}
            GROUP BY 1, 2
        ),
        return_data AS (
            SELECT
                {return_period} AS period_no,
                {return_label} AS period,
                {return_quantity} AS returns
            FROM return_header rh
            JOIN return_details rd
                ON rd.header_id = rh.id
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
    joins, where_fragments, params = visit_plan_build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)
    quantity = quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity" else "ROUND(SUM(id.item_total)::numeric, 2)"
    )
    query = f"""
        WITH summary AS (
            SELECT
            {TOTAL_AND_COMPLETE_STOPS}
            {VISIT_BASE_JOIN}
            {join_sql}
            WHERE {where_sql}
        ),
        timeline AS (
            SELECT
                {VISIT_SELECT_FIELS}
                {value_expr} AS sales
            {VISIT_BASE_JOIN}
            {VISITE_JOINS_SQL}
            {join_sql}
            WHERE {where_sql}
            GROUP BY
                {VISIT_GROUP_BY}
            ORDER BY vp.visit_start_time
        ),
        van_info AS (
            SELECT
               {VAN_INFO}
            {VISIT_BASE_JOIN}
            LEFT JOIN tbl_route rt ON rt.id = vp.route_id
            WHERE {where_sql}
            GROUP BY
                {VAN_INFO_GROUP_BY}
        )
        SELECT
           {VISIT_FINAL_SELECT}
    """
    row = db.execute(text(query),params).fetchone()
    return {
        "van_info": row.van_info,
        "summary": row.summary,
        "timeline": row.timeline
    }

@router.post("/van-load-utilization")
def van_load_utilization(payload:SalesDashboardKpisRequest, db:Session = Depends(get_db)):
    load_ctx = load_prepare_dashboard_context(payload)
    unload_ctx = unload_prepare_dashboard_context(payload)
    return_ctx = return_prepare_dashboard_context(payload)
    delivery_ctx = delivery_prepare_dashboard_context(payload)
    params = {
            **load_ctx["params"],
            **delivery_ctx["params"],
            **return_ctx["params"],
            **unload_ctx["params"],
    }

    query = f"""
        WITH loaded_data AS (
            SELECT
                ld.item_id,
                i.name AS item_name,
                {load_ctx['quantity']} AS loaded
            FROM tbl_load_header lh
            LEFT JOIN tbl_load_details ld ON ld.header_id = lh.id
            LEFT JOIN items i ON i.id = ld.item_id
            LEFT JOIN salesman s ON s.id = lh.salesman_id
            {load_ctx['join_sql']}
            WHERE {load_ctx['where_sql']}
            GROUP BY
                ld.item_id,
                i.name
        ),
        delivery_data AS (
            SELECT
                dd.item_id,
                {delivery_ctx['value_expr']} AS delivered
            FROM agent_delivery_headers dh
            LEFT JOIN agent_delivery_details dd ON dd.header_id = dh.id
            LEFT JOIN salesman s ON s.id = dh.salesman_id
            {delivery_ctx['join_sql']}
            WHERE {delivery_ctx['where_sql']}
            GROUP BY
                dd.item_id
        ),
        unload_data AS (
            SELECT
                uld.item_id,
                {unload_ctx['quantity']} AS unloaded
            FROM tbl_unload_header ulh
            LEFT JOIN tbl_unload_detail uld ON uld.header_id = ulh.id
            LEFT JOIN salesman s ON s.id = ulh.salesman_id
            {unload_ctx['join_sql']}
            WHERE {unload_ctx['where_sql']}
            GROUP BY
                uld.item_id
        ),
        return_data AS (
            SELECT
                rd.item_id,
                {return_ctx['value_expr']} AS returns
            FROM return_header rh
            LEFT JOIN return_details rd ON rd.header_id = rh.id
            LEFT JOIN salesman s ON s.id = rh.salesman_id
            {return_ctx['join_sql']}
            WHERE {return_ctx['where_sql']}
            GROUP BY
                rd.item_id
        )
        SELECT
            l.item_name AS sku,
            COALESCE(l.loaded, 0) AS loaded,
            COALESCE(d.delivered, 0) AS delivered,
            COALESCE(u.unloaded, 0) AS unloaded,
            COALESCE(r.returns, 0) AS returns,
            ROUND(
                (
                COALESCE(l.loaded, 0)
                -
                COALESCE(d.delivered, 0)
                -
                COALESCE(u.unloaded, 0)
                -
                COALESCE(r.returns, 0)
                )::numeric,
                2
            ) AS in_van,

            ROUND(
                (
                    COALESCE(d.delivered, 0)::numeric
                    /
                    NULLIF(l.loaded, 0)
                ) * 100,
                1
            ) AS fulfillment_percentage

        FROM loaded_data l
        LEFT JOIN delivery_data d ON d.item_id = l.item_id
        LEFT JOIN unload_data u ON u.item_id = l.item_id
        LEFT JOIN return_data r ON r.item_id = l.item_id
        ORDER BY delivered DESC
    """

    rows = db.execute(text(query), params).fetchall()
    sku_fulfillment = [dict(r._mapping)for r in rows]
    total_loaded = sum(x["loaded"] or 0 for x in sku_fulfillment)
    total_delivered = sum(x["delivered"] or 0 for x in sku_fulfillment)
    total_unloaded = sum(x["unloaded"] or 0 for x in sku_fulfillment)
    total_returns = sum(x["returns"] or 0 for x in sku_fulfillment)
    total_in_van = (total_loaded - total_delivered - total_unloaded - total_returns)
    sold_percentage = round((total_delivered / total_loaded) * 100, 1) if total_loaded else 0
    return {
        "summary": {
            "loaded": round(total_loaded, 2),
            "delivered": round(total_delivered, 2),
            "unloaded": round(total_unloaded, 2),
            "returns": round(total_returns, 2),
            "in_van": round(total_in_van, 2),
            "sold_percentage": sold_percentage
        },
        "sku_fulfillment": sku_fulfillment
    }