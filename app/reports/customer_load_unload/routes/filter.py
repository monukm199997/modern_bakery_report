from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional
from app.common.helper import parse_csv_ids
from app.core.database import get_db
from sqlalchemy import text


router = APIRouter(tags=["Load Unload Filter"])

@router.get("/load-unload-filter")
def comparison_filter(
    route_ids: Optional[str] = Query(None),
    salesman_ids: Optional[str] = Query(None),
    db = Depends(get_db)
):

    route_ids_list = parse_csv_ids(route_ids)
    salesman_ids_list = parse_csv_ids(salesman_ids)
    
    out = {}

    try:
        
        q = "SELECT id, route_name FROM tbl_route ORDER BY route_name"
        out["route"] = [
            dict(r._mapping) for r in db.execute(text(q)).fetchall()
            ]

        if route_ids_list:
                q = """
                    SELECT  id, osa_code || '-' || name as salesman_name
                    FROM salesman
                    WHERE route_id IN :route_ids
                    ORDER BY osa_code
                """
                out["salesman"] = [
                    dict(r._mapping)
                    for r in db.execute(
                        text(q), {"route_ids":tuple(route_ids_list)},
                    ).fetchall()
                ]

        elif salesman_ids_list:
                q = """
                    SELECT  id, osa_code || '-' || name as salesman_name
                    FROM salesman
                    WHERE id IN :salesman_ids
                    ORDER BY osa_code
                """
                out["salesman"] = [
                    dict(r._mapping)
                    for r in db.execute(
                        text(q), {"salesman_ids":tuple(salesman_ids_list)},
                    ).fetchall()
                ]
                        
        else:
                q = """
                    SELECT id, osa_code || '-' || name as salesman_name
                    FROM salesman
                    ORDER BY osa_code
                """
                out["salesman"] = [dict(r._mapping) for r in db.execute(text(q)).fetchall()]


    except Exception as e:
        print("FILTER ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))
    
    return out