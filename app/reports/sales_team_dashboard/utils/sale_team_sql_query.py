
JOIN_BASE_SQL = """
    FROM sales_documents_header ih
    LEFT JOIN sales_documents_detail id ON id.header_id=ih.id
    LEFT JOIN salesman s ON s.id = ih.salesman_id
"""

SALES_DOC_TYPES = "'ZVCS','YDO','YDI','YSCR','ZSCS','ZFCD','YFCD','YSDR'"

RETURN_DOC_TYPES = "'YRSC','ZRVS'"

SALES_VOLUME = """
    id.quantity
    """

SALES_REVENUE = """
    id.net_total
"""

TOTAL_RETURN_REVENUE = f"""
            COALESCE(
                    SUM(
                        CASE
                            WHEN ih.document_type IN ({RETURN_DOC_TYPES})
                            THEN {SALES_REVENUE}
                            ELSE 0
                        END
                    ),
                    0
                )
            """

TOTAL_SALES_REVENUE = f"""
                 COALESCE(
                        SUM(
                            CASE
                                WHEN ih.document_type IN ({SALES_DOC_TYPES})
                                THEN {SALES_REVENUE}
                                ELSE 0
                            END
                        ),
                        0
                    )
                """

TOTAL_RETURN_VOLUME = f"""
            COALESCE(
                SUM(
                    CASE
                        WHEN ih.document_type IN ({RETURN_DOC_TYPES})
                        THEN {SALES_VOLUME}
                        ELSE 0
                    END
                ),
                0
            )
        """

TOTAL_SALES_VOLUME = f"""
        COALESCE(
                SUM(
                    CASE
                        WHEN ih.document_type IN ({SALES_DOC_TYPES})
                        THEN {SALES_VOLUME}
                        ELSE 0
                    END
                ),
                0
            )
        """

REVENUE_NET_SALES = f"""
            (
               {TOTAL_SALES_REVENUE}
                -
               {TOTAL_RETURN_REVENUE}
            )
            """

VOLUME_NET_SALES = f"""
            (
                {TOTAL_SALES_VOLUME}
                -
                {TOTAL_RETURN_VOLUME}
            ) 
            """

VISIT_OVERVIEW_SELECT = """
        vp.salesman_id,
        s.name AS salesman_name,
        COUNT(vp.id) AS total_visits,
        COUNT(DISTINCT vp.customer_id) AS customers_visited,
        COUNT(
            CASE
                WHEN LOWER(vp.shop_status::text) = '0'
                THEN 1
            END
        ) AS closed_visits
    """

SALES_GROWTH_QUERY = f"""
    SELECT
        COALESCE(
        current_data.salesman_id,
        previous_data.salesman_id
        ) AS salesman_id,

        COALESCE(
            current_data.salesman_name,
            previous_data.salesman_name,
            'Unknown'
        ) AS salesman_name,

        COALESCE(
            current_data.salesman_code,
            previous_data.salesman_code,
            ''
        ) AS salesman_code,

        COALESCE(current_data.current_sales, 0) AS current_sales,
        COALESCE(previous_data.previous_sales, 0) AS previous_sales

    FROM
    (
        SELECT
            ih.salesman_id,
            s.name AS salesman_name,
            s.osa_code AS salesman_code,
            {REVENUE_NET_SALES} AS current_sales
        {JOIN_BASE_SQL}
        {{current_join_sql}}

        WHERE
            ih.invoice_date
            BETWEEN :current_from_date
            AND :current_to_date
            {{current_where_sql}}

        GROUP BY
            ih.salesman_id,
            s.name,
            s.osa_code
    ) AS current_data

    FULL OUTER JOIN
    (
        SELECT
            ih.salesman_id,
            s.name AS salesman_name,
            s.osa_code AS salesman_code,
            {REVENUE_NET_SALES} AS previous_sales
        {JOIN_BASE_SQL}
        {{previous_join_sql}}

        WHERE
            ih.invoice_date
            BETWEEN :previous_from_date
            AND :previous_to_date
            {{previous_where_sql}}

        GROUP BY
            ih.salesman_id,
            s.name,
            s.osa_code
    ) AS previous_data

        ON current_data.salesman_id
        = previous_data.salesman_id
"""

CUSTOMER_RETENTION_QUERY = """
    WITH previous_visits AS (
        SELECT DISTINCT
            vp.salesman_id,
            vp.customer_id

        FROM visit_plan vp
        LEFT JOIN salesman s ON s.id = vp.salesman_id
        {previous_join_sql}
        WHERE
            vp.visit_start_time IS NOT NULL
            AND vp.customer_id IS NOT NULL

            AND vp.visit_start_time::date
                BETWEEN :previous_from_date
                AND :previous_to_date

            {previous_where_sql}
    ),

    current_visits AS (
        SELECT DISTINCT
            vp.salesman_id,
            vp.customer_id

        FROM visit_plan vp
        LEFT JOIN salesman s ON s.id = vp.salesman_id
        {current_join_sql}

        WHERE
            vp.visit_start_time IS NOT NULL
            AND vp.customer_id IS NOT NULL
            AND vp.visit_start_time::date
                BETWEEN :current_from_date
                AND :current_to_date
            {current_where_sql}
    ),

    salesman_previous AS (
        SELECT
            pv.salesman_id,
            COUNT(DISTINCT pv.customer_id) AS previous_customers

        FROM previous_visits pv
        GROUP BY
            pv.salesman_id
    ),

    salesman_returning AS (
        SELECT
            pv.salesman_id,
            COUNT(DISTINCT pv.customer_id) AS returning_customers

        FROM previous_visits pv
        INNER JOIN current_visits cv
            ON cv.salesman_id = pv.salesman_id
            AND cv.customer_id = pv.customer_id

        GROUP BY
            pv.salesman_id
    )

    SELECT
        sp.salesman_id,
        COALESCE(s.name, 'Unknown') AS salesman_name,
        COALESCE(s.osa_code, '') AS salesman_code,
        sp.previous_customers,
        COALESCE(sr.returning_customers, 0) AS returning_customers

    FROM salesman_previous sp
    LEFT JOIN salesman_returning sr ON sr.salesman_id = sp.salesman_id
    LEFT JOIN salesman s ON s.id = sp.salesman_id

    ORDER BY
        CASE
            WHEN sp.previous_customers > 0
            THEN
                (COALESCE(sr.returning_customers, 0)::numeric / sp.previous_customers)
            ELSE 0
        END DESC,
        s.name ASC
"""

ORDERS_VS_INVOICES_QUERY = """
    WITH order_data AS (
        SELECT
            aoh.salesman_id,
            COUNT(DISTINCT aoh.id) AS orders
        FROM agent_order_headers aoh
        LEFT JOIN salesman os ON os.id = aoh.salesman_id
        {order_join_sql}
        WHERE
            aoh.delivery_date 
            BETWEEN :from_date AND :to_date
            {order_where_sql}
        GROUP BY
            aoh.salesman_id
    ),

    invoice_data AS (
        SELECT
            ih.salesman_id,
            COUNT(DISTINCT ih.id) AS invoices
        FROM sales_documents_header ih
        LEFT JOIN salesman ins ON ins.id = ih.salesman_id
        {invoice_join_sql}
        WHERE
            ih.invoice_date
            BETWEEN :from_date AND :to_date
            {invoice_where_sql}
        GROUP BY
            ih.salesman_id
    )

    SELECT
        COALESCE(od.salesman_id, id.salesman_id) AS salesman_id,
        COALESCE(os.name, ins.name,'Unknown') AS salesman_name,
        COALESCE(os.osa_code, ins.osa_code, '') AS salesman_code,
        COALESCE(od.orders, 0) AS orders,
        COALESCE(id.invoices, 0) AS invoices
    FROM order_data od
    FULL OUTER JOIN invoice_data id ON id.salesman_id = od.salesman_id
    LEFT JOIN salesman os ON os.id = od.salesman_id
    LEFT JOIN salesman ins ON ins.id = id.salesman_id
    ORDER BY
        CASE
            WHEN COALESCE(od.orders, 0) > 0
            THEN
                (COALESCE(id.invoices, 0)::numeric / od.orders)
            ELSE 0
        END DESC,
        salesman_name ASC
"""

