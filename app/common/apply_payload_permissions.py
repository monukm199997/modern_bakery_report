from fastapi import HTTPException
from app.common.permission_scope import resolve_scope

def _clean(value):
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 0:
        return None
    return list(value)

def apply_payload_permissions(payload, db, current_user):
    scope = resolve_scope(db, current_user)

    if scope["is_admin"]:
        return payload

    allowed_companies = scope["company_ids"]
    if not allowed_companies:
        raise HTTPException(status_code=403, detail="No data permission for this user")

    if hasattr(payload, "company_ids"):
        requested = _clean(getattr(payload, "company_ids"))
        if requested is None:
            payload.company_ids = allowed_companies
        else:
            final = [c for c in requested if c in allowed_companies]
            if not final:
                raise HTTPException(status_code=403, detail="No permission for requested company_ids")
            payload.company_ids = final

    for attr in ("route_ids", "salesman_ids"):
        if not hasattr(payload, attr):
            continue

        requested = _clean(getattr(payload, attr))
        if requested is None:
            setattr(payload, attr, None) 
            continue

        allowed = scope.get(attr) or []
        final = [x for x in requested if x in allowed]
        if not final:
            raise HTTPException(status_code=403, detail=f"No permission for requested {attr}")
        setattr(payload, attr, final)

    return payload