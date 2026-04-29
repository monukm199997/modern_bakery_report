TOTAL_CUSTOMERS = """ WITH total_customers AS (
                    SELECT DISTINCT
                        r.id AS region_id,
                        r.region_name,
                        ac.id AS customer_id
                    FROM agent_customers ac
                    JOIN tbl_route rt ON rt.id = ac.route_id
                    JOIN tbl_region r ON r.id = rt.region_id
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
                    JOIN invoice_details id ON id.header_id = ih.id
                    JOIN agent_customers ac ON ac.id = ih.customer_id
                    JOIN tbl_route rt ON rt.id = ih.route_id
                    JOIN tbl_region r ON r.id = rt.region_id
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