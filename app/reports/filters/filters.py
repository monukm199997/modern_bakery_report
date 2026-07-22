from functools import lru_cache
from typing import Optional
from fastapi import APIRouter, Query, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import get_db, engine
from app.utils.helper import parse_csv_ids
from app.dependencies.auth import get_current_user
from app.common.filter_permission import apply_permission_filter
from app.common.query_filter_builder import add_filter
from copy import deepcopy
from app.common.permission_scope import resolve_scope

router = APIRouter(tags=["Filters"])


@lru_cache(maxsize=1)
def load_static_filters():

    with engine.connect() as conn:

        companies = conn.execute(
            text(
                """
            SELECT id, company_code, company_name
            FROM tbl_company
            ORDER BY company_name
        """
            )
        ).fetchall()

        channels = conn.execute(
            text(
                """
            SELECT id, outlet_channel_code, outlet_channel
            FROM outlet_channel
            ORDER BY outlet_channel
        """
            )
        ).fetchall()

        categories = conn.execute(
            text(
                """
            SELECT id, category_code, category_name
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
def get_static_filters(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = resolve_scope(db, current_user)
    data = deepcopy(load_static_filters())

    if scope["company_ids"] is not None:
        allowed = set(scope["company_ids"])
        data["company"] = [x for x in data["company"] if x["id"] in allowed]

    if scope["route_ids"] is not None:
        if not scope["route_ids"]:
            data["customer_channel"] = []
        else:
            rows = db.execute(
                text(
                    """
                SELECT DISTINCT outlet_channel_id
                FROM agent_customers
                WHERE route_id = ANY(:route_ids) AND outlet_channel_id IS NOT NULL
            """
            ),
            {"route_ids": scope["route_ids"]}).fetchall()
            allowed_ch = {r[0] for r in rows}
            data["customer_channel"] = [x for x in data["customer_channel"] if x["id"] in allowed_ch]

    return data

@router.get("/regions")
def get_regions(
    company_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):
    query =  """
        SELECT id, region_code, region_name 
        FROM tbl_region 
        ORDER BY region_name
    """
    rows = db.execute(text(query)).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/routes")
def get_routes(
    region_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):
    selected_region_ids = parse_csv_ids(region_ids)
    scope = resolve_scope(db, current_user)
    final_region_ids = apply_permission_filter(selected_region_ids, scope["region_ids"])

    where, params = [], {}
    add_filter(where, params, "region_id", final_region_ids, "region_ids")
    add_filter(where, params, "id",scope["route_ids"], "route_ids")

    query = """
        SELECT id, route_code, route_name 
        FROM tbl_route
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY route_name"
    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/salesmen")
def get_salesmen(
    route_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):

    selected_route_ids = parse_csv_ids(route_ids)
    scope = resolve_scope(db, current_user)
    final_route_ids = apply_permission_filter(selected_route_ids, scope["route_ids"])

    where, params = [], {}
    add_filter(where, params, "route_id", final_route_ids, "route_ids")
    add_filter(where, params, "id", scope["salesman_ids"], "salesman_ids")

    query = """
        SELECT id, osa_code, name
        FROM salesman
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY name"
    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/items")
def get_items(
    category_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):
    selected_category_ids = parse_csv_ids(category_ids)
    where, params = [], {}

    add_filter(where, params, "category_id", selected_category_ids, "category_ids")

    query = """
        SELECT id, code, name 
        FROM items
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY name"
    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/customer")
def get_customer(
    outlet_channel_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user), 
    db: Session = Depends(get_db)
    ):
    selected_outlet_channel_ids = parse_csv_ids(outlet_channel_ids)
    scope = resolve_scope(db, current_user)

    where, params = [], {}
    add_filter(where, params, "route_id", scope["route_ids"], "route_ids")
    add_filter(where, params, "outlet_channel_id", selected_outlet_channel_ids, "outlet_channel_ids")

    query = "SELECT id, osa_code, name FROM agent_customers"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY name"
    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/super_wiser")
def get_super_wiser(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = resolve_scope(db, current_user)

    if scope["salesman_ids"] is None:
        rows = db.execute(text("""
            SELECT id, name
            FROM users
            WHERE role = 108
            ORDER BY name
        """)).fetchall()
        return [dict(r._mapping) for r in rows]

    if not scope["salesman_ids"]:
        return []
    
    rows = db.execute(text("""
        SELECT DISTINCT u.id, u.name
        FROM users u
        JOIN salesman s ON s.superwiser_id = u.id
        WHERE u.role = 108
          AND s.id = ANY(:salesman_ids)
        ORDER BY u.name
    """), {"salesman_ids": scope["salesman_ids"]}).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/customer_group")
def get_customer_group(
    customer_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = resolve_scope(db, current_user)
    selected_customer_ids = parse_csv_ids(customer_ids)

    where, params = [], {}

    add_filter(where, params, "route_id", scope["route_ids"], "route_ids")

    if selected_customer_ids:
        add_filter(where, params, "id", selected_customer_ids, "customer_ids")
        select_cols = "id, cust_group, payment_type"
        order_by = "ORDER BY cust_group"
    else:
        select_cols = "DISTINCT cust_group, payment_type"
        order_by = "ORDER BY payment_type, cust_group"

    query = f"SELECT {select_cols} FROM agent_customers"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " " + order_by

    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/customer_group_1")
def get_customer_group_1(
    customer_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = resolve_scope(db, current_user)
    selected_customer_ids = parse_csv_ids(customer_ids)

    where, params = [], {}
    add_filter(where, params, "route_id", scope["route_ids"], "route_ids")

    if selected_customer_ids:
        add_filter(where, params, "id", selected_customer_ids, "customer_ids")
        select_cols = 'id, customergroup, "CustomerGroupDesc"'
        order_by = "ORDER BY customergroup"
    else:
        select_cols = 'DISTINCT customergroup, "CustomerGroupDesc"'
        order_by = 'ORDER BY "CustomerGroupDesc", customergroup'

    query = f"SELECT {select_cols} FROM agent_customers"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " " + order_by

    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

@router.get("/customer_group_2")
def get_customer_group_2(
    customer_ids: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = resolve_scope(db, current_user)
    selected_customer_ids = parse_csv_ids(customer_ids)

    where, params = [], {}
    add_filter(where, params, "route_id", scope["route_ids"], "route_ids")

    if selected_customer_ids:
        add_filter(where, params, "id", selected_customer_ids, "customer_ids")
        select_cols = 'id, customergroup2, "CustomerGroupDesc2"'
        order_by = "ORDER BY customergroup2"
    else:
        select_cols = 'DISTINCT customergroup2, "CustomerGroupDesc2"'
        order_by = 'ORDER BY "CustomerGroupDesc2", customergroup2'

    query = f"SELECT {select_cols} FROM agent_customers"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " " + order_by

    rows = db.execute(text(query), params).fetchall()
    return [dict(r._mapping) for r in rows]

