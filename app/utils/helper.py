from fastapi import HTTPException
from datetime import datetime
from typing import List, Optional
from app.reports.sales_report.schemas.schemas import SalesReportRequest

def parse_csv_ids(s: Optional[str]) -> Optional[List[int]]:
    if not s:
        return None
    parts = [p.strip() for p in s.split(",") if p.strip() != ""]
    try:
        return [int(p) for p in parts]
    except ValueError:
        return None
    
def validate_mandatory(filters: SalesReportRequest):
    if not filters.from_date or not filters.to_date or not filters.search_type:
        raise HTTPException(status_code=400, detail="from_date, to_date, and search_type are required")
    try:
        _ = datetime.fromisoformat(filters.from_date)
        _ = datetime.fromisoformat(filters.to_date)
    except Exception:
        raise HTTPException(status_code=400, detail="from_date/to_date must be in YYYY-MM-DD format")


def choose_granularity(from_date_str: str, to_date_str: str) -> tuple[str, str, str]:
    d1 = datetime.fromisoformat(from_date_str).date()
    d2 = datetime.fromisoformat(to_date_str).date()
    days = (d2 - d1).days + 1

    if days <= 31:
        granularity = "daily"
        period_label_sql = """
        TO_CHAR(ih.invoice_date, 'YYYY-MM-DD')
        """
        order_by_sql = "ih.invoice_date"

    elif days <= 183:
        granularity = "weekly"

        period_label_sql = f"""
        CONCAT(
            TO_CHAR(GREATEST(DATE_TRUNC('week', ih.invoice_date), DATE '{from_date_str}'), 'DD Mon'),
            ' - ',
            TO_CHAR(
                LEAST(
                    DATE_TRUNC('week', ih.invoice_date) + INTERVAL '6 days',
                    DATE '{to_date_str}'
                ),
                'DD Mon'
            )
        )
        """
        order_by_sql = "DATE_TRUNC('week', ih.invoice_date)"

    else:
        granularity = "monthly"
        period_label_sql = """
        TO_CHAR(DATE_TRUNC('month', ih.invoice_date), 'Mon-YYYY')
        """
        order_by_sql = "DATE_TRUNC('month', ih.invoice_date)"

    return granularity, period_label_sql, order_by_sql


def quantity_expr_sql():
    return """
    ROUND(
        SUM(
            id.quantity * COALESCE(iu.upc::numeric, 1)
        )::numeric,
        2
    )
    """


