
TOTAL_CUSTOMER = """
            (
            SELECT COUNT(DISTINCT ih.customer_id) 
            FROM invoice_headers ih 
            ) AS total_customer
        """

TOTAL_PENDING_CUSTOMER = """
            (
            SELECT COUNT(DISTINCT nc.id)
            FROM new_customer nc
            WHERE nc.status = 0
            ) AS total_pending_customer
        """

TOTAL_NEW_CUSTOMER = """
            (
            SELECT COUNT (DISTINCT ac.id) 
            FROM agent_customers ac
            ) AS total_new_customer
        """

BASE_SQL = """
        FROM invoice_headers ih
        LEFT JOIN invoice_details id ON id.header_id = ih.id
        LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
        """

TOTAL_CUSTOMER_IN_REGION = """
            r.region_name,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage
        FROM invoice_headers ih
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        LEFT JOIN tbl_region r ON r.id = rt.region_id
    """

TOTAL_CUSTOMER_IN_ROUTE = """
            rt.route_name AS route_name,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage
        FROM invoice_headers ih
        JOIN tbl_route rt ON rt.id = ih.route_id
    """

TOTAL_CUSTOMER_IN_CHANNEL = """
            oc.outlet_channel,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage
        FROM invoice_headers ih
        JOIN agent_customers ac ON ac.id = ih.customer_id
        JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
    """

TOTAL_CUSTOMER_IN_CATEGORY = """
            cc.customer_category_name,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage
        FROM invoice_headers ih
        JOIN agent_customers ac ON ac.id = ih.customer_id
        JOIN customer_categories cc ON cc.id = ac.category_id
    """