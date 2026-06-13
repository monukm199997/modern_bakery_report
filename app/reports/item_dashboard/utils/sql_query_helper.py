STOCK_BASE_SQL = """
    FROM salesmanitemstocks_header h
    LEFt JOIN salesmanitemstocks_details d ON d.header_id=h.id
    LEFT JOIN item_uoms iu
            ON iu.item_id = d.item_id
            AND iu.uom_id = d.uom_id
"""

STOCK_BASE_SQL_1 = """
    FROM salesmanitemstocks_header h
    LEFT JOIN salesmanitemstocks_details d ON d.header_id=h.id
"""


SALES_BASE_SQL = """
    FROM invoice_headers ih
    LEFT JOIN invoice_details id ON id.header_id=ih.id
    LEFT JOIN item_uoms iu
            ON iu.item_id = id.item_id
            AND iu.uom_id = id.uom
"""