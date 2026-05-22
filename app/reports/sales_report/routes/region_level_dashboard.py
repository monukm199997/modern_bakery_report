from fastapi import APIRouter, Depends, HTTPException
from app.reports.sales_report.schemas.schemas import SalesReportRequest
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context
from app.reports.sales_report.utils.sql_query_helper import VISITED_CUSTOMER_PERFORMANCE, REGION_CONTRIBUTION_TOP_ITEMS
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions

router = APIRouter(tags=["Sales Report"], dependencies=[Depends(get_current_user)])


@router.post("/region-performance")
def region_perfomance(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)

    query = f"""
            SELECT
            r.region_name,
            {ctx['value_expr']} AS value,
            0 AS total_return
            {BASE_SQL}
            {ctx['join_sql']}
            LEFT JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY r.region_name
            ORDER BY value DESC
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/region-contribution-top-items")
def region_contribution_top_items(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    query = f"""
        WITH region_item_sales AS (
                SELECT
                    r.region_name,
                    it.name AS item_name,
                    {ctx['value_expr']} AS value,
                    ROW_NUMBER() OVER (
                        PARTITION BY r.region_name
                        ORDER BY {ctx['value_expr']} DESC
                    ) AS rn
                {BASE_SQL}
                LEFT JOIN items it ON it.id = id.item_id
                {ctx['join_sql']}
                LEFT JOIN tbl_region r ON r.id = rt.region_id
                WHERE {ctx['where_sql']}
                GROUP BY r.region_name, it.name
            )
            {REGION_CONTRIBUTION_TOP_ITEMS}
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/region-wise-visited-customer-performance")
def region_wise_visited_customer_performance(
    payload: SalesReportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)
    
    rows = db.execute(text(VISITED_CUSTOMER_PERFORMANCE), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/region-trendline-sales")
def region_trendline_sales(
    payload: SalesReportRequest, 
    db: Session = Depends(get_db), 
    current_user=Depends(get_current_user)
    ):
    
    payload = apply_payload_permissions(payload, current_user)
    ctx = prepare_dashboard_context(payload)

    query = f"""
            SELECT
                {ctx['period_label_sql']} AS period,
                r.region_name,
                {ctx['value_expr']} AS value
            {BASE_SQL}
            {ctx['join_sql']}
            LEFT JOIN tbl_region r ON r.id = rt.region_id
            WHERE {ctx['where_sql']}
            GROUP BY period, r.region_name,{ctx['order_by_sql']}
            ORDER BY {ctx['order_by_sql']}, r.region_name
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/route-comparison")
def route_comparison(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    query = f"""
        SELECT
            rt.id,
            rt.route_name,
            {ctx['value_expr']} AS value,
            COUNT(DISTINCT ih.id) AS invoice_count,
            COUNT(DISTINCT ih.customer_id) AS customer_count
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {ctx['where_sql']}
        GROUP BY
            rt.id,
            rt.route_name
        ORDER BY value DESC
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result
    

@router.post("/route-trend")
def route_trend(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            {ctx['period_label_sql']} AS period,
            rt.id AS route_id,
            rt.route_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {ctx['where_sql']}
        GROUP BY
            {ctx['order_by_sql']},
            rt.id,
            rt.route_name
        ORDER BY
           {ctx['order_by_sql']}
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return {"message": "No data found for the given criteria."}
    result = [dict(r._mapping) for r in rows]
    return result


@router.post("/top-20-route")
def top_20_route(payload: SalesReportRequest,
    db:Session=Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            rt.route_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY rt.route_name
            ORDER BY value DESC
            LIMIT 20;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/bottom-20-route")
def bottom_20_route(payload: SalesReportRequest,
    db:Session=Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            rt.route_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY rt.route_name
            ORDER BY value ASC 
            LIMIT 20;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/salesman-comparison")
def salesman_comparison(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            s.id AS salesman_id,
            s.name AS salesman_name,
            {ctx['value_expr']} AS value,
            COUNT(DISTINCT ih.id) AS invoice_count,
            COUNT(DISTINCT ih.customer_id) AS customer_count
        {BASE_SQL}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            s.id,
            s.name
        ORDER BY value DESC
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/salesman_trend")
def salesman_trendline(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            {ctx['period_label_sql']} AS period,
            s.id AS salesman_id,
            s.name AS salesman_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            {ctx['order_by_sql']},
            s.id,
            s.name
        ORDER BY
            {ctx['order_by_sql']}
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/top-20-salesman")
def top_20_salesman(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            s.name as salesman_name,
            rt.route_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY s.name, rt.route_name
            ORDER BY value DESC
            LIMIT 20;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/bottom-20-salesman")
def bottom_20_salesman(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            s.name as salesman_name,
            rt.route_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY s.name, rt.route_name
            ORDER BY value ASC
            LIMIT 20;
            """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/category-comparison")
def category_comparison(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            ic.id AS item_category_id,
            ic.category_name AS item_category_name,
            {ctx['value_expr']} AS value,
            COUNT(DISTINCT id.item_id) AS total_item
        {BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            ic.id,
            ic.category_name
        ORDER BY value DESC
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/category-trend")
def category_trend(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
           {ctx['period_label_sql']} AS period,
            ic.id AS item_category_id,
            ic.category_name AS item_category_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            {ctx['order_by_sql']},
            ic.id,
            ic.category_name
        ORDER BY
            {ctx['order_by_sql']}
        """
    rows = db.execute(text(query), ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/top-20-item-category")
def top_item_category(payload:SalesReportRequest,
    db:Session=Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            ic.category_name AS item_category_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            LEFT JOIN items i ON i.id = id.item_id
            LEFT JOIN item_categories ic ON ic.id = i.category_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ic.category_name
            ORDER BY value DESC
            LIMIT 20;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/bottom-20-item-category")
def bottom_item_category(payload:SalesReportRequest,
    db:Session=Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            ic.category_name AS item_category_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            LEFT JOIN items i ON i.id = id.item_id
            LEFT JOIN item_categories ic ON ic.id = i.category_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY ic.category_name
            ORDER BY value ASC
            LIMIT 20;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/item-comparison")
def item_comparison(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            i.id AS item_id,
            i.name AS item_name,
            ic.category_name AS item_category_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            i.id,
            i.name,
            ic.category_name
        ORDER BY value DESC
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/item-trend")
def item_trendline(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
           {ctx['period_label_sql']} AS period,
            i.id AS item_id,
            i.name AS item_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            {ctx['order_by_sql']},
            i.id,
            i.name
        ORDER BY
            {ctx['order_by_sql']}
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/top-20-item")
def top_20_item(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            i.name as item_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            LEFT JOIN items i ON i.id = id.item_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY i.name
            ORDER BY value DESC
            LIMIT 20;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/bottom-20-item")
def bottom_20_item(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            i.name as item_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            LEFT JOIN items i ON i.id = id.item_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY i.name
            ORDER BY value ASC
            LIMIT 20;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/channel-comparison")
def channel_comparison(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            oc.id AS customer_channel_id,
            oc.outlet_channel AS customer_channel_name,
            {ctx['value_expr']} AS value,
            COUNT(DISTINCT ih.customer_id) AS customer_count
        {BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            oc.id,
            oc.outlet_channel
        ORDER BY value DESC
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/channel-trend")
def channel_trendline(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            {ctx['period_label_sql']},
            oc.id AS customer_channel_id,
            oc.outlet_channel AS customer_channel_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            {ctx['order_by_sql']},
            oc.id,
            oc.outlet_channel
        ORDER BY
           {ctx['order_by_sql']}
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result


@router.post("/top-20-channel")
def top_channel(payload:SalesReportRequest,
    db:Session=Depends(get_db),
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            oc.outlet_channel AS customer_channel_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            LEFT JOIN items i ON i.id = id.item_id
            LEFT JOIN item_categories ic ON ic.id = i.category_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY oc.outlet_channel
            ORDER BY value DESC
            LIMIT 20;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/bottom-20-channel")
def bottom_channel(payload:SalesReportRequest,
    db:Session=Depends(get_db),
):
    ctx = prepare_dashboard_context(payload)
    query = f"""
            SELECT
            oc.outlet_channel AS customer_channel_name,
            {ctx['value_expr']} as value
            {BASE_SQL}
            LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            LEFT JOIN items i ON i.id = id.item_id
            LEFT JOIN item_categories ic ON ic.id = i.category_id
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
            GROUP BY oc.outlet_channel
            ORDER BY value DESC
            LIMIT 20;
            """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/customer-comparison")
def customer_comparison(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            ac.id AS customer_id,
            ac.name AS customer_name,
            s.name AS salesman_name,
            oc.outlet_channel AS customer_channel_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            ac.id,
            ac.name,
            s.name,
            oc.outlet_channel
        ORDER BY value DESC
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/customer-trend")
def customer_trendline(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            {ctx['period_label_sql']},
            ac.id AS customer_id,
            ac.name AS customer_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            {ctx['order_by_sql']},
            ac.id,
            ac.name
        ORDER BY
            {ctx['order_by_sql']}
        LIMIT 10
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result


@router.post("/top_20-customer")
def top_customer(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            ac.id AS customer_id,
            ac.name AS customer_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            ac.id,
            ac.name
        ORDER BY value DESC
        LIMIT 20
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result

@router.post("/bottom_20-customer")
def bottom_customer(payload:SalesReportRequest, db:Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            ac.id AS customer_id,
            ac.name AS customer_name,
            {ctx['value_expr']} AS value
        {BASE_SQL}
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY
            ac.id,
            ac.name
        ORDER BY value ASC
        LIMIT 20
        """
    rows = db.execute(text(query),ctx["params"]).fetchall()
    if not rows:
        return{"messase":"No data found for the given criteria"}
    result = [dict(r._mapping)for r in rows]
    return result