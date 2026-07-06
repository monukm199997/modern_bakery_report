import openpyxl
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from tempfile import NamedTemporaryFile
from fastapi.responses import FileResponse
from app.dependencies.auth import get_current_user
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from app.reports.item_loading_report.schemas.item_loading_schema import ItemLoadingRequest
from app.reports.item_loading_report.utils.item_loading_helper import prepare_dashboard_context

router = APIRouter(tags=["Item Loading Report"], dependencies=[Depends(get_current_user)])

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

@router.post("/item-loading-export")
def item_loading_export(payload: ItemLoadingRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)

    query = f"""
        WITH ordered_data AS (
            SELECT
                aoh.salesman_id,
                {ctx['order_value']} AS ordered_qty,
                MAX(aoh.comment) AS remarks_by_stores
            FROM agent_order_headers aoh
            LEFT JOIN agent_order_details aod
                ON aod.header_id = aoh.id
                AND aod.deleted_at IS NULL
            JOIN agent_customers ac
                ON ac.id = aoh.customer_id
                AND ac.is_driver = 1
            LEFT JOIN salesman s
                ON s.id = aoh.salesman_id
            LEFT JOIN tbl_route rt
                ON rt.id = aoh.route_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = aod.item_id
                AND iu.uom_id = aod.uom_id
            WHERE {ctx['order_where_sql']}
            GROUP BY aoh.salesman_id
        ),

        received_data AS (
            SELECT
                lh.salesman_id,
                {ctx['load_volue']} AS received_qty
            FROM tbl_load_header lh
            LEFT JOIN tbl_load_details ld
                ON ld.header_id = lh.id
                AND ld.deleted_at IS NULL
            LEFT JOIN salesman s2
                ON s2.id = lh.salesman_id
            LEFT JOIN tbl_route rt2
                ON rt2.id = lh.route_id
            LEFT JOIN item_uoms iu
                ON iu.item_id = ld.item_id
                AND iu.uom_id = ld.uom
            WHERE {ctx["receive_where_sql"]}
            GROUP BY lh.salesman_id
        )

        SELECT
            s.id AS salesman_id,
            s.osa_code AS salesman_code,
            s.name AS salesman_name,
            COALESCE(o.ordered_qty, 0) AS salesman_ordered_qty,
            COALESCE(r.received_qty, 0) AS received_qty,
            COALESCE(o.ordered_qty, 0) - COALESCE(r.received_qty, 0) AS diff,
            o.remarks_by_stores
        FROM ordered_data o
        LEFT JOIN received_data r
            ON r.salesman_id = o.salesman_id
        LEFT JOIN salesman s
            ON s.id = o.salesman_id
        ORDER BY
            s.osa_code,
            s.name;
    """

    rows = db.execute(text(query), ctx["params"]).mappings().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Item Loading Report"

    headers = [
        "Salesman Code",
        "Sales Team",
        "Ordered QTY",
        "Received Qty",
        "Diff",
        "Remarks by Stores",
    ]

    ws.append(headers)

    for cell in ws[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.border = BORDER
        cell.alignment = CENTER

    for row in rows:
        ws.append([
            row.salesman_code,
            row.salesman_name,
            row.salesman_ordered_qty,
            row.received_qty,
            row.diff,
            row.remarks_by_stores,
           
        ])

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = BORDER

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
        filename="Item_Loading_Report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )