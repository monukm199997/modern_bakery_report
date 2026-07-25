from io import BytesIO

import xlsxwriter
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.common.apply_payload_permissions import apply_payload_permissions
from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_comparison_report.schemas.sales_comparison_schema import (
    SalesComparisonRequest,
)
from app.reports.sales_comparison_report.utils.sales_comparison_helper import (
    prepare_comparison_context,
    pretty_header,
)


router = APIRouter(tags=["Sales Comparison Report"], dependencies=[Depends(get_current_user)])


@router.post("/export")
def export_sales_comparison(
    payload: SalesComparisonRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    payload = apply_payload_permissions(payload, db, current_user)
    ctx = prepare_comparison_context(payload)

    query = f"""
        SELECT
            {ctx["select_sql"]}
        {ctx["from_sql"]}
        WHERE {ctx["where_sql"]}
        {ctx["group_by_sql"]}
    """

    rows = [dict(row) for row in db.execute(text(query), ctx["params"]).mappings().all()]

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    worksheet = workbook.add_worksheet("Sales Comparison")

    header_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#903442",
        "border": 1,
        "align": "center",
        "valign": "vcenter",
    })
    cell_fmt = workbook.add_format({"border": 1})
    num_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
    neg_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00", "font_color": "red"})
    total_fmt = workbook.add_format({
        "bold": True,
        "font_color": "white",
        "bg_color": "#903442",
        "border": 1,
        "num_format": "#,##0.00",
    })

    if not rows:
        worksheet.write(0, 0, "No Data Found", header_fmt)
    else:
        headers = list(rows[0].keys())

        for col, header in enumerate(headers):
            worksheet.write(0, col, pretty_header(header), header_fmt)

        for row_idx, row in enumerate(rows, start=1):
            for col_idx, header in enumerate(headers):
                value = row.get(header)
                if isinstance(value, (int, float)):
                    worksheet.write(row_idx, col_idx, value, neg_fmt if value < 0 else num_fmt)
                else:
                    worksheet.write(row_idx, col_idx, value, cell_fmt)

        total_row = len(rows) + 1
        worksheet.write(total_row, 0, "Total", total_fmt)

        for col_idx, header in enumerate(headers[1:], start=1):
            values = [row.get(header) for row in rows]
            if all(isinstance(v, (int, float)) or v is None for v in values):
                total = sum(float(v or 0) for v in values)
                worksheet.write(total_row, col_idx, total, total_fmt)
            else:
                worksheet.write(total_row, col_idx, "", total_fmt)

        for col, header in enumerate(headers):
            max_len = max(len(pretty_header(header)), *(len(str(r.get(header, ""))) for r in rows))
            worksheet.set_column(col, col, min(max_len + 3, 45))

        worksheet.freeze_panes(1, 0)

    workbook.close()
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sales_comparison_report.xlsx"},
    )
