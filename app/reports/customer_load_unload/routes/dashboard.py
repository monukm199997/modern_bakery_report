from fastapi import APIRouter, Depends
from app.reports.customer_load_unload.schemas.schema import LoadUnloadReportRequest
from app.common.helper import validate_mandatory, quantity_expr_sql
from app.reports.customer_load_unload.utils.load_unload_helper import sales_query_parts
from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text

router = APIRouter(tags=["Load Unload Dashboard"])
@router.post("/total-load")
async def total_load(payload:LoadUnloadReportRequest, db: Session = Depends(get_db) ):
    validate_mandatory(payload)

    where_fragments, params = sales_query_parts(payload)
    where_sql = " AND ".join(where_fragments)
    

    quantity = quantity_expr_sql()
    value_expr = (
        quantity if payload.search_type.lower() == "quantity"
        else "SUM(id.item_total)"
    )

    query = f"""
            SELECT
            id.item_id,
            {value_expr} AS total_sales
            FROM invoice_headers ih
            JOIN invoice_details id ON id.header_id = ih.id
            LEFT JOIN item_uoms iu
                ON iu.item_id = id.item_id
                AND iu.uom_id = id.uom
            WHERE {where_sql}
            GROUP BY id.item_id
            """
    result = db.execute(text(query), params).fetchall()
    out = [dict(r._mapping)for r in result]
    return {"tatal_sale": out}





    
