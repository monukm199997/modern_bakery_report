
SALES_DOC_TYPES = "'ZVCS','YDO','YDI','YSCR','ZSCS','ZFCD','YFCD','YSDR'"
RETURN_DOC_TYPES = "'YRSC','ZRVS'"

DRILL_DOWN_MAP = {
    "customer": {
        "select": """
            ac.osa_code AS customer_code,
            ac.name AS customer
        """,
        "group_by": "ac.osa_code, ac.name",
    },
    "item": {
        "select": """
            i.code AS item_code,
            i.name AS item,
            i.barcode
        """,
        "group_by": "i.code, i.name, i.barcode",
    },
}

FACT_AGGREGATES = f"""
    SUM(CASE WHEN sdh.document_type IN ({SALES_DOC_TYPES})  THEN sdd.net_total ELSE 0 END) AS sales_amount,
    SUM(CASE WHEN sdh.document_type IN ({RETURN_DOC_TYPES}) THEN sdd.net_total ELSE 0 END) AS return_amount,
    SUM(CASE WHEN sdh.document_type IN ({SALES_DOC_TYPES})  THEN sdd.quantity  ELSE 0 END) AS sales_qty,
    SUM(CASE WHEN sdh.document_type IN ({RETURN_DOC_TYPES}) THEN sdd.quantity  ELSE 0 END) AS return_qty
"""

REVENUE_METRICS = [
    "COALESCE(SUM(f.sales_amount), 0) AS revenue_gross_sales",
    "COALESCE(SUM(f.return_amount), 0) AS revenue_sales_return",
    "ROUND((COALESCE(SUM(f.return_amount), 0) / NULLIF(SUM(f.sales_amount), 0) * 100)::numeric, 2) AS revenue_return_percent",
    "COALESCE(SUM(f.sales_amount) - SUM(f.return_amount), 0) AS revenue_net_sales",
]

VOLUME_METRICS = [
    "COALESCE(SUM(f.sales_qty), 0) AS volume_gross_sales",
    "COALESCE(SUM(f.return_qty), 0) AS volume_sales_return",
    "ROUND((COALESCE(SUM(f.return_qty), 0) / NULLIF(SUM(f.sales_qty), 0) * 100)::numeric, 2) AS volume_return_percent",
    "COALESCE(SUM(f.sales_qty) - SUM(f.return_qty), 0) AS volume_net_sales",
]