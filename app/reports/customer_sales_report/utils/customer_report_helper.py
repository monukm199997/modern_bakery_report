from app.reports.customer_sales_report.schemas.schemas import CustomerSalesReportRequest
from app.utils.helper import validate_mandatory, choose_granularity, quantity_expr_sql
from sqlalchemy import text
from app.reports.customer_sales_report.utils.sql_query_helper import ITEM_QUERY


def build_query_parts(payload: CustomerSalesReportRequest):
    joins = []
    where_fragments = []
    params = {}

    where_fragments.append("ih.invoice_date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.display_quantity and payload.display_quantity.lower() == "without_free_good":
        where_fragments.append("id.item_total <> 0")

    if payload.company_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("LEFT JOIN tbl_route rt ON rt.id = ih.route_id")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("ih.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
        
    joins = list(dict.fromkeys(joins))
    return joins, where_fragments, params




def prepare_dashboard_context(payload: CustomerSalesReportRequest):
    validate_mandatory(payload)

    granularity, period_label_sql, order_by_sql = choose_granularity(
        payload.from_date, payload.to_date
    )

    joins, where_fragments, params = build_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    join_sql = "\n".join(joins)

    quantity = quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity"
        else "SUM(id.item_total)"
    )

    return {
        "granularity": granularity,
        "period_label_sql": period_label_sql,
        "order_by_sql": order_by_sql,
        "join_sql": join_sql,
        "where_sql": where_sql,
        "params": params,
        "value_expr": value_expr,
    }




def build_dynamic_detail_sql(db, where_sql, params, value_expr):
    item_query = f"""
        {ITEM_QUERY}
        WHERE {where_sql}
        ORDER BY 2, 1
        """
    item_rows = db.execute(text(item_query), params).fetchall()
    category_items = {}
    for item_name, category_name in item_rows:
        category_items.setdefault(category_name, []).append(item_name)

    item_columns = []
    category_columns = []
    total_parts = []

    for category_name, items in category_items.items():
        for item_name in items:
            item_sql = item_name.replace("'", "''")
            item_alias = item_name.replace('"', '""')
            item_columns.append(f"""
                    ROUND(
                        COALESCE(
                            SUM(
                                CASE
                                    WHEN i.name = '{item_sql}'
                                    THEN {value_expr}
                                    ELSE 0
                                END
                            ),
                            0
                        )::numeric,
                        2
                    ) AS "{item_alias}"
                """)
            
    for category_name in category_items.keys():
        category_sql = category_name.strip().replace("'", "''")
        category_alias = category_name.replace('"', '""')
        category_total_expr = f"""
            COALESCE(
                SUM(
                    CASE
                        WHEN COALESCE(TRIM(ic.category_name), 'Unknown') = '{category_sql}'
                        THEN {value_expr}
                        ELSE 0
                    END
                ),
                0
            )
        """
        category_columns.append(f"""
            ROUND(
                ({category_total_expr})::numeric,
                2
            ) AS "{category_alias}"
        """)
        total_parts.append(f"({category_total_expr})")
    dynamic_columns = item_columns + category_columns

    if total_parts:
        dynamic_columns.append(f"""
            ROUND(
                COALESCE(
                    SUM(
                        CASE
                            WHEN i.name IS NOT NULL
                            THEN {value_expr}
                            ELSE 0
                        END
                    ),
                    0
                )::numeric,
                2
            ) AS "Total"
        """)
    else:
        dynamic_columns.append('0 AS "Total"')
        
    return dynamic_columns