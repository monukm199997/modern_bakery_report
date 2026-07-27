
SELECT_QUERY = """
        ac.osa_code AS customer_code,
        ac.name AS customer_name,
        ac.dateof_creation,
        CASE
            WHEN ac.status = 1 THEN 'Active'
            WHEN ac.status = 0 THEN 'Inactive'
        END AS status,
        rt.route_code,
        rt.route_name,
        s.osa_code AS salesman_code,
        s.name AS salesman_name,
        oc.outlet_channel,
        ac.trade_license_no AS tl_number,
        ac.tin_no,
        ac.customer_type,
        ac.cust_group,
        ac.payment_type AS payment_terms,
        ac.street || ' - ' || ac.city AS address,
        r.region_name,
        ac.latitude,
        ac.longitude
    """

JOIN_QUERY = """
        FROM agent_customers ac
        LEFT JOIN tbl_route rt ON rt.id = ac.route_id
        LEFT JOIN salesman s ON s.route_id = ac.route_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN tbl_region r ON r.id = ac.region_id
    """