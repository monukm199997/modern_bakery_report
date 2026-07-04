from typing import Dict, List

from fastapi import HTTPException

from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)


SALES_DOC_SQL = "'ZVCS','YDO','YDI','YSCR','ZSCS','ZFCD','YFCD','YSDR'"
RETURN_DOC_SQL = "'YRSC','ZRVS'"


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
            i.barcode AS barcode,
            u.name AS uom_name,
            iu.upc AS upc
        """,
        "group_by": "i.code, i.name, u.name, iu.upc, i.barcode",
        "joins": [
            "LEFT JOIN uom u ON u.id = sdd.uom",
            """
            LEFT JOIN item_uoms iu
                ON iu.item_id = sdd.item_id
                AND iu.uom_id = sdd.uom
                AND iu.status = '1'
            """,
        ],
    },
    "salesman": {
        "select": "sm.osa_code AS salesman_code, sm.name AS salesman, sup.name AS supervisor",
        "group_by": "sm.osa_code, sm.name,sup.name",
    },
    "route": {
        "select": "rt.route_code AS route_code, rt.route_name AS route, sm.osa_code AS salesman_code, sm.name AS salesman",
        "group_by": "rt.route_code, rt.route_name, sm.osa_code, sm.name",
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
        "select": "oc.outlet_channel_code AS channel_code, oc.outlet_channel AS channel",
        "group_by": "oc.outlet_channel_code, oc.outlet_channel",
    },
}


BASE_FROM_SQL = """
FROM sales_documents_header sdh
JOIN sales_documents_detail sdd
    ON sdd.header_id = sdh.id
LEFT JOIN salesman sm
    ON sm.id = sdh.salesman_id
LEFT JOIN users sup
    ON sup.id = sm.superwiser_id
    AND sup.role = 108
LEFT JOIN items i
    ON i.id = sdd.item_id
LEFT JOIN agent_customers ac
    ON ac.id = sdh.customer_id
LEFT JOIN outlet_channel oc
    ON oc.id = ac.outlet_channel_id
LEFT JOIN tbl_route rt
    ON rt.id = sdh.route_id
"""


def sales_amount_expr(date_condition: str) -> str:
    return f"""
    COALESCE(
        SUM(
            CASE
                WHEN {date_condition}
                AND TRIM(UPPER(sdh.document_type)) IN ({SALES_DOC_SQL})
                THEN sdd.net_total
                ELSE 0
            END
        ),
        0
    )
    """


def return_amount_expr(date_condition: str) -> str:
    return f"""
    COALESCE(
        SUM(
            CASE
                WHEN {date_condition}
                AND TRIM(UPPER(sdh.document_type)) IN ({RETURN_DOC_SQL})
                THEN sdd.net_total
                ELSE 0
            END
        ),
        0
    )
    """


def net_amount_expr(date_condition: str) -> str:
    return f"(({sales_amount_expr(date_condition)}) - ({return_amount_expr(date_condition)}))"


def sales_quantity_expr(date_condition: str) -> str:
    return f"""
    COALESCE(
        SUM(
            CASE
                WHEN {date_condition}
                AND TRIM(UPPER(sdh.document_type)) IN ({SALES_DOC_SQL})
                THEN sdd.quantity
                ELSE 0
            END
        ),
        0
    )
    """


def return_quantity_expr(date_condition: str) -> str:
    return f"""
    COALESCE(
        SUM(
            CASE
                WHEN {date_condition}
                AND TRIM(UPPER(sdh.document_type)) IN ({RETURN_DOC_SQL})
                THEN sdd.quantity
                ELSE 0
            END
        ),
        0
    )
    """


def net_quantity_expr(date_condition: str) -> str:
    return f"(({sales_quantity_expr(date_condition)}) - ({return_quantity_expr(date_condition)}))"


def percent_change_expr(current_expr: str, previous_expr: str) -> str:
    return f"""
    ROUND(
        (
            CASE
                WHEN COALESCE(({previous_expr}), 0) = 0 THEN
                    CASE WHEN COALESCE(({current_expr}), 0) > 0 THEN 100 ELSE 0 END
                ELSE
                    ((COALESCE(({current_expr}), 0) - COALESCE(({previous_expr}), 0))
                    / COALESCE(({previous_expr}), 0)) * 100
            END
        )::numeric,
        2
    )
    """


def build_filters(payload: SalesComparisonRequest):
    where: List[str] = [
        "sdh.deleted_at IS NULL",
        "sdd.deleted_at IS NULL",
        """
        (
            sdh.invoice_date::date BETWEEN :current_from_date AND :current_to_date
            OR sdh.invoice_date::date BETWEEN :previous_from_date AND :previous_to_date
        )
        """,
    ]

    params: Dict = {
        "current_from_date": payload.current_from_date,
        "current_to_date": payload.current_to_date,
        "previous_from_date": payload.previous_from_date,
        "previous_to_date": payload.previous_to_date,
    }

    if payload.company_ids:
        where.append("sm.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        where.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where.append("sdh.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids

    if payload.salesman_ids:
        where.append("sdh.salesman_id = ANY(:salesman_ids)")
        params["salesman_ids"] = payload.salesman_ids
    
    if payload.super_wiser_ids:
        where.append("sup.id = ANY(:super_wiser_ids)")
        params["super_wiser_ids"] = payload.super_wiser_ids

    if payload.customer_groups_ids:
        where.append("ac.cust_group = ANY(:customer_groups_ids)")
        params["customer_groups_ids"] = payload.customer_groups_ids

    if payload.customer_groups_1_ids:
        where.append("ac.customergroup = ANY(CAST(:customer_groups_1_ids AS text[]))")
        params["customer_groups_1_ids"] = payload.customer_groups_1_ids

    if payload.customer_groups_2_ids:
        where.append("ac.customergroup2 = ANY(CAST(:customer_groups_2_ids AS text[]))")
        params["customer_groups_2_ids"] = payload.customer_groups_2_ids

    return where, params


def build_drill_down_parts(drill_down_fields):
    selected_fields = [f.lower() for f in (drill_down_fields or [])]

    select_cols: List[str] = []
    group_cols: List[str] = []
    extra_joins: List[str] = []

    for field in selected_fields:
        if field not in DRILL_DOWN_MAP:
            raise HTTPException(status_code=400, detail=f"Invalid drill_down_field: {field}")

        cfg = DRILL_DOWN_MAP[field]
        select_cols.append(cfg["select"])
        group_cols.append(cfg["group_by"])
        extra_joins.extend(cfg.get("joins", []))

    return select_cols, group_cols, list(dict.fromkeys(extra_joins))


def build_comparison_metric_columns(search_type: str):
    current_cond = "sdh.invoice_date::date BETWEEN :current_from_date AND :current_to_date"
    previous_cond = "sdh.invoice_date::date BETWEEN :previous_from_date AND :previous_to_date"

    current_revenue = net_amount_expr(current_cond)
    previous_revenue = net_amount_expr(previous_cond)
    current_volume = net_quantity_expr(current_cond)
    previous_volume = net_quantity_expr(previous_cond)

    metric_cols: List[str] = []

    if search_type in ["amount", "both"]:
        metric_cols.extend([
            f"({current_revenue}) AS current_revenue",
            f"({previous_revenue}) AS previous_revenue",
            f"(({current_revenue}) - ({previous_revenue})) AS revenue_difference",
            f"{percent_change_expr(current_revenue, previous_revenue)} AS revenue_growth_percent",
        ])

    if search_type in ["quantity", "both"]:
        metric_cols.extend([
            f"({current_volume}) AS current_volume",
            f"({previous_volume}) AS previous_volume",
            f"(({current_volume}) - ({previous_volume})) AS volume_difference",
            f"{percent_change_expr(current_volume, previous_volume)} AS volume_growth_percent",
        ])

    if search_type not in ["amount", "quantity", "both"]:
        raise HTTPException(status_code=400, detail="search_type must be amount, quantity, or both")

    return metric_cols


def prepare_comparison_context(payload: SalesComparisonRequest) -> Dict:
    select_cols, group_cols, extra_joins = build_drill_down_parts(payload.drill_down_fields)
    metric_cols = build_comparison_metric_columns(payload.search_type)
    where, params = build_filters(payload)

    return {
        "select_sql": ",\n".join(select_cols + metric_cols),
        "from_sql": BASE_FROM_SQL + "\n" + "\n".join(extra_joins),
        "where_sql": " AND ".join(where),
        "group_by_sql": "GROUP BY " + ", ".join(group_cols) if group_cols else "",
        "params": params,
    }


def compute_comparison(current_value, previous_value):
    current_value = float(current_value or 0)
    previous_value = float(previous_value or 0)
    difference = current_value - previous_value

    if previous_value == 0:
        growth_percent = 100 if current_value > 0 else 0
    else:
        growth_percent = round((difference / previous_value) * 100, 2)

    return {
        "current": current_value,
        "previous": previous_value,
        "difference": difference,
        "growth_percent": growth_percent,
    }


def pretty_header(name: str) -> str:
    replacements = {
        "current_revenue": "Current Revenue",
        "previous_revenue": "Previous Revenue",
        "revenue_difference": "Revenue Difference",
        "revenue_growth_percent": "Revenue Growth %",
        "current_volume": "Current Volume",
        "previous_volume": "Previous Volume",
        "volume_difference": "Volume Difference",
        "volume_growth_percent": "Volume Growth %",
    }
    return replacements.get(name, name.replace("_", " ").title())
