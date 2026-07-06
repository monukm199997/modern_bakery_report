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
        i.barcode,
        u.name AS uom_name,
        iu.upc AS upc
        """,
        "group_by": "i.code, i.name, i.barcode, u.name, iu.upc",
    },
    "salesman": {
        "select": """
        sm.osa_code AS salesman_code,
        sm.name AS salesman,
        sup.name AS superwiser
        """,
        "group_by": "sm.osa_code, sm.name, sup.name",
    },
    "route": {
        "select": """
        rt.route_code,
        rt.route_name AS route,
        sm.name AS salesman,
        sm.osa_code AS salesman_code
        """,
        "group_by": "rt.route_code, rt.route_name, sm.name, sm.osa_code",
    },
    "supervisor": {
        "select": "sup.name AS supervisor",
        "group_by": "sup.name",
    },
    "customer_group": {
        "select": "ac.cust_group AS customer_group",
        "group_by": "ac.cust_group",
    },
    "customer_group_1": {
        "select": """
            ac."CustomerGroupDesc" AS customer_group_1
        """,
        "group_by": """
                ac."CustomerGroupDesc"
                """,
    },
    "customer_group_2": {
         "select": """
            ac."CustomerGroupDesc2" AS customer_group_2
        """,
        "group_by": """
                ac."CustomerGroupDesc2"
                """,
    },
    "channel": {
        "select": """
        oc.outlet_channel_code AS channel_code,
        oc.outlet_channel AS channel
        """,
        "group_by": "oc.outlet_channel_code, oc.outlet_channel",
    },
}

SALES_VOLUME = """
    sdd.quantity
    """
SALES_REVENUE = """
    sdd.net_total
"""

REVENUE_GROSS_SALES = f"""COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type IN ({SALES_DOC_TYPES})
                        THEN {SALES_REVENUE}
                        ELSE 0
                    END
                ),
                0
            ) AS revenue_gross_sales
        """

REVENUE_GROSS_RETURN = f"""COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type IN ({RETURN_DOC_TYPES})
                        THEN {SALES_REVENUE}
                        ELSE 0
                    END
                ),
                0
            ) AS revenue_sales_return
            """


REVENUE_ZERO = f"""
            COALESCE(
                    SUM(
                        CASE
                            WHEN sdh.document_type IN ({SALES_DOC_TYPES})
                            THEN {SALES_REVENUE}
                            ELSE 0
                        END
                    ),
                    0   
                ) = 0 THEN 0
            """

TOTAL_RETURN_REVENUE = f"""
            COALESCE(
                    SUM(
                        CASE
                            WHEN sdh.document_type IN ({RETURN_DOC_TYPES})
                            THEN {SALES_REVENUE}
                            ELSE 0
                        END
                    ),
                    0
                )
            """

TOTAL_SALES_REVENUE = f"""
                 COALESCE(
                        SUM(
                            CASE
                                WHEN sdh.document_type IN ({SALES_DOC_TYPES})
                                THEN {SALES_REVENUE}
                                ELSE 0
                            END
                        ),
                        0
                    )
                """


REVENUE_RETURN_PERCENT = f"""
            ROUND(
                (
                    CASE
                        WHEN
                            {REVENUE_ZERO}
                        ELSE
                            (
                               {TOTAL_RETURN_REVENUE}
                                /
                               {TOTAL_SALES_REVENUE}
                            ) * 100
                    END
                )::numeric,
                2
            ) AS revenue_return_percent
            """

REVENUE_NET_SALES = f"""
            (
               {TOTAL_SALES_REVENUE}
                -
               {TOTAL_RETURN_REVENUE}
            ) AS revenue_net_sales
            """


VOLUME_GROSS_SALES = f"""
        COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type IN ({SALES_DOC_TYPES})
                        THEN {SALES_VOLUME}
                        ELSE 0
                    END
                ),
                0
            ) AS volume_gross_sales
         """

VOLUME_GROSS_RETURN = f"""
        COALESCE(
            SUM(
                CASE
                    WHEN sdh.document_type IN ({RETURN_DOC_TYPES})
                    THEN {SALES_VOLUME}
                    ELSE 0
                END
            ),
             0
        ) AS volume_sales_return
    """

VOLUME_ZERO = f"""
        COALESCE(
            SUM(
                CASE
                    WHEN sdh.document_type IN ({SALES_DOC_TYPES})
                    THEN {SALES_VOLUME}
                    ELSE 0
                END
            ),
            0
        ) = 0 THEN 0
    """

TOTAL_RETURN_VOLUME = f"""
            COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type IN ({RETURN_DOC_TYPES})
                        THEN {SALES_VOLUME}
                        ELSE 0
                    END
                ),
                0
            )
        """

TOTAL_SALES_VOLUME = f"""
        COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type IN ({SALES_DOC_TYPES})
                        THEN {SALES_VOLUME}
                        ELSE 0
                    END
                ),
                0
            )
        """

VOLUME_RETURN_PERCENT = f"""
            ROUND(
                (
                    CASE
                        WHEN 
                            {VOLUME_ZERO}
                        ELSE
                            (   
                                {TOTAL_RETURN_VOLUME}
                                /
                                {TOTAL_SALES_VOLUME}
                            ) * 100
                    END
                )::numeric,
                2
            ) AS volume_return_percent
            """

VOLUME_NET_SALES = f"""
            (
                {TOTAL_SALES_VOLUME}
                -
                {TOTAL_RETURN_VOLUME}
            ) AS volume_net_sales
            """
#-------------------------------------------------------------------------------
PERIOD_MAP = {
    "day": {
        "select":   "TO_CHAR(sdh.invoice_date, 'YYYY-MM-DD') AS period",
        "group_by": "TO_CHAR(sdh.invoice_date, 'YYYY-MM-DD')",
        "order_by": "TO_CHAR(sdh.invoice_date, 'YYYY-MM-DD')",
    },
    "month": {
        "select":   "TO_CHAR(sdh.invoice_date, 'YYYY-MM') AS period",
        "group_by": "TO_CHAR(sdh.invoice_date, 'YYYY-MM')",
        "order_by": "TO_CHAR(sdh.invoice_date, 'YYYY-MM')",
    },
    "year": {
        "select":   "TO_CHAR(sdh.invoice_date, 'YYYY') AS period",
        "group_by": "TO_CHAR(sdh.invoice_date, 'YYYY')",
        "order_by": "TO_CHAR(sdh.invoice_date, 'YYYY')",
    },
}


PIVOT_PERIOD_START_MAP = {
    "day":   "sdh.invoice_date::date",
    "month": "date_trunc('month', sdh.invoice_date)::date",
    "year":  "date_trunc('year',  sdh.invoice_date)::date",
}


PIVOT_NET_AMOUNT = f"""
    (
        COALESCE(SUM(CASE WHEN sdh.document_type IN ({SALES_DOC_TYPES})  THEN {SALES_REVENUE} ELSE 0 END), 0)
      - COALESCE(SUM(CASE WHEN sdh.document_type IN ({RETURN_DOC_TYPES}) THEN {SALES_REVENUE} ELSE 0 END), 0)
    ) AS net_amount
"""

PIVOT_NET_QUANTITY = f"""
    (
        COALESCE(SUM(CASE WHEN sdh.document_type IN ({SALES_DOC_TYPES})  THEN {SALES_VOLUME} ELSE 0 END), 0)
      - COALESCE(SUM(CASE WHEN sdh.document_type IN ({RETURN_DOC_TYPES}) THEN {SALES_VOLUME} ELSE 0 END), 0)
    ) AS net_quantity
"""
 