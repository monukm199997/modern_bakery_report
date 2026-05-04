
COMPANY_SALES = """
            SELECT
                c.company_name,
                SUM(value) AS value
            FROM filtered_sales fs
            LEFT JOIN tbl_company c
                ON c.id = fs.company_id
            GROUP BY c.company_name
            ORDER BY value DESC
            """

REGION_CONTRIBUTION_TOP_ITEMS = """
            SELECT 
                region_name, item_name, value
            FROM region_item_sales
            WHERE rn = 1
            ORDER BY value DESC
        """


TOTAL_CUSTOMERS = """ WITH total_customers AS (
                    SELECT DISTINCT
                        r.id AS region_id,
                        r.region_name,
                        ac.id AS customer_id
                    FROM agent_customers ac
                    LEFT JOIN tbl_route rt ON rt.id = ac.route_id
                    LEFT JOIN tbl_region r ON r.id = rt.region_id
                    WHERE
                        ac.status = 1
                        AND r.id = ANY(:region_ids)
                )"""

VISITED_CUSTOMERS = """
                    visited_customers AS (
                    SELECT DISTINCT
                        r.id AS region_id,
                        ih.customer_id
                    FROM invoice_headers ih
                    LEFT JOIN invoice_details id ON id.header_id = ih.id
                    LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
                    LEFT JOIN tbl_route rt ON rt.id = ih.route_id
                    LEFT JOIN tbl_region r ON r.id = rt.region_id
                    WHERE
                        ac.status = 1
                        AND id.item_total > 0
                        AND ih.invoice_date BETWEEN :from_date AND :to_date
                        AND r.id = ANY(:region_ids)
                )"""

VISITED_CUSTOMER_PERFORMANCE = f"""

                {TOTAL_CUSTOMERS},
                {VISITED_CUSTOMERS}
                SELECT
                        t.region_name,
                        COUNT(DISTINCT v.customer_id) AS visited_customers,
                        COUNT(DISTINCT t.customer_id) AS total_customers,
                        ROUND(
                            (COUNT(DISTINCT v.customer_id)::numeric
                            / NULLIF(COUNT(DISTINCT t.customer_id), 0)) * 100,
                            2
                        ) AS visited_percentage
                    FROM total_customers t
                    LEFT JOIN visited_customers v
                        ON t.customer_id = v.customer_id
                        AND t.region_id = v.region_id
                    GROUP BY t.region_id, t.region_name
                    ORDER BY t.region_name;
                """


JOINS_SQL = """
        FROM invoice_headers ih
        LEFT JOIN invoice_details id ON id.header_id = ih.id
        LEFT JOIN salesman s ON s.id = ih.salesman_id
        LEFT JOIN items it ON it.id = id.item_id
        LEFT JOIN item_categories cat ON cat.id = it.category_id
        LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
        """