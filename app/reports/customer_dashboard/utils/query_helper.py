
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
            ) AS percentage,
    """

TOTAL_CUSTOMER_IN_ROUTE = """
            rt.route_name AS route_name,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage,
    """

TOTAL_CUSTOMER_IN_CHANNEL = """
            oc.outlet_channel,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage,
        
    """

TOTAL_CUSTOMER_IN_CATEGORY = """
            cc.customer_category_name,
            COUNT(DISTINCT ih.customer_id) AS total_customers,
            ROUND(
                COUNT(DISTINCT ih.customer_id)*100.0 /
                SUM(COUNT(DISTINCT ih.customer_id)) OVER (),2
            ) AS percentage,
    """