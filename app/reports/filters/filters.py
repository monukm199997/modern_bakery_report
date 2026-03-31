from fastapi import APIRouter, Query
from sqlalchemy import text
from functools import lru_cache
from app.core.database import engine
from typing import Optional, List
from app.common.helper import parse_csv_ids

router = APIRouter(tags=["Filters"])


@lru_cache(maxsize=1)
def load_static_filters():

    with engine.connect() as conn:

        companies = conn.execute(text("""
            SELECT id, company_name
            FROM tbl_company
            ORDER BY company_name
        """)).fetchall()

        channels = conn.execute(text("""
            SELECT id, outlet_channel
            FROM outlet_channel
            ORDER BY outlet_channel
        """)).fetchall()

        categories = conn.execute(text("""
            SELECT id, category_name
            FROM item_categories
            ORDER BY category_name
        """)).fetchall()

    return {
        "company": [dict(r._mapping) for r in companies],
        "customer_channel": [dict(r._mapping) for r in channels],
        "item_category": [dict(r._mapping) for r in categories],
    }


@router.get("/static")
def get_static_filters():
    return load_static_filters()


@router.get("/regions")
def get_regions(company_ids: Optional[str] = Query(None)):

    company_ids_list = parse_csv_ids(company_ids)

    query = """
        SELECT id, region_name
        FROM tbl_region
        WHERE (:company_ids IS NULL OR company_id = ANY(:company_ids))
        ORDER BY region_name
    """

    with engine.connect() as conn:
        rows = conn.execute(
            text(query),
            {"company_ids": company_ids_list}
        ).fetchall()

    return [dict(r._mapping) for r in rows]


@router.get("/routes")
def get_routes(region_ids: Optional[str] = Query(None)):
    region_ids_list = parse_csv_ids(region_ids)

    query = """
        SELECT id, route_name
        FROM tbl_route
        WHERE (:region_ids IS NULL OR region_id = ANY(:region_ids))
        ORDER BY route_name
    """

    with engine.connect() as conn:
        rows = conn.execute(text(query), {
            "region_ids": region_ids_list
        }).fetchall()
    return [dict(r._mapping) for r in rows]


@router.get("/salesmen")
def get_salesmen(route_ids: Optional[str] = Query(None)):
    route_ids_list = parse_csv_ids(route_ids)

    query = """
        SELECT id, name
        FROM salesman
        WHERE (:route_ids IS NULL OR route_id = ANY(:route_ids))
        ORDER BY name
    """

    with engine.connect() as conn:
        rows = conn.execute(text(query), {
            "route_ids": route_ids_list
        }).fetchall()

    return [dict(r._mapping) for r in rows]


@router.get("/items")
def get_items(category_ids: Optional[str] = Query(None)):
    category_ids_list = parse_csv_ids(category_ids)

    query = """
        SELECT id, name
        FROM items
        WHERE (:category_ids IS NULL OR category_id = ANY(:category_ids))
        ORDER BY name
    """

    with engine.connect() as conn:
        rows = conn.execute(text(query), {
            "category_ids": category_ids_list
        }).fetchall()

    return [dict(r._mapping) for r in rows]