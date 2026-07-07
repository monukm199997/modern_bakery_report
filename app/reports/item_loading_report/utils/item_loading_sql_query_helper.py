
DRILL_DOWN_MAP = {
    "item": {
        "order_select": """
            aod.item_id,
            i.code AS item_code,
            i.name AS item,
            i.barcode,
            u.name AS uom_name,
            iu_pc.upc AS upc
        """,
        "receive_select": """
            ld.item_id,
            i2.code AS item_code,
            i2.name AS item,
            i2.barcode,
            u2.name AS uom_name,
            iu_pc2.upc AS upc
        """,
        "final_select": """
            COALESCE(o.item_code, r.item_code) AS item_code,
            COALESCE(o.item, r.item) AS item,
            COALESCE(o.barcode, r.barcode) AS barcode,
            COALESCE(o.uom_name, r.uom_name) AS uom_name,
            COALESCE(o.upc, r.upc) AS upc
        """,
        "order_group_by": """
            aod.item_id,
            i.code,
            i.name,
            i.barcode,
            u.name,
            iu_pc.upc
        """,
        "receive_group_by": """
            ld.item_id,
            i2.code,
            i2.name,
            i2.barcode,
            u2.name,
            iu_pc2.upc
        """,
        "join_on": "o.item_id = r.item_id",
        "order_joins": """
            LEFT JOIN items i
                ON i.id = aod.item_id
            LEFT JOIN uom u
                ON u.id = aod.uom_id
        """,
        "receive_joins": """
            LEFT JOIN items i2
                ON i2.id = ld.item_id
            LEFT JOIN uom u2
                ON u2.id = ld.uom
        """,
    },

    "route": {
        "order_select": """
            aoh.route_id,
            rt.route_code,
            rt.route_name AS route,
            s.name AS salesman,
            s.osa_code AS salesman_code
        """,
        "receive_select": """
            lh.route_id,
            rt2.route_code,
            rt2.route_name AS route,
            s2.name AS salesman,
            s2.osa_code AS salesman_code
        """,
        "final_select": """
            COALESCE(o.route_code, r.route_code) AS route_code,
            COALESCE(o.route, r.route) AS route,
            COALESCE(o.salesman, r.salesman) AS salesman,
            COALESCE(o.salesman_code, r.salesman_code) AS salesman_code
        """,
        "order_group_by": """
            aoh.route_id,
            rt.route_code,
            rt.route_name,
            s.name,
            s.osa_code
        """,
        "receive_group_by": """
            lh.route_id,
            rt2.route_code,
            rt2.route_name,
            s2.name,
            s2.osa_code
        """,
        "join_on": """
            o.route_id = r.route_id
            AND o.salesman_code = r.salesman_code
        """,
    },
}



ORDER_QUANTITY = """
        ROUND(
            SUM(
                aod.quantity * COALESCE(iu_pc.upc::numeric, 1)
                / NULLIF(iu_pac.upc::numeric, 0)
            )::numeric,
            2
        )
    """

LOAD_QUANTITY = """
        ROUND(
            SUM(
                ld.qty * COALESCE(iu_pc2.upc::numeric, 1)
                / NULLIF(iu_pac.upc::numeric, 0)
            )::numeric,
            2
        )
    """

ITEM_UOM_UPC_JOIN = """
        LEFT JOIN item_uoms iu_pc ON iu_pc.item_id = aod.item_id AND iu_pc.uom_id = aod.uom_id
        LEFT JOIN item_uoms iu_pac ON iu_pac.item_id = aod.item_id AND iu_pac.name = 'PAC'
    """

ORDER_DATA_JOIN = f"""
        agent_order_headers aoh
        LEFT JOIN agent_order_details aod ON aod.header_id = aoh.id AND aod.deleted_at IS NULL
        JOIN agent_customers ac ON ac.id = aoh.customer_id AND ac.is_driver = 1
        LEFT JOIN salesman s ON s.id = aoh.salesman_id
        LEFT JOIN tbl_route rt ON rt.id = aoh.route_id
        {ITEM_UOM_UPC_JOIN}
    """
ITEM_UOM_UPC_JOIN2 ="""
        LEFT JOIN item_uoms iu_pc2 ON iu_pc2.item_id = ld.item_id AND iu_pc2.uom_id = ld.uom
        LEFT JOIN item_uoms iu_pac ON iu_pac.item_id = ld.item_id AND iu_pac.name = 'PAC'
    """
RECIEVE_DATA_JOIN = f"""
        tbl_load_header lh
        LEFT JOIN tbl_load_details ld ON ld.header_id = lh.id AND ld.deleted_at IS NULL
        LEFT JOIN salesman s2 ON s2.id = lh.salesman_id
        LEFT JOIN tbl_route rt2 ON rt2.id = lh.route_id
        {ITEM_UOM_UPC_JOIN2}
    """

FINAL_SELECT = """
        COALESCE(o.ordered_qty, 0) AS salesman_ordered_qty,
        COALESCE(r.received_qty, 0) AS received_qty,
        COALESCE(o.ordered_qty, 0) - COALESCE(r.received_qty, 0) AS diff,
        o.remarks_by_stores
    """