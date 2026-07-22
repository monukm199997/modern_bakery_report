BASE_SQL_JOIN = """
        FROM visit_plan vp
        LEFT JOIN agent_customers ac ON ac.id = vp.customer_id
        LEFT JOIN tbl_route rt ON rt.id = vp.route_id
        LEFT JOIN salesman s ON s.id = vp.salesman_id
        LEFT JOIN users sup ON sup.id = s.superwiser_id AND sup.role = 108
        LEFT JOIN (
            SELECT DISTINCT ON (salesman_id, DATE(created_at))
                salesman_id,
                DATE(created_at) AS login_date,
                location
            FROM tbl_salesman_location
            ORDER BY salesman_id, DATE(created_at), created_at
        ) tsl
            ON tsl.salesman_id = vp.salesman_id
        AND tsl.login_date = DATE(vp.visit_start_time)
"""

DATE = """
        TO_CHAR(vp.visit_start_time, 'YYYY-MM-DD') AS date
    """

TIME_SPENT = """
        COALESCE((vp.visit_end_time - vp.visit_start_time)::text, '-' ) AS time_spent
    """
IDLE_TIME = """
        COALESCE(
         (vp.visit_start_time - LAG(vp.visit_end_time) OVER (PARTITION BY vp.salesman_id ORDER BY vp.visit_start_time)
         )::text, '-' ) AS idle_time
    """
LOGIN_TIME = """
        TO_CHAR((tsl.location::jsonb -> 0 ->> 'time')::timestamp, 'HH24:MI:SS') AS login_time
    """

VISIT_START_TIME = """
    TO_CHAR(vp.visit_start_time, 'HH24:MI:SS') AS visit_start_time
"""

VISIT_END_TIME = """
    TO_CHAR(vp.visit_end_time, 'HH24:MI:SS') AS visit_end_time
"""


SELECT_SQL = f"""
        {DATE},
        ac.osa_code AS customer_code,
        ac.name AS customer_name,
        ac.contact_no AS customer_contact,
        rt.route_code AS route_code,
        rt.route_name AS route_name,
        s.osa_code AS salesman_code,
        s.name AS salesman_name,
        sup.name AS superwiser,
        {VISIT_START_TIME},
        {VISIT_END_TIME},
        {TIME_SPENT},
        {IDLE_TIME},
        {LOGIN_TIME},
        ac.latitude AS customer_latitude,
        ac.longitude AS customer_longitude,
        vp.latitude,
        vp.longitude,
        vp.shop_status,
        vp.remark AS reason
"""