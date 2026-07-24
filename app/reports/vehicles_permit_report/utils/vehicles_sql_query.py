

SELECT_QUERY = """
        v.number_plat AS vehicles_number_plate,
        r.region_code || ' - ' || r.region_name AS region,
        vp.permit_no AS permit_number,
        vp.expiry_date AS permit_expiry_date,
        vp.registration_card_no AS registration_card_number,
        vp.registration_card_expiry_date
    """

JOIN_QUERY = """
        FROM vehicle_permit vp
        LEFT JOIN tbl_vehicle v ON v.id = vp.vehicle_id
        LEFT JOIN tbl_region r ON r.id = vp.region_id
    """