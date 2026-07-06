from datetime import date
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.sales_new_report.schemas.sales_schema import SalesPivotExportRequest
from app.reports.sales_new_report.utils.sales_helper import prepare_sales_pivot_context

router = APIRouter(tags=["Sales New Report"], dependencies=[Depends(get_current_user)])

HEADER_COLOR = "903442"
WHITE = "FFFFFF"
RED = "FF0000"

def get_sales_pivot_rows(payload: SalesPivotExportRequest, db: Session):
    ctx = prepare_sales_pivot_context(payload)

    query = f"""
        SELECT
            {ctx["select_sql"]}
        FROM sales_documents_header sdh
        JOIN sales_documents_detail sdd ON sdd.header_id = sdh.id
        LEFT JOIN salesman sm ON sm.id = sdh.salesman_id
        LEFT JOIN users sup ON sup.id = sm.superwiser_id AND sup.role = 108
        LEFT JOIN items i ON i.id = sdd.item_id
        LEFT JOIN agent_customers ac ON ac.id = sdh.customer_id
        LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id
        LEFT JOIN tbl_route rt ON rt.id = sdh.route_id
        {ctx["extra_join_sql"]}
        WHERE {ctx["where_sql"]}
        {ctx["group_by_sql"]}
        {ctx["order_by_sql"]}
    """
    rows = db.execute(text(query), ctx["params"]).mappings().all()
    return [dict(row) for row in rows]


def _parse_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def _period_label(period_start: date, period: str) -> str:
    if period == "day":
        return period_start.strftime("%Y-%m-%d")

    if period == "month":
        return period_start.strftime("%b %Y")

    if period == "year":
        return period_start.strftime("%Y")

    return str(period_start)


def build_sales_pivot_excel(rows, period, search_type):
    wb = Workbook()

    border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right", vertical="center")
    header_fill = PatternFill(fill_type="solid", start_color=HEADER_COLOR, end_color=HEADER_COLOR)
    header_font = Font(bold=True, color=WHITE)
    total_font = Font(bold=True, color=WHITE)

    def finish():
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=Sales_Report.xlsx"},
        )

    AMOUNT = ("Amount", "net_amount", "#,##0.00")
    QUANTITY = ("Quantity", "net_quantity", "#,##0.000")
    if search_type == "amount":
        sheet_specs = [AMOUNT]
    elif search_type == "quantity":
        sheet_specs = [QUANTITY]
    else:  # both
        sheet_specs = [AMOUNT, QUANTITY]

    if not rows:
        ws = wb.active
        ws.title = sheet_specs[0][0]
        ws["A1"] = "No Data Found"
        return finish()

    reserved = ("period_start", "net_amount", "net_quantity")
    entity_cols = [k for k in rows[0].keys() if k not in reserved]

    periods = sorted({_parse_date(r["period_start"]) for r in rows if r["period_start"] is not None})
    period_labels = [_period_label(p, period) for p in periods]

    row_order = []
    row_meta = {}
    for r in rows:
        key = tuple(r[c] for c in entity_cols)
        if key not in row_meta:
            row_order.append(key)
            row_meta[key] = [r[c] for c in entity_cols]

    if entity_cols:
        leading_headers = list(entity_cols) 
    else:
        leading_headers = ["summary"]
        row_meta = {k: ["All"] for k in row_meta}
    n_lead = len(leading_headers)

    def write_sheet(ws, value_col, num_fmt):
        matrix = {key: {} for key in row_order}
        for r in rows:
            key = tuple(r[c] for c in entity_cols)
            p = _parse_date(r["period_start"])
            try:
                matrix[key][p] = float(r[value_col] or 0)
            except (TypeError, ValueError):
                matrix[key][p] = 0.0

        headers = leading_headers + period_labels + ["Total"]
        for col_index, label in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_index)
            cell.value = label
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = center
            cell.border = border

        col_totals = [0.0] * len(periods)
        grand_total = 0.0
        r_idx = 2
        for key in row_order:
            for c, value in enumerate(row_meta[key], start=1):
                cell = ws.cell(row=r_idx, column=c)
                cell.value = value
                cell.border = border

            row_total = 0.0
            for p_i, p in enumerate(periods):
                v = matrix[key].get(p, 0.0)
                cell = ws.cell(row=r_idx, column=n_lead + 1 + p_i)
                cell.value = v
                cell.alignment = right
                cell.border = border
                cell.number_format = num_fmt
                if v < 0:
                    cell.font = Font(color=RED)
                row_total += v
                col_totals[p_i] += v

            cell = ws.cell(row=r_idx, column=n_lead + 1 + len(periods))
            cell.value = row_total
            cell.alignment = right
            cell.border = border
            cell.number_format = num_fmt
            cell.font = Font(bold=True)
            grand_total += row_total
            r_idx += 1

        total_row = r_idx
        cell = ws.cell(row=total_row, column=1)
        cell.value = "Total"
        cell.fill = header_fill
        cell.font = total_font
        cell.alignment = center
        cell.border = border
        for c in range(2, n_lead + 1):
            cell = ws.cell(row=total_row, column=c)
            cell.fill = header_fill
            cell.border = border

        for p_i in range(len(periods)):
            cell = ws.cell(row=total_row, column=n_lead + 1 + p_i)
            cell.value = col_totals[p_i]
            cell.fill = header_fill
            cell.font = total_font
            cell.alignment = right
            cell.border = border
            cell.number_format = num_fmt

        cell = ws.cell(row=total_row, column=n_lead + 1 + len(periods))
        cell.value = grand_total
        cell.fill = header_fill
        cell.font = total_font
        cell.alignment = right
        cell.border = border
        cell.number_format = num_fmt

        for column in ws.columns:
            max_length = 0
            col_letter = get_column_letter(column[0].column)
            for cell in column:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max_length + 4
        ws.freeze_panes = "A2"

    for i, (title, value_col, num_fmt) in enumerate(sheet_specs):
        ws = wb.active if i == 0 else wb.create_sheet()
        ws.title = title
        write_sheet(ws, value_col, num_fmt)

    return finish()


@router.post("/sales-pivot-export")
def export_pivot_report(
    payload: SalesPivotExportRequest,
    db: Session = Depends(get_db),
):
    rows = get_sales_pivot_rows(payload, db)
    return build_sales_pivot_excel(
        rows,
        period=payload.period.lower(),
        search_type=payload.search_type.lower(),
    )