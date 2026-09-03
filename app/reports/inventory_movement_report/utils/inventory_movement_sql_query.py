LOAD_QUANTITY = """
        ROUND(
            SUM(
                ld.qty
                / NULLIF(COALESCE(iu.upc::numeric, 1), 0)
            )::numeric,
            2
        )
    """

UNLOAD_QUANTITY = """
        ROUND(
            SUM(
                ud.qty
            )::numeric,
            2
        )
    """

SALES_QUANTITY = """
        ROUND(
            SUM(
                id.quantity
            )::numeric,
            2
        )       
    """

VAN_RETURN_QUANTITY = """
        ROUND(
            SUM(
                vrd.item_quantity
            )::numeric,
            2
        )
    """

RETURN_QUANTITY = """
        ROUND(
            SUM(
                rd.item_quantity
            )::numeric,
            2
        )
    """


ITEM_UOM_UPC_JOIN = """
        LEFT JOIN item_uoms iu ON iu.item_id = ld.item_id AND iu.uom_id = ld.displayunit
    """


UNLOAD_DATA_JOIN = """
        tbl_unload_header uh
        JOIN tbl_unload_detail ud ON ud.header_id = uh.id AND ud.deleted_at IS NULL
        LEFT JOIN salesman su ON su.id = uh.salesman_id
        LEFT JOIN tbl_route ru ON ru.id = uh.route_id
        LEFT JOIN items i ON i.id = ud.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
"""

LOAD_DATA_JOIN = f"""
        tbl_load_header lh
        JOIN tbl_load_details ld ON ld.header_id = lh.id AND ld.deleted_at IS NULL
        LEFT JOIN salesman sl ON sl.id = lh.salesman_id
        LEFT JOIN tbl_route rl ON rl.id = lh.route_id
        LEFT JOIN items i ON i.id = ld.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
        {ITEM_UOM_UPC_JOIN}
"""

SALES_DATA_JOIN = """
        invoice_headers ih
        JOIN invoice_details id ON id.header_id = ih.id AND id.deleted_at IS NULL
        LEFT JOIN salesman si ON si.id = ih.salesman_id
        LEFT JOIN tbl_route ri ON ri.id = ih.route_id
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
"""

VAN_RETURN_DATA_JOIN = """
        mbvreturn_header vrh
        JOIN mbvreturn_details vrd ON vrd.header_id = vrh.id AND vrd.deleted_at IS NULL
        LEFT JOIN salesman svr ON svr.id = vrh.salesman_id
        LEFT JOIN tbl_route rvr ON rvr.id = vrh.route_id
        LEFT JOIN items i ON i.id = vrd.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
"""

RETURN_DATA_JOIN = """
        return_header rh
        JOIN return_details rd ON rd.header_id = rh.id AND rd.deleted_at IS NULL
        LEFT JOIN salesman sr ON sr.id = rh.salesman_id
        LEFT JOIN tbl_route rr ON rr.id = rh.route_id
        LEFT JOIN items i ON i.id = rd.item_id
        LEFT JOIN item_categories ic ON ic.id = i.category_id
"""

SOLD_RETURN_NET_QTY = """
       (COALESCE(sd.sold_qty, 0) + COALESCE(vr.van_return_qty, 0) + COALESCE(r.return_qty, 0))
    """

LOAD_UNLOAD_NET_SOLD = """
            (COALESCE(u.open_stock, 0) + COALESCE(l.load_qty, 0))
            """

CLOSE_STOCK = f"""
        {LOAD_UNLOAD_NET_SOLD} - {SOLD_RETURN_NET_QTY}
"""

SALESMAN_CODE = """
        COALESCE(
            u.salesman_code,
            l.salesman_code,
            sd.salesman_code,
            vr.salesman_code,
            r.salesman_code
    ) AS salesman_code,
"""

SALESMAN_NAME ="""
        COALESCE(
            u.salesman_name,
            l.salesman_name,
            sd.salesman_name,
            vr.salesman_name,
            r.salesman_name
    ) AS salesman_name,
"""

ITEM_NAME =""" 
        COALESCE(
            u.item_name,
            l.item_name,
            sd.item_name,
            vr.item_name,
            r.item_name
        ) AS item_name,
    """

ITEM_CATEGORY = """ 
        COALESCE(
            u.item_category,
            l.item_category,
            sd.item_category,
            vr.item_category,
            r.item_category
        ) AS item_category,
    """

FINAL_SELECT = f"""
        COALESCE(u.open_stock, 0) AS open_stock,
        COALESCE(l.load_qty, 0) AS load_qty,
        COALESCE(sd.sold_qty, 0) AS sold_qty,
        COALESCE(r.return_qty, 0) AS grv_qty,
        COALESCE(vr.van_return_qty, 0) AS van_return_qty,
        {CLOSE_STOCK} AS close_stock
            
    """