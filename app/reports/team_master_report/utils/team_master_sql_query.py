
SELECT_QUERY = """
        v.vehicle_code,
        v.number_plat,
        rt.route_code,
        rt.route_name,
        s.osa_code AS salesman_code,
        s.name AS salesman_name,
        sup.name AS superwiser,
        s.dateof_join,
        r.region_name
    """

JOIN_QUERY = """
        FROM salesman s
        LEFT JOIN tbl_route rt ON s.route_id = rt.id
        LEFT JOIN tbl_vehicle v ON v.id = rt.vehicle_id
        LEFT JOIN users sup ON sup.id = s.superwiser_id AND sup.role = 108
        LEFT JOIN tbl_region r ON rt.region_id = r.id
"""