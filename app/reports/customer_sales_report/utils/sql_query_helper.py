
BASE_SQL = """
        FROM invoice_headers ih
            LEFT JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
        """

OPTIONAL_JOINS_SQL = """
                LEFT JOIN agent_customers cst ON cst.id = ih.customer_id
                LEFT JOIN customer_categories cc ON cc.id = cst.category_id
                """

OPTIONAL_JOINS_SQL_1 = """
            LEFT JOIN agent_customers cst ON cst.id = ih.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = cst.outlet_channel_id
            """

ELIGIBLE_CUSTOMERS_SQL = """
        eligible_customers AS (
            SELECT
                ac.id
            FROM agent_customers ac  
        )
        """

SALES_BY_CUSTOMER_SQL = """
            sales_by_customer AS (
                SELECT 
                    DISTINCT ih.customer_id
                FROM invoice_headers ih
                LEFT JOIN invoice_details id ON id.header_id = ih.id
                LEFT JOIN item_uoms iu
                        ON iu.item_id = id.item_id
                        AND iu.uom_id = id.uom
            )
        """


CUSTOMER_SALES_KPIS_SQL = f"""
                    WITH {ELIGIBLE_CUSTOMERS_SQL},
                    {SALES_BY_CUSTOMER_SQL}
                    SELECT
                        COUNT(ec.id) AS total_customers,
                        COUNT(s.customer_id) AS active_sales_customers,
                        COUNT(ec.id) - COUNT(s.customer_id) AS inactive_sales_customers
                    FROM eligible_customers ec
                    LEFT JOIN sales_by_customer s
                        ON s.customer_id = ec.id
                    """

SELECT = """
            SELECT
                ac.osa_code || '-' || ac.name AS "Customer",
                oc.outlet_channel_code || '-' || oc.outlet_channel AS "Customer Channel",
                cat.customer_category_code || '-' || cat.customer_category_name AS "Customer Category",
                ac.contact_no AS "Contact Number",
                r.region_code || '-' || r.region_name AS "Region",
                rt.route_name AS "Route",
                
        """

FROM_CLAUSE = """
        FROM invoice_headers ih
            LEFT JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN salesman s ON s.id = ih.salesman_id
            LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
            LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
            LEFT JOIN customer_categories cat ON cat.id = ac.category_id
        """

GROUP_BY = """
        GROUP BY
            ac.osa_code, ac.name, ac.contact_no,
            r.region_code, r.region_name,
            rt.route_name,
            oc.outlet_channel_code, oc.outlet_channel,
            cat.customer_category_code, cat.customer_category_name
        """

ITEM_QUERY = f"""
        SELECT DISTINCT
            COALESCE(i.name, 'Unknown Item') AS item_name,
            COALESCE(TRIM(ic.category_name), 'Unknown') AS item_category_name
        {FROM_CLAUSE}
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id

        """