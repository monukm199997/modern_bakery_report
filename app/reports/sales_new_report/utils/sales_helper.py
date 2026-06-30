from fastapi import HTTPException
from app.reports.sales_new_report.schemas.sales_schema import SalesReportRequest
from app.utils.helper import validate_mandatory

DRILL_DOWN_MAP = {
    "customer": {
        "sales_select": """
            ac.osa_code AS customer_code,
            ac.name AS customer
        """,
        "return_select": """
            ac.osa_code AS customer_code,
            ac.name AS customer
        """,
        "final_select": """
            COALESCE(s.customer_code, r.customer_code) AS customer_code,
            COALESCE(s.customer, r.customer) AS customer
        """,
        "sales_group_by": """
            ac.osa_code,
            ac.name
        """,
        "return_group_by": """
            ac.osa_code,
            ac.name
        """,
        "join_on": """
            s.customer_code = r.customer_code
            AND s.customer = r.customer
        """
    },
    "item": {
        "sales_select": """
            i.code AS item_code,
            i.name AS item
        """,
        "return_select": """
            i.code AS item_code,
            i.name AS item
        """,
        "final_select": """
            COALESCE(s.item_code, r.item_code) AS item_code,
            COALESCE(s.item, r.item) AS item
        """,
        "sales_group_by": """
            i.code,
            i.name
        """,
        "return_group_by": """
            i.code,
            i.name
        """,
        "join_on": """
            s.item_code = r.item_code
            AND s.item = r.item
        """,
    },
    "salesman": {
        "sales_select": """
            sm.osa_code AS salesman_code,
            sm.name AS salesman
        """,
        "return_select": """
            sm.osa_code AS salesman_code,
            sm.name AS salesman
        """,
        "final_select": """
            COALESCE(s.salesman_code, r.salesman_code) AS salesman_code,
            COALESCE(s.salesman, r.salesman) AS salesman
        """,
        "sales_group_by": """
            sm.osa_code,
            sm.name
        """,
        "return_group_by": """
            sm.osa_code,
            sm.name
        """,
        "join_on": """
        s.salesman_code = r.salesman_code
        AND s.salesman = r.salesman
        """,
    },
    "route": {
        "sales_select": """
            rt.route_code AS route_code,
            rt.route_name AS route
        """,
        "return_select": """
            rt.route_code AS route_code,
            rt.route_name AS route
        """,
        "final_select": """
            COALESCE(s.route_code, r.route_code) AS route_code,
            COALESCE(s.route, r.route) AS route
        """,
        "sales_group_by": """
            rt.route_code,
            rt.route_name
        """,
        "return_group_by": """
            rt.route_code,
            rt.route_name
        """,
        "join_on": """
            s.route_code = r.route_code
            AND s.route = r.route
        """,
    },
    "supervisor": {
        "sales_select": "sw.name AS supervisor",
        "return_select": "sw.name AS supervisor",
        "final_select": "COALESCE(s.supervisor, r.supervisor) AS supervisor",
        "sales_group_by": "sw.name",
        "return_group_by": "sw.name",
        "join_on": "s.supervisor = r.supervisor",
    },
    "customer_group": {
        "sales_select": "ac.cust_group AS customer_group",
        "return_select": "ac.cust_group AS customer_group",
        "final_select": "COALESCE(s.customer_group, r.customer_group) AS customer_group",
        "sales_group_by": "ac.cust_group",
        "return_group_by": "ac.cust_group",
        "join_on": "s.customer_group = r.customer_group",
    },
    "channel": {
        "sales_select": """
            oc.outlet_channel_code AS channel_code,
            oc.outlet_channel AS channel
        """,
        "return_select": """
            oc.outlet_channel_code AS channel_code,
            oc.outlet_channel AS channel
        """,
        "final_select": """
            COALESCE(s.channel_code, r.channel_channel_code) AS channel_code,
            COALESCE(s.channel, r.channel) AS channel
        """,
        "sales_group_by": """
            oc.channel_name,
            oc.outlet_channel
        """,
        "return_group_by": """
        oc.channel_name,
        oc.outlet_channel
        """,
        "join_on": """
        s.channel_code = r.channel_code
         AND s.channel = r.channel
        """,
    },
}


def build_common_filters(payload: SalesReportRequest):
    sales_where = []
    return_where = []
    params = {}

    sales_where.append("ih.invoice_date::date BETWEEN :from_date AND :to_date")
    return_where.append("rh.created_at::date BETWEEN :from_date AND :to_date")

    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        sales_where.append("sm.company_id = ANY(:company_ids)")
        return_where.append("sm.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        sales_where.append("rt.region_id = ANY(:region_ids)")
        return_where.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        sales_where.append("ih.route_id = ANY(:route_ids)")
        return_where.append("rh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.salesman_ids:
        sales_where.append("ih.salesman_id = ANY(:salesman_ids)")
        return_where.append("rh.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids

    if payload.item_category_ids:
        sales_where.append("i.category_id = ANY(:item_category_ids)")
        return_where.append("i.category_id = ANY(:item_category_ids)")
        params["item_category_ids"] = payload.item_category_ids

    if payload.item_ids:
        sales_where.append("id.item_id = ANY(:item_ids)")
        return_where.append("rd.item_id = ANY(:item_ids)")
        params["item_ids"] = payload.item_ids

    if payload.customer_channel_ids:
        sales_where.append("ac.outlet_channel_id = ANY(:customer_channel_ids)")
        return_where.append("ac.outlet_channel_id = ANY(:customer_channel_ids)")
        params["customer_channel_ids"] = payload.customer_channel_ids

    if payload.customer_ids:
        sales_where.append("ih.customer_id = ANY(:customer_ids)")
        return_where.append("rh.customer_id = ANY(:customer_ids)")
        params["customer_ids"] = payload.customer_ids

    if payload.customer_groups_ids:
        sales_where.append("ac.cust_group = ANY(:customer_groups_ids)")
        return_where.append("ac.cust_group = ANY(:customer_groups_ids)")
        params["customer_groups_ids"] = payload.customer_groups_ids

    if payload.super_wiser_ids:
        sales_where.append("sm.superwiser_id = ANY(:super_wiser_ids)")
        return_where.append("sm.superwiser_id = ANY(:super_wiser_ids)")
        params["super_wiser_ids"] = payload.super_wiser_ids

    return sales_where, return_where, params


def prepare_sales_report_context(payload: SalesReportRequest):
    validate_mandatory(payload)

    selected_fields = payload.drill_down_fields or []

    sales_select_cols = []
    return_select_cols = []
    final_select_cols = []
    sales_group_cols = []
    return_group_cols = []
    join_conditions = []

    for field in selected_fields:
        field = field.lower()

        if field not in DRILL_DOWN_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid drill_down_field: {field}"
            )

        config = DRILL_DOWN_MAP[field]
        sales_select_cols.append(config["sales_select"])
        return_select_cols.append(config["return_select"])
        final_select_cols.append(config["final_select"])
        sales_group_cols.append(config["sales_group_by"])
        return_group_cols.append(config["return_group_by"])
        join_conditions.append(config["join_on"])

    search_type = payload.search_type.lower()

    metric_cols = []

    if search_type in ["amount", "both"]:
        metric_cols.extend([
            "COALESCE(s.gross_sales_amount, 0) AS revenue_gross_sales",
            "COALESCE(r.return_amount, 0) AS revenue_sales_return",
            """
            COALESCE(
                ROUND(
                    (
                        COALESCE(r.return_amount, 0)
                        / NULLIF(COALESCE(s.gross_sales_amount, 0), 0)
                        * 100
                    )::numeric,
                    2
                ),
                0
            ) AS revenue_return_percent
            """,
            """
            (
                COALESCE(s.gross_sales_amount, 0)
                - COALESCE(r.return_amount, 0)
            ) AS revenue_net_sales
            """,
        ])

    if search_type in ["quantity", "both"]:
        metric_cols.extend([
            "COALESCE(s.gross_sales_qty, 0) AS volume_gross_sales",
            "COALESCE(r.return_qty, 0) AS volume_sales_return",
            """
           COALESCE(
                ROUND(
                    (
                        COALESCE(r.return_qty, 0)
                        / NULLIF(COALESCE(s.gross_sales_qty, 0), 0)
                        * 100
                    )::numeric,
                    2
                ),
                0
            ) AS volume_return_percent
            """,
            """
            (
                COALESCE(s.gross_sales_qty, 0)
                - COALESCE(r.return_qty, 0)
            ) AS volume_net_sales
            """,
        ])

    if search_type not in ["amount", "quantity", "both"]:
        raise HTTPException(
            status_code=400,
            detail="search_type must be amount, quantity, or both"
        )

    sales_where, return_where, params = build_common_filters(payload)
    return {
        "sales_select_sql": (
            ",\n".join(sales_select_cols) + ","
            if sales_select_cols else ""
        ),
        "return_select_sql": (
            ",\n".join(return_select_cols) + ","
            if return_select_cols else ""
        ),
        "final_select_sql": (
            ",\n".join(final_select_cols + metric_cols)
        ),
        "sales_group_by_sql": (
            "GROUP BY " + ", ".join(sales_group_cols)
            if sales_group_cols else ""
        ),
        "return_group_by_sql": (
            "GROUP BY " + ", ".join(return_group_cols)
            if return_group_cols else ""
        ),
        "join_on_sql": (
            " AND ".join(join_conditions)
            if join_conditions else "1 = 1"
        ),
        "sales_where_sql": " AND ".join(sales_where),
        "return_where_sql": " AND ".join(return_where),
        "params": params,
    }


def sales_quantity():
    return """
    ROUND(
        SUM(
            CASE
                WHEN iu.upc IS NULL THEN 0
                ELSE id.quantity::numeric * iu.upc::numeric
            END
        ),
        6
    )
    """

def return_quantity():
    return """
    ROUND(
        SUM(
            CASE
                WHEN iu.upc IS NULL THEN 0
                ELSE rd.item_quantity::numeric * iu.upc::numeric
            END
        ),
        6
    )
    """