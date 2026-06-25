from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from tempfile import NamedTemporaryFile
import openpyxl

from openpyxl.styles import PatternFill, Font, Border, Side, Alignment

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.visit_report.schemas.visit_schema import VisitPlanRequest
from app.reports.visit_report.utils.visit_helper import prepare_dashboard_context

router = APIRouter(tags=["Visit Report"], dependencies=[Depends(get_current_user)])

HEADER_FILL = PatternFill(
    start_color="993442",
    end_color="993442",
    fill_type="solid"
)

HEADER_FONT = Font(
    color="FFFFFF",
    bold=True
)

BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin")
)

CENTER = Alignment(horizontal="center", vertical="center")


@router.post("/visit-export")
def visit_export(
    payload: VisitPlanRequest,
    db: Session = Depends(get_db)
):
    ctx = prepare_dashboard_context(payload)

    query = f"""
        SELECT
            TO_CHAR(vp.visit_start_time, 'YYYY-MM-DD') AS date,
            ac.osa_code AS customer_code,
            ac.name AS customer_name,
            ac.contact_no AS customer_contact,
            rt.route_code AS route_code,
            rt.route_name AS route_name,
            s.osa_code AS salesman_code,
            s.name AS salesman_name,
            TO_CHAR(vp.visit_start_time, 'HH24:MI:SS') AS visit_start_time,
            TO_CHAR(vp.visit_end_time, 'HH24:MI:SS') AS visit_end_time,
            ac.latitude AS customer_latitude,
            ac.longitude AS customer_longitude,
            vp.latitude,
            vp.longitude,
            vp.shop_status,
            vp.remark AS reason
        FROM visit_plan vp
        LEFT JOIN agent_customers ac ON ac.id = vp.customer_id
        LEFT JOIN tbl_route rt ON rt.id = vp.route_id
        LEFT JOIN salesman s ON s.id = vp.salesman_id
        WHERE {ctx['where_sql']}
        ORDER BY date DESC
    """

    rows = db.execute(text(query), ctx["params"]).fetchall()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Visit Report"

    headers = [
        "Date",
        "Customer Code",
        "Customer Name",
        "Customer Contact",
        "Route Code",
        "Route",
        "Sales Team Code",
        "Sales Team",
        "Start Time",
        "End Time",
        "Customer Latitude",
        "Customer Longitude",
        "Visit Latitude",
        "Visit Longitude"
    ]

    ws.append(headers)

    # Header Styling
    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = CENTER

    # Data Rows
    for row in rows:
        ws.append([
            row.date,
            row.customer_code,
            row.customer_name,
            row.customer_contact,
            row.route_code,
            row.route_name,
            row.salesman_code,
            row.salesman_name,
            row.visit_start_time,
            row.visit_end_time,
            row.customer_latitude,
            row.customer_longitude,
            row.latitude,
            row.longitude
           
        ])

    # Apply Border
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = BORDER

    # Auto Width
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter

        for cell in column:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except Exception:
                pass

        ws.column_dimensions[column_letter].width = min(max_length + 3, 50)

    with NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        wb.save(tmp.name)
        file_path = tmp.name

    return FileResponse(
        path=file_path,
        filename="Visit_Report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )