STOCK_BASE_SQL = """
    FROM salesmanitemstocks_header h
    LEFt JOIN salesmanitemstocks_details d ON d.header_id=h.id
"""


SALES_BASE_SQL = """
    FROM sales_documents_header ih
    LEFT JOIN sales_documents_detail id ON id.header_id=ih.id
"""



SALES_DOC_TYPES = "'ZVCS','YDO','YDI','YSCR','ZSCS','ZFCD','YFCD','YSDR'"

RETURN_DOC_TYPES = "'YRSC','ZRVS'"

SALES_VOLUME = """
    id.quantity
    """

SALES_REVENUE = """
    id.net_total
"""

TOTAL_RETURN_REVENUE = f"""
            COALESCE(
                    SUM(
                        CASE
                            WHEN ih.document_type IN ({RETURN_DOC_TYPES})
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
                                WHEN ih.document_type IN ({SALES_DOC_TYPES})
                                THEN {SALES_REVENUE}
                                ELSE 0
                            END
                        ),
                        0
                    )
                """

TOTAL_RETURN_VOLUME = f"""
            COALESCE(
                SUM(
                    CASE
                        WHEN ih.document_type IN ({RETURN_DOC_TYPES})
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
                        WHEN ih.document_type IN ({SALES_DOC_TYPES})
                        THEN {SALES_VOLUME}
                        ELSE 0
                    END
                ),
                0
            )
        """

REVENUE_NET_SALES = f"""
            (
               {TOTAL_SALES_REVENUE}
                -
               {TOTAL_RETURN_REVENUE}
            )
            """

VOLUME_NET_SALES = f"""
            (
                {TOTAL_SALES_VOLUME}
                -
                {TOTAL_RETURN_VOLUME}
            ) 
            """