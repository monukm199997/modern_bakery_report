from fastapi import HTTPException
from app.reports.sales_new_report.schemas.sales_schema import SalesReportRequest
from app.utils.helper import validate_mandatory
from app.reports.sales_new_report.utils.sales_sql_query import (
    SALES_DOCUMENT_TYPES,
    RETURN_DOCUMENT_TYPES,
    DRILL_DOWN_MAP,
    REVENUE_GROSS_SALES,
    REVENUE_GROSS_RETURN,
    REVENUE_RETURN_PERCENT,
    REVENUE_NET_SALES,
    VOLUME_GROSS_SALES,
    VOLUME_GROSS_RETURN,
    VOLUME_RETURN_PERCENT,
    VOLUME_NET_SALES,
)


def build_sales_document_filters(payload: SalesReportRequest):
    where = []
    params = {}

    where.append("sdh.invoice_date BETWEEN :from_date AND :to_date")
    where.append("sdh.deleted_at IS NULL")
    where.append("sdd.deleted_at IS NULL")

    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

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

    if payload.item_category_ids:
        where.append("i.category_id = ANY(:item_category_ids)")
        params["item_category_ids"] = payload.item_category_ids

    if payload.item_ids:
        where.append("sdd.item_id = ANY(:item_ids)")
        params["item_ids"] = payload.item_ids

    if payload.customer_channel_ids:
        where.append("ac.outlet_channel_id = ANY(:customer_channel_ids)")
        params["customer_channel_ids"] = payload.customer_channel_ids

    if payload.customer_ids:
        where.append("sdh.customer_id = ANY(:customer_ids)")
        params["customer_ids"] = payload.customer_ids

    if payload.customer_groups_ids:
        where.append("ac.cust_group = ANY(:customer_groups_ids)")
        params["customer_groups_ids"] = payload.customer_groups_ids

    if payload.super_wiser_ids:
        where.append("sup.id = ANY(:super_wiser_ids)")
        params["super_wiser_ids"] = payload.super_wiser_ids

    return where, params


def prepare_sales_report_context(payload: SalesReportRequest):
    validate_mandatory(payload)

    selected_fields = payload.drill_down_fields or []

    select_cols = []
    group_cols = []

    for field in selected_fields:
        field = field.lower()

        if field not in DRILL_DOWN_MAP:
            raise HTTPException( status_code=400, detail=f"Invalid drill_down_field: {field}")

        config = DRILL_DOWN_MAP[field]

        select_cols.append(config["select"])
        group_cols.append(config["group_by"])

    search_type = payload.search_type.lower()

    metric_cols = []

    if search_type in ["amount", "both"]:
        metric_cols.extend(
            [
            REVENUE_GROSS_SALES,
            REVENUE_GROSS_RETURN,
            REVENUE_RETURN_PERCENT,
            REVENUE_NET_SALES,
            ]
        )

    if search_type in ["quantity", "both"]:
        metric_cols.extend(
            [
            VOLUME_GROSS_SALES,
            VOLUME_GROSS_RETURN,
            VOLUME_RETURN_PERCENT,
            VOLUME_NET_SALES,
            ]
        )

    if search_type not in ["amount", "quantity", "both"]:
        raise HTTPException(status_code=400, detail="search_type must be amount, quantity, or both")

    where_fragments, params = build_sales_document_filters(payload)

    params["sales_document_types"] = SALES_DOCUMENT_TYPES
    params["return_document_types"] = RETURN_DOCUMENT_TYPES

    return {
        "select_sql": ",\n".join(select_cols + metric_cols),
        "where_sql": " AND ".join(where_fragments),
        "group_by_sql": ("GROUP BY " + ", ".join(group_cols) if group_cols else ""),
        "params": params,
    }




