SALES_DOCUMENT_TYPES = ["ZVCS", "YDO", "YDI", "YSCR", "ZSCS", "ZFCD", "YFCD"]

RETURN_DOCUMENT_TYPES = ["YRSC", "ZRVS"]


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
        i.name AS item
        """,
        "group_by": "i.code, i.name",
    },
    "salesman": {
        "select": """
        sm.osa_code AS salesman_code,
        sm.name AS salesman
        """,
        "group_by": "sm.osa_code, sm.name",
    },
    "route": {
        "select": """
        rt.route_code,
        rt.route_name AS route
        """,
        "group_by": "rt.route_code, rt.route_name",
    },
    "supervisor": {
        "select": "sup.name AS supervisor",
        "group_by": "sup.name",
    },
    "customer_group": {
        "select": "ac.cust_group AS customer_group",
        "group_by": "ac.cust_group",
    },
    "channel": {
        "select": """
        oc.outlet_channel_code AS channel_code,
        oc.outlet_channel AS channel
        """,
        "group_by": "oc.outlet_channel_code, oc.outlet_channel",
    },
}

SALES_QUANTITY = """
        sdd.quantity::numeric * iu.upc::numeric
    """

REVENUE_GROSS_SALES = """COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type = ANY(:sales_document_types)
                        THEN sdd.net_total
                        ELSE 0
                    END
                ),
                0
            ) AS revenue_gross_sales
        """

REVENUE_GROSS_RETURN = """COALESCE(
                SUM(
                    CASE
                        WHEN sdh.document_type = ANY(:return_document_types)
                        THEN sdd.net_total
                        ELSE 0
                    END
                ),
                0
            ) AS revenue_sales_return
            """


REVENUE_ZERO = """
            COALESCE(
                    SUM(
                        CASE
                            WHEN sdh.document_type = ANY(:sales_document_types)
                            THEN sdd.net_total
                            ELSE 0
                        END
                    ),
                    0   
                ) = 0 THEN 0
            """

TOTAL_RETURN_REVENUE = """
            COALESCE(
                    SUM(
                        CASE
                            WHEN sdh.document_type = ANY(:return_document_types)
                            THEN sdd.net_total
                            ELSE 0
                        END
                    ),
                    0
                )
            """

TOTAL_SALES_REVENUE = """
                 COALESCE(
                        SUM(
                            CASE
                                WHEN sdh.document_type = ANY(:sales_document_types)
                                THEN sdd.net_total
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
                        WHEN sdh.document_type = ANY(:sales_document_types)
                        THEN {SALES_QUANTITY}
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
                    WHEN sdh.document_type = ANY(:return_document_types)
                    THEN {SALES_QUANTITY}
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
                    WHEN sdh.document_type = ANY(:sales_document_types)
                    THEN {SALES_QUANTITY}
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
                        WHEN sdh.document_type = ANY(:return_document_types)
                        THEN {SALES_QUANTITY}
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
                        WHEN sdh.document_type = ANY(:sales_document_types)
                        THEN {SALES_QUANTITY}
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
