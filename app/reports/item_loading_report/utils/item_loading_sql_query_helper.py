
DRILL_DOWN_MAP = {
    "item": {
        "order_select": """
            aod.item_id,
            i.code AS item_code,
            i.name AS item,
            i.barcode
        """,
        "receive_select": """
            ld.item_id,
            i2.code AS item_code,
            i2.name AS item,
            i2.barcode
        """,
        "final_select": """
            COALESCE(o.item_code, r.item_code) AS item_code,
            COALESCE(o.item, r.item) AS item,
            COALESCE(o.barcode, r.barcode) AS barcode
        """,
        "order_group_by": """
            aod.item_id,
            i.code,
            i.name,
            i.barcode,
            CASE
                WHEN iu_pac.upc IS NOT NULL THEN 'PAC'
                ELSE iu_invoice.name
            END,
            CASE
                WHEN iu_pac.upc IS NOT NULL THEN iu_pac.upc
                ELSE iu_invoice.upc
            END
        """,
        "receive_group_by": """
            ld.item_id,
            i2.code,
            i2.name,
            i2.barcode
        """,
        "join_on": "o.item_id = r.item_id",
        "order_joins": """
            LEFT JOIN items i
                ON i.id = aod.item_id
        """,
        "receive_joins": """
            LEFT JOIN items i2
                ON i2.id = ld.item_id
        """,
    },

    "route": {
        "order_select": """
            rt.route_code,
            rt.route_name AS route
        """,
        "receive_select": """
            rt2.route_code,
            rt2.route_name AS route
        """,
        "final_select": """
            COALESCE(o.route_code, r.route_code) AS route_code,
            COALESCE(o.route, r.route) AS route
        """,
        "order_group_by": """
            rt.route_code,
            rt.route_name
        """,
        "receive_group_by": """
            rt2.route_code,
            rt2.route_name
        """,
        "join_on": """
            o.route_code = r.route_code
        """,
    },
}



ORDER_QUANTITY = """
    ROUND(
        SUM(
            CASE
                WHEN iu_pac.upc IS NOT NULL THEN
                    aod.quantity * COALESCE(iu_invoice.upc::numeric, 1)
                    / NULLIF(iu_pac.upc::numeric, 0)
                ELSE
                    aod.quantity
            END
        )::numeric,
        2
    )
"""

LOAD_QUANTITY = """
        ROUND(
            SUM(
                ld.qty
                / NULLIF(COALESCE(iu2.upc::numeric, 1), 0)
            )::numeric,
            2
        )
    """

ITEM_UOM_UPC_JOIN = """
    LEFT JOIN item_uoms iu_invoice ON iu_invoice.item_id = aod.item_id AND iu_invoice.uom_id = aod.uom_id
    LEFT JOIN item_uoms iu_pac ON iu_pac.item_id = aod.item_id AND iu_pac.name = 'PAC'
"""

DISPLAY_UOM = """
    CASE
        WHEN COUNT(DISTINCT CASE WHEN iu_pac.upc IS NOT NULL THEN 'PAC' ELSE iu_invoice.name END) = 1
        THEN MAX(CASE WHEN iu_pac.upc IS NOT NULL THEN 'PAC' ELSE iu_invoice.name END)
        ELSE 'MIXED'
    END
"""

DISPLAY_UPC = """
    CASE
        WHEN COUNT(DISTINCT CASE WHEN iu_pac.upc IS NOT NULL THEN iu_pac.upc::numeric ELSE iu_invoice.upc::numeric END) = 1
        THEN MAX(CASE WHEN iu_pac.upc IS NOT NULL THEN iu_pac.upc::numeric ELSE iu_invoice.upc::numeric END)
        ELSE NULL
    END
"""

ORDER_DATA_JOIN = f"""
        agent_order_headers aoh
        LEFT JOIN agent_order_details aod ON aod.header_id = aoh.id AND aod.deleted_at IS NULL
        JOIN agent_customers ac ON ac.id = aoh.customer_id AND ac.is_driver = 1
        LEFT JOIN salesman s ON s.id = aoh.salesman_id
        LEFT JOIN tbl_route rt ON rt.id = aoh.route_id
        {ITEM_UOM_UPC_JOIN}
    """

ITEM_UOM_UPC_JOIN2 = """
        LEFT JOIN item_uoms iu2 ON iu2.item_id = ld.item_id AND iu2.uom_id = ld.displayunit
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