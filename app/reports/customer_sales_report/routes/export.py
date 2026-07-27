from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import StreamingResponse
from app.reports.customer_sales_report.schemas.schemas import (
    CustomerSalesReportExportRequest,
)
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.common.apply_payload_permissions import apply_payload_permissions
from app.utils.helper import validate_mandatory
from app.reports.customer_sales_report.utils.customer_report_helper import prepare_dashboard_context, build_dynamic_detail_sql
from app.reports.customer_sales_report.utils.sql_query_helper import SELECT,FROM_CLAUSE, GROUP_BY
import pandas as pd
import io

router = APIRouter(tags=["Customer Sales Report"], dependencies=[Depends(get_current_user)])
raw_value_expr = "id.quantity"

@router.post("/export")
def customer_sale_export(
    payload: CustomerSalesReportExportRequest, 
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, db, current_user)
    validate_mandatory(payload)
    if payload.view_type not in ("default", "detail"):
        raise HTTPException(400, "view_type must be default or detail")
    ctx = prepare_dashboard_context(payload)
    dynamic_columns = build_dynamic_detail_sql(
                    db=db,
                    where_sql= ctx['where_sql'],
                    params= ctx["params"],
                    value_expr= raw_value_expr
                )
    dynamic_columns = ','.join(dynamic_columns)

    if payload.view_type == "default":
        query = f"""
                {SELECT}
                {ctx['value_expr']} AS "Total"
                {FROM_CLAUSE}
                {ctx['join_sql']}
                LEFT JOIN tbl_region r ON r.id = rt.region_id
                WHERE {ctx['where_sql']}
                {GROUP_BY}
                ORDER BY "Total" DESC
                """
    else:
        query = f"""
                {SELECT}
                s.osa_code || ' - ' || s.name AS "Sales Team",
                {dynamic_columns}
                {FROM_CLAUSE}
                {ctx['join_sql']}
                LEFT JOIN tbl_region r ON r.id = rt.region_id
                LEFT JOIN items i ON i.id = id.item_id
                LEFT JOIN item_categories ic ON ic.id = i.category_id
                WHERE {ctx['where_sql']}
                {GROUP_BY},
                s.osa_code,
                s.name
            ORDER BY ac.name
            """ 
    df = pd.read_sql(text(query), db.bind, params=ctx["params"])

    if df.empty:
        if payload.view_type == "default":
            df = pd.DataFrame(columns=[
                "Customer",
                "Customer Channel",
                "Customer Category",
                "Contact Number",
                "Region",
                "Route",
                "Total"
            ])
        else:
            df = pd.DataFrame(columns=[
                "Customer",
                "Customer Channel",
                "Customer Category",
                "Contact Number",
                "Region",
                "Route",
                "Sales Team",
                "Total"
            ])
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Customer Sales")

        workbook = writer.book
        worksheet = writer.sheets["Customer Sales"]

        header_format = workbook.add_format({
            "bold": True,
            "font_color": "white",
            "bg_color": "#993442",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        for col_num, column_name in enumerate(df.columns):
            worksheet.write(0, col_num, column_name, header_format)

        for idx, col in enumerate(df.columns):
            if df.empty:
                max_len = len(str(col))
            else:
                max_len = max(
                    df[col].astype(str).map(len).max(),
                    len(str(col))
                )

            worksheet.set_column(idx, idx, min(max_len + 5, 50))

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=customer_sales_report.xlsx"}
    )