from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from io import BytesIO
import pandas as pd
from app.reports.sales_report.utils.sales_report_helper import prepare_dashboard_context, style_sheet
from app.common.helper import quantity_expr_sql
from app.core.database import get_db
from app.reports.sales_report.schemas.schemas import ExportRequest

router = APIRouter(tags=["Sales Report - Export"])

@router.post("/sales-report/export")
def export_sales_report(
    payload: ExportRequest,
    db: Session = Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)
    if payload.item_ids:
        group_col = "item_name"
    elif payload.salesman_ids:
        group_col = "name"
    elif payload.route_ids:
        group_col = "route_name"
    elif payload.region_ids:
        group_col = "region_name"
    else:
        group_col = "company_name"


    if payload.search_type.lower() == "quantity":
        value_sql = quantity_expr_sql()
        total_col = "Total Qty"
    else:
        value_sql = "SUM(id.item_total)"
        total_col = "Total Amt"

    join_sql = ctx["join_sql"]

    if "JOIN tbl_route rt" not in join_sql:
        join_sql = f"""
        JOIN tbl_route rt ON rt.id = ih.route_id
        {join_sql}
        """

    query = f"""
    SELECT
    comp.company_name,
    rg.region_name,
    rt.route_name,
    sm.name,
    it.code AS item_code,
    it.name AS item_name,
    cat.category_name AS material_category,
    {ctx["period_label_sql"]} AS period_label,
    {ctx["order_by_sql"]} AS period_sort,
    {value_sql} as value
    FROM invoice_headers ih
    JOIN invoice_details id ON id.header_id = ih.id
    JOIN items it ON it.id = id.item_id
    LEFT JOIN item_categories cat ON cat.id = it.category_id
    {join_sql}
    JOIN salesman sm ON sm.id = ih.salesman_id
    LEFT JOIN tbl_region rg ON rg.id = rt.region_id
    LEFT JOIN tbl_company comp ON comp.id = ih.company_id
    LEFT JOIN agent_customers ac ON ac.id = ih.customer_id
    LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
    WHERE {ctx["where_sql"]}
    GROUP BY
        comp.company_name,
        rg.region_name,
        rt.route_name,
        sm.name,
        it.code,
        it.name,
        cat.category_name,
        {ctx["order_by_sql"]},
        period_label
    ORDER BY
        {group_col},
        it.name,
        {ctx["order_by_sql"]}
    """

    result = db.execute(text(query), ctx["params"])
    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No data found")
    
    df = pd.DataFrame(rows, columns=result.keys())

    def make_item_pivot(dataframe: pd.DataFrame) -> pd.DataFrame:

        if dataframe.empty:
            return pd.DataFrame(columns=[
            "item_code",
            "item_name",
            "material_category",
            total_col
        ])

        dataframe = dataframe.copy()

        dataframe["item_code"] = dataframe["item_code"].astype(str)
        dataframe["item_name"] = dataframe["item_name"].astype(str)
        dataframe["material_category"] = dataframe["material_category"].fillna("")
        dataframe["period_label"] = dataframe["period_label"].astype(str)

        period_order = (
        dataframe[["period_label", "period_sort"]]
        .drop_duplicates()
        .sort_values("period_sort")
    )
        ordered_labels = period_order["period_label"].tolist()  
        pivot = pd.pivot_table(
            dataframe,
            index=[
                "item_code",
                "item_name",
                "material_category"
            ],
            columns="period_label",
            values="value",
            aggfunc="sum",
            fill_value=0
        )

        ordered_labels = [
        label for label in ordered_labels
        if label in pivot.columns
    ]
        if ordered_labels:
            pivot = pivot[ordered_labels]
        pivot.columns = [f"{str(col)}" for col in pivot.columns]

        pivot = pivot.reset_index()

        value_cols = [
        col for col in pivot.columns
        if col not in ["item_code", "item_name", "material_category"]
        ]

        pivot[total_col] = pivot[value_cols].sum(axis=1)


        category_totals = (
            pivot.groupby("material_category")[value_cols + [total_col]]
            .sum()
            .reset_index()
        )

        category_totals["item_code"] = ""
        category_totals["item_name"] = category_totals["material_category"].replace("", "Uncategorized")
        category_totals["material_category"] = ""

        category_totals = category_totals[
            ["item_code", "item_name", "material_category"] + value_cols + [total_col]
        ]

        grand_total = pivot[value_cols + [total_col]].sum().to_dict()
        grand_total.update({
            "item_code": "",
            "item_name": "Total",
            "material_category": ""
        })

        grand_total_df = pd.DataFrame([grand_total])

        final_df = pd.concat(
        [pivot, category_totals, grand_total_df],
        ignore_index=True
    )

        return final_df

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        summary_df = make_item_pivot(df)

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        style_sheet(writer.sheets["Summary"])

        used_sheet_names = {"Summary"}

        for group_name, gdf in df.groupby(group_col):

            if gdf.empty:
                continue

            safe_sheet_name = (
                str(group_name).replace("/", "-")
                if group_name else "Unknown"
            )

            safe_sheet_name = safe_sheet_name[:31]

            original_name = safe_sheet_name
            count = 1

            while safe_sheet_name in used_sheet_names:
                safe_sheet_name = (
                    f"{original_name[:27]}_{count}"
                )[:31]
                count += 1

            used_sheet_names.add(safe_sheet_name)

            pivot_df = make_item_pivot(gdf)

            pivot_df.to_excel(
                writer,
                sheet_name=safe_sheet_name,
                index=False
            )

            style_sheet(writer.sheets[safe_sheet_name])

    output.seek(0)

    filename = (
        f"sales_report_{payload.search_type.lower()}_"
        f"{payload.from_date}_to_{payload.to_date}.xlsx"
    )

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        }
    )