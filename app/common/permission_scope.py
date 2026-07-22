from sqlalchemy import text
from app.common.permission_utils import normalize_permission

# DECISION 1: who is admin
ADMIN_ROLE_ID = 1


def is_admin(user) -> bool:
    return user.get("role") == ADMIN_ROLE_ID
    # alt (users.role: 0=SuperAdmin,1=admin,2=user):
    # return user.get("role") == 0
    # return user.get("role") in (0, 1)


def resolve_scope(db, user) -> dict:
    if is_admin(user):
        return {
            "is_admin": True,
            "company_ids": None,
            "region_ids": None,
            "route_ids": None,
            "salesman_ids": None,
        }

    company_ids = normalize_permission(user.get("company"))

    if not company_ids:
        return {
            "is_admin": False,
            "company_ids": [],
            "region_ids": None,
            "route_ids": [],
            "salesman_ids": [],
        }

    get_salesman = """
            SELECT id AS salesman_id, route_id
            FROM salesman
            WHERE company_id = ANY(:company_ids)
        """

    rows = (
        db.execute(
            text(get_salesman),
            {"company_ids": company_ids},
        )
        .mappings()
        .all()
    )
    salesman_ids = [r["salesman_id"] for r in rows]
    route_ids = sorted({r["route_id"] for r in rows if r["route_id"] is not None})

    return {
        "is_admin": False,
        "company_ids": company_ids,
        "region_ids": None,
        "route_ids": route_ids,
        "salesman_ids": salesman_ids,
    }
