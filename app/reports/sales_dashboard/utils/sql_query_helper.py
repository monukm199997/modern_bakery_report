
RETURN_BASE_SQL = """
        FROM return_header rh
        LEFT JOIN return_details rd ON rd.header_id = rh.id
        LEFT JOIN salesman s ON s.id = rh.salesman_id
        """
    #         LEFT JOIN item_uoms iu
    #             ON iu.item_id = rd.item_id
    #             AND iu.uom_id = rd.uom_id
SALES_BASE_SQL = """
        FROM invoice_headers ih
            LEFT JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN salesman s ON s.id = ih.salesman_id
        """

ORDER_BASE_SQL = """
        FROM agent_order_headers oh
        LEFT JOIN agent_order_details od ON od.header_id = oh.id
        LEFT JOIN salesman s ON s.id = oh.salesman_id
        LEFT JOIN item_uoms iu
            ON iu.item_id = od.item_id
            AND iu.uom_id = od.uom_id
        """

DELIVERY_BASE_SQL = """
        FROM agent_delivery_headers dh
        LEFT JOIN agent_delivery_details dd ON dd.header_id = dh.id
        LEFT JOIN salesman s ON s.id = dh.salesman_id
        LEFT JOIN item_uoms iu
            ON iu.item_id = dd.item_id
            AND iu.uom_id = dd.uom_id
        """

SALES_ITEM_JOINS_SQL = """
                LEFT JOIN items i ON i.id = id.item_id
                LEFT JOIN item_categories ic ON ic.id = i.category_id
            """
SALES_REGION_JOINS_SQL = """
                LEFT JOIN tbl_route sales_rt ON sales_rt.id = ih.route_id
                LEFT JOIN tbl_region r ON r.id = sales_rt.region_id
            """
SALES_BASE_SQL_1 = """
        FROM invoice_headers ih
            LEFT JOIN invoice_details id ON id.header_id = ih.id
        """
RETURN_CHANNEL_JOINS_SQL = """
                LEFT JOIN agent_customers cst ON cst.id = rh.customer_id
                LEFT JOIN outlet_channel oc ON oc.id = cst.outlet_channel_id
            """
RETURN_ITEM_JOINS_SQL = """
                LEFT JOIN items i ON i.id = rd.item_id
                LEFT JOIN item_categories ic ON ic.id = i.category_id
            """
RETURN_REGION_JOINS_SQL = """
                LEFT JOIN tbl_route return_rt ON return_rt.id = rh.route_id
                LEFT JOIN tbl_region r ON r.id = return_rt.region_id
            """

TREND_DATA_SELECT_SQL = """
            SELECT
                x.segment,
                json_agg(
                json_build_object(
                'day',
                TO_CHAR(x.sales_date, 'Dy'),
                'sales',
                x.daily_sales
            )
            ORDER BY x.sales_date
        """

PREVIOUS_WEEK_WHERE_SQL = """
        WHERE ih.invoice_date BETWEEN
        CURRENT_DATE - INTERVAL '14 day'
        AND
        CURRENT_DATE - INTERVAL '8 day'
    """

SALES = """
        ROUND(s.sales::numeric, 2) AS sales
    """
RETURN = """
         ROUND(COALESCE(r.returns, 0)::numeric, 2) AS returns
    """
SHARE_PERCENTAGE = """
        ROUND((s.sales/SUM(s.sales) OVER()) * 100, 1) AS share_percentage
    """
WOW ="""
    ROUND(((COALESCE(c.current_sales, 0) - COALESCE(p.previous_sales, 0)) / NULLIF(p.previous_sales, 0)) * 100, 1) AS wow
    """


SELECT = F"""
        s.segment,
        {SALES},
        {RETURN},
        {SHARE_PERCENTAGE},
        {WOW},
        COALESCE(t.trend_7d, '[]'::json) AS trend_7d
    """

FROM_CLAUSE = """
        FROM sales_data s
        LEFT JOIN return_data r ON r.segment = s.segment
        LEFT JOIN current_week_sales c ON c.segment = s.segment
        LEFT JOIN previous_week_sales p ON p.segment = s.segment
        LEFT JOIN trend_data t ON t.segment = s.segment
        ORDER BY s.sales DESC
        LIMIT :limit
    """


ROUTE_COUNT = """
        COUNT(DISTINCT ih.route_id) AS route       
    """

SALESMAN_COUNT = """
    COUNT(DISTINCT ih.salesman_id) AS salesman
"""

FROM_CLAUSE_1 = """
        FROM invoice_headers ih
        JOIN invoice_details id ON id.header_id = ih.id
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        LEFT JOIN tbl_region r ON r.id = rt.region_id
    """
REGION_SALES = """
        ROUND(r.sales::numeric, 2) AS sales
    """
REGION_CONTRIBUTION = """
        ROUND((r.sales/SUM(r.sales) OVER()) * 100, 1) AS national_share_percentage
    """
WEEK_OVER_WEEK ="""
        ROUND(((COALESCE(c.current_sales, 0) - COALESCE(p.previous_sales, 0)) / NULLIF(p.previous_sales, 0)) * 100, 1) AS wow
    """
PERFORMANCE_SCORE = """
        ROUND(((r.sales / SUM(r.sales) OVER()) * 100) * 2.1, 0) AS performance_score
    """

SELECT_1 = f"""
            r.region,
            {REGION_SALES},
            {REGION_CONTRIBUTION},
            {WEEK_OVER_WEEK},
            r.route,
            r.salesman,
            {PERFORMANCE_SCORE}
        """


TOTAL_AND_COMPLETE_STOPS = """
        COUNT(*) AS total_stops,
        COUNT(
            CASE
                WHEN vp.shop_status = '1' 
                THEN 'completed'
            END
            ) AS completed_stops
        """

VISIT_BASE_JOIN = """
            FROM visit_plan vp
                LEFT JOIN salesman s ON s.id = vp.salesman_id
        """

VISIT_SELECT_FIELS = """
        TO_CHAR(
            vp.visit_start_time,
            'HH24:MI'
            ) AS visit_time,
            ac.name AS customer_name,
            oc.outlet_channel AS channel,
            vp.shop_status,
            vp.latitude,
            vp.longitude,
        """

VISITE_JOINS_SQL = """
        LEFT JOIN agent_customers ac ON ac.id = vp.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            LEFT JOIN invoice_headers ih ON ih.customer_id = vp.customer_id
            LEFT JOIN invoice_details id ON id.header_id = ih.id
        """

VISIT_GROUP_BY = """
        vp.visit_start_time,
        ac.name,
        oc.outlet_channel,
        vp.shop_status,
        vp.latitude,
        vp.longitude
    """

VAN_INFO = """
        s.id AS salesman_id,
        rt.route_name,
        s.name AS salesman_name,
        COUNT(
            DISTINCT vp.customer_id
        ) AS assigned_customers
    """

VAN_INFO_GROUP_BY = """
        rt.route_name,
        s.name,
        s.id
    """
VAN_INFO_SELECT = """
        (
        SELECT json_agg(v)
            FROM van_info v
        ) AS van_info
    """
SUMMURY_SELECT = """
        (
        SELECT row_to_json(s)
        FROM (
            SELECT
                completed_stops,
                total_stops,
                ROUND((completed_stops::numeric / NULLIF(total_stops, 0) ) * 100, 1) AS progress_percentage
                FROM summary
            ) s
        ) AS summary
    """

TIMELINE_SELECT = """
        (
        SELECT json_agg(t)
        FROM timeline t
        ) AS timeline
    """

VISIT_FINAL_SELECT = f"""
        {VAN_INFO_SELECT},
        {SUMMURY_SELECT},
        {TIMELINE_SELECT}
    """