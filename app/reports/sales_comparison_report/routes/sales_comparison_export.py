import io
import xlsxwriter
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)
from app.reports.sales_comparison_report.utils.sales_comparison_helper import (
    get_periods,
    prepare_dashboard_context,
    compute_comparison,
    format_period_label
)

router = APIRouter(tags=["Sales Comparison Report"], dependencies = [Depends(get_current_user)])


@router.post("/sales-comparison-export")
def sales_comparison_export(
    payload: SalesComparisonRequest,
    db: Session = Depends(get_db),
):
    selected_date = payload.selected_date
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()

    current_from, current_to, prev_from, prev_to = get_periods(
        payload.report_by, selected_date
    )

    ctx = prepare_dashboard_context(
        payload, current_from, current_to, prev_from, prev_to
    )
    where_sql = ctx["where_sql"]
    params = ctx["params"]
    current_expr = ctx["current_expr"]
    prev_expr = ctx["prev_expr"]

    base_from = f"""
        {BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN tbl_route rt ON rt.id = ih.route_id
        WHERE {where_sql}
    """

    data_sql = f"""
        SELECT
            i.code AS item_code,
            i.name AS item,
            {current_expr} AS current_sales,
            {prev_expr}    AS previous_sales
        {base_from}
        GROUP BY i.code, i.name
        ORDER BY i.code, i.name
    """

    result = db.execute(text(data_sql), params)
    current_label = format_period_label(payload.report_by, current_from, current_to)
    prev_label    = format_period_label(payload.report_by, prev_from, prev_to)

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet("Sales Comparison")

    header_fmt = workbook.add_format(
        {"bold": True, "bg_color": "#993442", "font_color": "#FFFFFF", "align": "center"}
    )
    num_fmt = workbook.add_format({"num_format": "#,##0.00"})
    pct_fmt = workbook.add_format({"num_format": "0.00%"})
    neg_num_fmt = workbook.add_format({"num_format": "#,##0.00", "font_color": "#C00000"})
    neg_pct_fmt = workbook.add_format({"num_format": "0.00%", "font_color": "#C00000"})

    headers = [
        "Item Code",
        "Item",
        f"Current ({current_label})",
        f"Previous ({prev_label})",
        "Difference",
        "Growth %",
    ]
    for col, h in enumerate(headers):
        worksheet.write(0, col, h, header_fmt)

    row_no = 1
    for r in result:
        m = r._mapping
        comp = compute_comparison(m["current_sales"], m["previous_sales"])

        worksheet.write(row_no, 0, m["item_code"])
        worksheet.write(row_no, 1, m["item"])
        worksheet.write(row_no, 2, comp["current_sales"], num_fmt)
        worksheet.write(row_no, 3, comp["previous_sales"], num_fmt)

        diff_fmt = neg_num_fmt if comp["difference"] < 0 else num_fmt
        worksheet.write(row_no, 4, comp["difference"], diff_fmt)

        growth_fmt = neg_pct_fmt if comp["growth_percent"] < 0 else pct_fmt
        worksheet.write(row_no, 5, comp["growth_percent"] / 100, growth_fmt)
        row_no += 1

    last_row = max(row_no - 1, 0)
    worksheet.autofilter(0, 0, last_row, len(headers) - 1)
    worksheet.freeze_panes(1, 0)
    worksheet.set_column(0, 0, 14)
    worksheet.set_column(1, 1, 36)
    worksheet.set_column(2, 5, 22)

    workbook.close()
    output.seek(0)

    filename = f"sales_comparison_{current_from:%Y%m%d}_{current_to:%Y%m%d}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
