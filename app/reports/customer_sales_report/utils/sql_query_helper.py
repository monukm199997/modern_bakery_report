
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