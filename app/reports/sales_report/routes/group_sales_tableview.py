
from datetime import datetime

from fastapi import APIRouter, Depends

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.utils.constant import MONTH_ORDER
from app.reports.sales_report.utils.sql_query_helper import SELECT,GROUP_BY,CHANNEL_JOIN_SQL,ITEM_JOIN_SQL
from app.reports.customer_sales_report.utils.sql_query_helper import BASE_SQL
from app.dependencies.auth import get_current_user
from app.reports.sales_report.schemas.schemas import (
    SalesReportRequest
)
from app.reports.sales_report.utils.sales_report_helper import (
    prepare_dashboard_context,
)

router = APIRouter(tags=["Sales Report"],dependencies=[Depends(get_current_user)])

@router.post('/group-sales-matrix-tableview')
def group_sales_matrix_tableview(payload: SalesReportRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    current_year = datetime.now().year
    query = f"""
        WITH yearly_sales AS (
            SELECT
                {SELECT}
                EXTRACT(YEAR FROM ih.invoice_date)::text AS period,
                {ctx['value_expr']} AS value,
                'yearly' AS period_type,
                EXTRACT(YEAR FROM ih.invoice_date) AS sort_order
            {BASE_SQL}
            {CHANNEL_JOIN_SQL}
            {ITEM_JOIN_SQL}
            {ctx['join_sql']}
            WHERE
                {ctx['where_sql']}
                AND EXTRACT(YEAR FROM ih.invoice_date)
                    < :current_year
            GROUP BY
                {GROUP_BY}
                EXTRACT(YEAR FROM ih.invoice_date)
        ),
        monthly_sales AS (
            SELECT
                {SELECT}
                TO_CHAR(
                    ih.invoice_date,
                    'Mon-YY'
                ) AS period,
                {ctx['value_expr']} AS value,
                'monthly' AS period_type,
                EXTRACT(MONTH FROM ih.invoice_date) + 100 AS sort_order
            {BASE_SQL}
            {CHANNEL_JOIN_SQL}
            {ITEM_JOIN_SQL}
            {ctx['join_sql']}
            WHERE
                {ctx['where_sql']}
                AND EXTRACT(YEAR FROM ih.invoice_date)
                    = :current_year
            GROUP BY
                {GROUP_BY}
                TO_CHAR(
                    ih.invoice_date,
                    'Mon-YY'
                ),
                EXTRACT(MONTH FROM ih.invoice_date)
        )
        SELECT *
        FROM yearly_sales
        UNION ALL
        SELECT *
        FROM monthly_sales
        ORDER BY
            "Item",
            sort_order
    """
    params = {**ctx['params'], 'current_year': current_year}
    rows = db.execute(text(query),params).fetchall()
    data = [dict(r._mapping) for r in rows]
    return data