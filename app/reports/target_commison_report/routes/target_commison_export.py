import os
import tempfile
from calendar import monthrange
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from openpyxl import Workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.reports.target_commison_report.schemas.schemas import SalesAchievementSchema
from app.reports.target_commison_report.utils.target_commison_helper import (
    prepare_all_contexts,
)


router = APIRouter(tags=["Target Commission Report"], dependencies=[Depends(get_current_user)])

def fetch_sales_data(db: Session, ctx: dict, to_date: str):
    sql = f"""
        SELECT
            rg.region_name      AS region,
            rt.route_name       AS route_name,
            s.id                AS salesman_id,
            s.name              AS salesman_name,
            s.osa_code          AS osa_code,
            COALESCE(ROUND(
                SUM(CASE
                    WHEN DATE(ih.invoice_date) = :daily_date
                    THEN {ctx['quantity']}
                    ELSE 0
                END), 6
            ), 0) AS daily_sales,
            COALESCE(ROUND(SUM({ctx['quantity']}), 6), 0) AS cumulative_sales
        FROM invoice_headers ih
        LEFT JOIN invoice_details id ON id.header_id = ih.id
        LEFT JOIN salesman      s   ON s.id = ih.salesman_id
        LEFT JOIN item_uoms     iu  ON iu.item_id = id.item_id
                                   AND iu.uom_id  = id.uom
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY rg.region_name, rt.route_name, s.id, s.name, s.osa_code
        ORDER BY rg.region_name, s.name
    """
    params = {**ctx["params"], "daily_date": to_date}
    return db.execute(text(sql), params).mappings().all()


def fetch_returns_data(db: Session, ctx: dict, to_date: str):
    sql = f"""
        SELECT
            rg.region_name AS region,
            s.id           AS salesman_id,
            s.name         AS salesman_name,
            s.osa_code     AS osa_code,
            rt.route_name  AS route_name,
            COALESCE(ROUND(
                SUM(CASE
                    WHEN DATE(rh.created_at) = :daily_date
                    THEN {ctx['quantity']}
                    ELSE 0
                END), 6
            ), 0) AS daily_returns,
            COALESCE(ROUND(SUM({ctx['quantity']}), 6), 0) AS cumulative_returns
        FROM return_header rh
        LEFT JOIN return_details rd ON rd.header_id = rh.id
        LEFT JOIN salesman       s  ON s.id = rh.salesman_id
        LEFT JOIN item_uoms      iu ON iu.item_id = rd.item_id
                                   AND iu.uom_id  = rd.uom_id
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY rg.region_name, s.id, s.name, s.osa_code, rt.route_name
    """
    params = {**ctx["params"], "daily_date": to_date}
    return db.execute(text(sql), params).mappings().all()


def fetch_target_data(db: Session, ctx: dict):
    sql = f"""
        SELECT
            rg.region_name AS region,
            s.id           AS salesman_id,
            s.name         AS salesman_name,
            s.osa_code     AS osa_code,
            rt.route_name  AS route_name,
            COALESCE(SUM(tc.total_target_amount), 0) AS target
        FROM target_commison tc
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
        GROUP BY rg.region_name, s.id, s.name, s.osa_code, rt.route_name
    """
    return db.execute(text(sql), ctx["params"]).mappings().all()


def compute_region_rows(sales_data, return_data, target_data,
                        total_days: int, current_day: int):
    """
    Builds rows grouped by region. Uses the UNION of keys across the
    three datasets so that a salesman with only returns or only a
    target still appears in the report.
    """
    sales_map = {(r["region"], r["salesman_id"]): r for r in sales_data}
    return_map = {(r["region"], r["salesman_id"]): r for r in return_data}
    target_map = {(r["region"], r["salesman_id"]): r for r in target_data}

    all_keys = set(sales_map) | set(return_map) | set(target_map)

    # Salesman name + route_name may be missing in some sources; pick
    # the first non-null we can find for display.
    def pick(key, field):
        for m in (sales_map, return_map, target_map):
            row = m.get(key)
            if row and row.get(field):
                return row[field]
        return ""

    region_data = defaultdict(list)

    for key in all_keys:
        region, salesman_id = key
        sales_row = sales_map.get(key, {})
        ret_row = return_map.get(key, {})
        tgt_row = target_map.get(key, {})

        daily_sales = float(sales_row.get("daily_sales", 0) or 0)
        cumulative_sales = float(sales_row.get("cumulative_sales", 0) or 0)
        daily_returns = float(ret_row.get("daily_returns", 0) or 0)
        cumulative_returns = float(ret_row.get("cumulative_returns", 0) or 0)
        monthly_target = float(tgt_row.get("target", 0) or 0)

        daily_net = daily_sales - daily_returns
        cumulative_net = cumulative_sales - cumulative_returns

        # ---- Correct pro-rated targets (matches the printed report) ----
        daily_target = monthly_target / total_days if total_days else 0
        mtd_target = monthly_target * current_day / total_days if total_days else 0

        daily_ach = (daily_net / daily_target * 100) if daily_target else 0
        cumulative_ach = (cumulative_net / mtd_target * 100) if mtd_target else 0

        projected_sales = (
            (cumulative_net / current_day) * total_days if current_day else 0
        )
        projected_ach = (
            (projected_sales / monthly_target * 100) if monthly_target else 0
        )

        # Return % (visible in the printed report)
        daily_ret_pct = (daily_returns / daily_sales * 100) if daily_sales else 0
        mtd_ret_pct = (
            cumulative_returns / cumulative_sales * 100
            if cumulative_sales else 0
        )

        region_data[region].append({
            "route_name": pick(key, "route_name"),
            "osa_code": pick(key, "osa_code"),
            "salesman": pick(key, "salesman_name"),
            "daily_sales": daily_sales,
            "daily_returns": daily_returns,
            "daily_ret_pct": daily_ret_pct,
            "daily_net": daily_net,
            "daily_target": daily_target,
            "daily_ach": daily_ach,
            "cumulative_sales": cumulative_sales,
            "cumulative_returns": cumulative_returns,
            "mtd_ret_pct": mtd_ret_pct,
            "cumulative_net": cumulative_net,
            "mtd_target": mtd_target,
            "cumulative_ach": cumulative_ach,
            "projected_sales": projected_sales,
            "monthly_target": monthly_target,
            "projected_ach": projected_ach,
        })

    # Sort rows inside each region by salesman name for stable output
    for region in region_data:
        region_data[region].sort(key=lambda x: (x["salesman"] or "").lower())

    return region_data


# =====================================================================
# WORKBOOK BUILDER
# =====================================================================

YELLOW = PatternFill(start_color="D9B300", end_color="D9B300", fill_type="solid")
BLUE = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")
TOTAL = PatternFill(start_color="FFE699", end_color="FFE699", fill_type="solid")
THIN = Side(style="thin", color="000000")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
BOLD = Font(bold=True, size=10)
CENTER = Alignment(horizontal="center", vertical="center")

# Sub-header row (row 3) — matches the printed report column-for-column.
# 18 columns total:
#   A: Route
#   B: Code (salesman.osa_code)
#   C: Salesman
#   D-I: DAILY block       (Sales, Returns, Retn %, Net Sales, Target, Achv %)
#   J-O: CUMULATIVE block  (Sales, Returns, Retn %, Net Sales, Target, Achv %)
#   P-R: MONTHLY block     (Achievement Projected, Target, Achv %)
REGION_SUB_HEADERS = [
    "Route", "Code", "Salesman",
    "Sales", "Returns", "Retn %", "Net Sales", "Target", "Achv %",
    "Sales", "Returns", "Retn %", "Net Sales", "Target", "Achv %",
    "Achievement (Projected)", "Target", "Achv %",
]
TOTAL_COLS = len(REGION_SUB_HEADERS)  # 17

SUMMARY_SUB_HEADERS = [
    "Region",
    "Net Sales", "Target", "Achv %",     # DAILY
    "Net Sales", "Target", "Achv %",     # CUMULATIVE
    "Projected", "Target", "Achv %",     # MONTHLY
]


def _style_header(cell):
    cell.fill = YELLOW
    cell.font = BOLD
    cell.border = BORDER
    cell.alignment = CENTER


def _write_row(ws, row_idx, values, fill=None, bold=False):
    for col, value in enumerate(values, 1):
        cell = ws.cell(row_idx, col)
        # Skip cells that are part of a merge but not the top-left anchor
        if isinstance(cell, MergedCell):
            continue
        cell.value = value
        cell.border = BORDER
        cell.alignment = CENTER
        if fill:
            cell.fill = fill
        if bold:
            cell.font = BOLD
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            cell.number_format = "#,##0.00"


def _auto_width(ws):
    for col in ws.columns:
        max_len = 0
        try:
            column_letter = get_column_letter(col[0].column)
        except AttributeError:
            # Skip merged cells
            continue
        for cell in col:
            # Skip merged-anchor cells like the title (huge multi-line string)
            if isinstance(cell, MergedCell):
                continue
            try:
                if cell.value is not None:
                    # Cap each cell's contribution so a long title or
                    # region-total label doesn't blow out the column.
                    length = min(len(str(cell.value)), 25)
                    max_len = max(max_len, length)
            except Exception:
                pass
        ws.column_dimensions[column_letter].width = max_len + 3


def build_workbook(region_data, from_date: str, to_date: str):
    wb = Workbook()
    wb.remove(wb.active)

    # ------------------------------------------------------------
    # SUMMARY SHEET
    # ------------------------------------------------------------
    summary_ws = wb.create_sheet("Summary", 0)

    # Title
    summary_ws.merge_cells(start_row=1, start_column=1,
                           end_row=1, end_column=len(SUMMARY_SUB_HEADERS))
    summary_ws.cell(1, 1, (
        f"Modern Bakery LLC.\n"
        f"ESTIMATED SALES & ACHIEVEMENT "
        f"(From {from_date} To {to_date})"
    ))
    summary_ws.cell(1, 1).font = Font(bold=True, size=14)
    summary_ws.cell(1, 1).alignment = CENTER

    # Group headers (row 2)
    summary_ws.cell(2, 1, "")  # Region label sits empty above
    _style_header(summary_ws.cell(2, 1))
    # DAILY group: cols 2-4
    summary_ws.merge_cells(start_row=2, start_column=2, end_row=2, end_column=4)
    summary_ws.cell(2, 2, f"DAILY ({to_date})")
    _style_header(summary_ws.cell(2, 2))
    # CUMULATIVE group: cols 5-7
    summary_ws.merge_cells(start_row=2, start_column=5, end_row=2, end_column=7)
    summary_ws.cell(2, 5, f"CUMULATIVE ({from_date} – {to_date})")
    _style_header(summary_ws.cell(2, 5))
    # MONTHLY group: cols 8-10
    summary_ws.merge_cells(start_row=2, start_column=8, end_row=2, end_column=10)
    summary_ws.cell(2, 8, "ESTIMATED MONTHLY SALES")
    _style_header(summary_ws.cell(2, 8))

    # Sub-headers (row 3)
    for col, header in enumerate(SUMMARY_SUB_HEADERS, 1):
        _style_header(summary_ws.cell(3, col, header))

    summary_row = 4
    grand = {
        "daily_net": 0, "daily_target": 0,
        "mtd_net": 0, "mtd_target": 0,
        "projected": 0, "monthly_target": 0,
    }

    # ------------------------------------------------------------
    # REGION SHEETS
    # ------------------------------------------------------------
    for region, rows in region_data.items():
        ws = wb.create_sheet((region or "Unknown")[:30])

        # Title (row 1)
        ws.merge_cells(start_row=1, start_column=1,
                       end_row=1, end_column=TOTAL_COLS)
        ws.cell(1, 1, (
            f"Modern Bakery LLC.\n"
            f"ESTIMATED SALES & ACHIEVEMENT "
            f"(From {from_date} To {to_date})"
        ))
        ws.cell(1, 1).font = Font(bold=True, size=14)
        ws.cell(1, 1).alignment = CENTER
        ws.row_dimensions[1].height = 36

        # Group headers (row 2)
        # Cols A-C: blank header band (sits above Route + Code + Salesman)
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=3)
        _style_header(ws.cell(2, 1, ""))
        # DAILY (cols D-I = 4..9)
        ws.merge_cells(start_row=2, start_column=4, end_row=2, end_column=9)
        ws.cell(2, 4, f"DAILY ({to_date})")
        _style_header(ws.cell(2, 4))
        # CUMULATIVE (cols J-O = 10..15)
        ws.merge_cells(start_row=2, start_column=10, end_row=2, end_column=15)
        ws.cell(2, 10, f"CUMULATIVE ({from_date} – {to_date})")
        _style_header(ws.cell(2, 10))
        # ESTIMATED MONTHLY SALES (cols P-R = 16..18)
        ws.merge_cells(start_row=2, start_column=16, end_row=2, end_column=18)
        ws.cell(2, 16, "ESTIMATED MONTHLY SALES")
        _style_header(ws.cell(2, 16))

        # Sub-headers (row 3)
        for col, header in enumerate(REGION_SUB_HEADERS, 1):
            _style_header(ws.cell(3, col, header))

        # Freeze rows 1-3 so they stay visible while scrolling
        ws.freeze_panes = "A4"

        row_idx = 4
        tot = {
            "daily_sales": 0, "daily_returns": 0, "daily_net": 0,
            "daily_target": 0,
            "mtd_sales": 0, "mtd_returns": 0, "mtd_net": 0,
            "mtd_target": 0,
            "projected": 0, "monthly_target": 0,
        }

        for item in rows:
            # Order MUST match REGION_SUB_HEADERS
            _write_row(ws, row_idx, [
                item["route_name"],
                item["osa_code"],
                item["salesman"],
                # DAILY block
                item["daily_sales"],
                item["daily_returns"],
                round(item["daily_ret_pct"], 2),
                item["daily_net"],
                round(item["daily_target"], 2),
                round(item["daily_ach"], 2),
                # CUMULATIVE block
                item["cumulative_sales"],
                item["cumulative_returns"],
                round(item["mtd_ret_pct"], 2),
                item["cumulative_net"],
                round(item["mtd_target"], 2),
                round(item["cumulative_ach"], 2),
                # MONTHLY block
                round(item["projected_sales"], 2),
                item["monthly_target"],
                round(item["projected_ach"], 2),
            ])
            tot["daily_sales"] += item["daily_sales"]
            tot["daily_returns"] += item["daily_returns"]
            tot["daily_net"] += item["daily_net"]
            tot["daily_target"] += item["daily_target"]
            tot["mtd_sales"] += item["cumulative_sales"]
            tot["mtd_returns"] += item["cumulative_returns"]
            tot["mtd_net"] += item["cumulative_net"]
            tot["mtd_target"] += item["mtd_target"]
            tot["projected"] += item["projected_sales"]
            tot["monthly_target"] += item["monthly_target"]
            row_idx += 1

        # ----- Region salesman total -----
        daily_ret_pct = (
            tot["daily_returns"] / tot["daily_sales"] * 100
            if tot["daily_sales"] else 0
        )
        mtd_ret_pct = (
            tot["mtd_returns"] / tot["mtd_sales"] * 100
            if tot["mtd_sales"] else 0
        )
        daily_pct = (
            tot["daily_net"] / tot["daily_target"] * 100
            if tot["daily_target"] else 0
        )
        mtd_pct = (
            tot["mtd_net"] / tot["mtd_target"] * 100
            if tot["mtd_target"] else 0
        )
        month_pct = (
            tot["projected"] / tot["monthly_target"] * 100
            if tot["monthly_target"] else 0
        )

        _write_row(ws, row_idx, [
            f"{region} TOTAL", "", "",
            tot["daily_sales"],
            tot["daily_returns"],
            round(daily_ret_pct, 2),
            tot["daily_net"],
            round(tot["daily_target"], 2),
            round(daily_pct, 2),
            tot["mtd_sales"],
            tot["mtd_returns"],
            round(mtd_ret_pct, 2),
            tot["mtd_net"],
            round(tot["mtd_target"], 2),
            round(mtd_pct, 2),
            round(tot["projected"], 2),
            tot["monthly_target"],
            round(month_pct, 2),
        ], fill=BLUE, bold=True)
        ws.merge_cells(start_row=row_idx, start_column=1,
                       end_row=row_idx, end_column=3)

        # ----- Summary sheet row for this region -----
        _write_row(summary_ws, summary_row, [
            region,
            tot["daily_net"],
            round(tot["daily_target"], 2),
            round(daily_pct, 2),
            tot["mtd_net"],
            round(tot["mtd_target"], 2),
            round(mtd_pct, 2),
            round(tot["projected"], 2),
            tot["monthly_target"],
            round(month_pct, 2),
        ])
        summary_row += 1

        grand["daily_net"] += tot["daily_net"]
        grand["daily_target"] += tot["daily_target"]
        grand["mtd_net"] += tot["mtd_net"]
        grand["mtd_target"] += tot["mtd_target"]
        grand["projected"] += tot["projected"]
        grand["monthly_target"] += tot["monthly_target"]

        _auto_width(ws)

    # ------------------------------------------------------------
    # GRAND TOTAL on summary
    # ------------------------------------------------------------
    g_daily_pct = (
        grand["daily_net"] / grand["daily_target"] * 100
        if grand["daily_target"] else 0
    )
    g_mtd_pct = (
        grand["mtd_net"] / grand["mtd_target"] * 100
        if grand["mtd_target"] else 0
    )
    g_month_pct = (
        grand["projected"] / grand["monthly_target"] * 100
        if grand["monthly_target"] else 0
    )

    _write_row(summary_ws, summary_row, [
        "GRAND TOTAL",
        grand["daily_net"],
        round(grand["daily_target"], 2),
        round(g_daily_pct, 2),
        grand["mtd_net"],
        round(grand["mtd_target"], 2),
        round(g_mtd_pct, 2),
        round(grand["projected"], 2),
        grand["monthly_target"],
        round(g_month_pct, 2),
    ], fill=TOTAL, bold=True)

    _auto_width(summary_ws)
    return wb


# =====================================================================
# ROUTE
# =====================================================================

def _cleanup(path: str):
    try:
        os.remove(path)
    except OSError:
        pass


@router.post("/sales-achievement-export")
def sales_achievement_export(
    payload: SalesAchievementSchema,
    db: Session = Depends(get_db),
):
    from_dt = datetime.strptime(payload.from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(payload.to_date, "%Y-%m-%d")

    total_days = monthrange(from_dt.year, from_dt.month)[1]
    current_day = to_dt.day

    ctxs = prepare_all_contexts(payload)

    sales_data = fetch_sales_data(db, ctxs["sales"], payload.to_date)
    return_data = fetch_returns_data(db, ctxs["returns"], payload.to_date)
    target_data = fetch_target_data(db, ctxs["target"])

    region_data = compute_region_rows(
        sales_data, return_data, target_data,
        total_days=total_days,
        current_day=current_day,
    )

    wb = build_workbook(
        region_data,
        from_date=payload.from_date,
        to_date=payload.to_date,
    )

    # Write to a temp file and let FastAPI delete it after sending.
    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx", prefix="sales_achievement_")
    os.close(fd)
    wb.save(tmp_path)

    download_name = (
        f"sales_achievement_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    )

    return FileResponse(
        path=tmp_path,
        filename=download_name,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        background=BackgroundTask(_cleanup, tmp_path),
    )
