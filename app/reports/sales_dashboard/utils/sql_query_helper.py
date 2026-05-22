
RETURN_BASE_SQL = """
        FROM return_header rh
        LEFT JOIN return_details rd ON rd.header_id = rh.id
        LEFT JOIN salesman s ON s.id = rh.salesman_id
        LEFT JOIN item_uoms iu
                ON iu.item_id = rd.item_id
                AND iu.uom_id = rd.uom_id
        """
  
SALES_BASE_SQL = """
        FROM invoice_headers ih
            LEFT JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
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
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
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
        LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
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

SALES_OVERVIEW_JOIN_SQL = """
        FROM invoice_headers ih
        LEFT JOIN invoice_details id ON id.header_id = ih.id
        LEFT JOIN item_uoms iu ON iu.item_id = id.item_id
        AND iu.uom_id = id.uom
    """
RETURN_OVERVIEW_JOIN_SQL = """
        FROM return_header rh
        LEFT JOIN return_details rd ON rd.header_id = rh.id
        LEFT JOIN item_uoms iu
                ON iu.item_id = rd.item_id
                AND iu.uom_id = rd.uom_id
    """

VAN_ROUTE_SELECT_SQL = """
        ih.salesman_id,
        s.osa_code AS van_id,
        s.name AS salesman,
        ac.name AS customer_name,
        ih.invoice_time,
        ac.latitude,
        ac.longitude,
    """

VAN_ROUTE_GROUP_BY = """
        ih.salesman_id,
        s.osa_code,
        s.name,
        rt.route_name,
        ac.name,
        ih.invoice_time,
        ac.latitude,
        ac.longitude
    """


LOADED_DATA_JOIN_SQL = """
        FROM tbl_load_header lh
        LEFT JOIN tbl_load_details ld ON ld.header_id = lh.id
        LEFT JOIN salesman s ON s.id = lh.salesman_id
        LEFT JOIN item_uoms iu
            ON iu.item_id = ld.item_id
            AND iu.uom_id = ld.uom
    """

UNLOADED_DATA_JOIN_SQL = """
        FROM tbl_unload_header ulh
        LEFT JOIN tbl_unload_detail uld ON uld.header_id = ulh.id
        LEFT JOIN salesman s ON s.id = ulh.salesman_id
        LEFT JOIN item_uoms iu
            ON iu.item_id = uld.item_id
            AND iu.uom_id = uld.uom
    """

ORDER_JOIN_SQL = """
        FROM agent_order_headers oh
        LEFT JOIN agent_order_details od ON od.header_id = oh.id
        LEFT JOIN salesman s ON s.id = oh.salesman_id
        LEFT JOIN item_uoms iu
                ON iu.item_id = od.item_id
                AND iu.uom_id = od.uom_id
        LEFT JOIN agent_customers ac ON ac.id = oh.customer_id
    """