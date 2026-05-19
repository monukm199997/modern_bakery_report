from functools import lru_cache
from typing import Optional
from unittest import result
from app.core.database import get_db
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import engine
from app.utils.helper import parse_csv_ids
from app.dependencies.auth import get_current_user
from app.common.current_user_permissions import get_user_permissions
from app.common.filter_permission import apply_permission_filter
from app.common.query_filter_builder import add_filter
from copy import deepcopy

router = APIRouter(tags=["Filters"])


@lru_cache(maxsize=1)
def load_static_filters():

    with engine.connect() as conn:

        companies = conn.execute(
            text(
                """
            SELECT id, company_name
            FROM tbl_company
            ORDER BY company_name
        """
            )
        ).fetchall()

        channels = conn.execute(
            text(
                """
            SELECT id, outlet_channel
            FROM outlet_channel
            ORDER BY outlet_channel
        """
            )
        ).fetchall()

        categories = conn.execute(
            text(
                """
            SELECT id, category_name
            FROM item_categories
            ORDER BY category_name
        """
            )
        ).fetchall()

    return {
        "company": [dict(r._mapping) for r in companies],
        "customer_channel": [dict(r._mapping) for r in channels],
        "item_category": [dict(r._mapping) for r in categories],
    }


@router.get("/static")
def get_static_filters(current_user=Depends(get_current_user)):

    perms = get_user_permissions(current_user)

    data = deepcopy(load_static_filters())

    # Restrict company list
    if perms["company"]:
        data["company"] = [x for x in data["company"] if x["id"] in perms["company"]]

    # Restrict channel list
    if perms["outlet_channel"]:
        data["customer_channel"] = [
            x for x in data["customer_channel"] if x["id"] in perms["outlet_channel"]
        ]

    # Restrict item category list
    if perms["item_category"]:
        data["item_category"] = [
            x for x in data["item_category"] if x["id"] in perms["item_category"]
        ]

    return data


@router.get("/regions")
def get_regions(
    company_ids: Optional[str] = Query(None), current_user=Depends(get_current_user), db:Session = Depends(get_db)
):

    selected_company_ids = parse_csv_ids(company_ids)

    perms = get_user_permissions(current_user)

    final_company_ids = apply_permission_filter(
        selected_company_ids,
        perms["company"]
    )

    where = []
    params = {}

    add_filter(where, params, "company_id", final_company_ids, "company_ids")
    add_filter(where, params, "id", perms["region"], "region_ids")

    query = """
        SELECT id, region_name
        FROM tbl_region
    """

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY region_name"

    
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result


@router.get("/routes")
def get_routes(
    region_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db:Session = Depends(get_db)
):
    selected_region_ids = parse_csv_ids(region_ids)
    perms = get_user_permissions(current_user)

    final_region_ids = apply_permission_filter(
        selected_region_ids,
        perms["region"]
    )

    where = []
    params = {}

    add_filter(where, params, "region_id", final_region_ids, "region_ids")
    add_filter(where, params, "id", perms["route"], "route_ids")

    query = """
        SELECT id, route_name
        FROM tbl_route
    """

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY route_name"

    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result


@router.get("/salesmen")
def get_salesmen(
    route_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db:Session = Depends(get_db)
):

    selected_route_ids = parse_csv_ids(route_ids)

    perms = get_user_permissions(current_user)

    # Case 1: user has explicit route permission
    if perms["route"] is not None:
        allowed_route_ids = perms["route"]
    # Case 2: route=[] -> allow all routes under permitted regions
    elif perms["region"] is not None:

        rows = db.execute(text("""
            SELECT id
            FROM tbl_route
            WHERE region_id = ANY(:region_ids)
        """), {
            "region_ids": perms["region"]
        }).fetchall()

        allowed_route_ids = [r[0] for r in rows]

    # Case 3: no restriction at all
    else:
        allowed_route_ids = None

    # --------------------------------------------------
    # Apply selected route against allowed route ids
    # --------------------------------------------------

    final_route_ids = apply_permission_filter(
        selected_route_ids,
        allowed_route_ids
    )

    where = []
    params = {}

    add_filter(where, params, "route_id", final_route_ids, "route_ids")
    add_filter(where, params, "id", perms["salesman"], "salesman_ids")

    query = """
        SELECT id, name
        FROM salesman
    """

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY name"

    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result


@router.get("/items")
def get_items(
    category_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db:Session = Depends(get_db)
):

    selected_category_ids = parse_csv_ids(category_ids)

    perms = get_user_permissions(current_user)

    final_category_ids = apply_permission_filter(
        selected_category_ids,
        perms["item_category"]
    )

    where = []
    params = {}

    add_filter(where, params, "category_id", final_category_ids, "category_ids")
    add_filter(where, params, "id", perms["item"], "item_ids")

    query = """
        SELECT id, name
        FROM items
    """

    if where:
        query += " WHERE " + " AND ".join(where)

    query += " ORDER BY name"
    
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result

@router.get("/customer")
def get_customer(
    outlet_channel_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db:Session = Depends(get_db)
):
    selected_category_ids = parse_csv_ids(outlet_channel_ids)
    perms = get_user_permissions(current_user)

    final_outlet_channel_ids = apply_permission_filter(
        selected_category_ids,
        perms["item_category"]
    )

    where = []
    params = {}

    add_filter(where, params, "outlet_channel_id", final_outlet_channel_ids, "outlet_channel_ids")
    add_filter(where, params, "id", perms["customer"], "customer_ids")

    query = """
        SELECT id, name
        FROM agent_customers
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY name"
    
    rows = db.execute(text(query), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return result