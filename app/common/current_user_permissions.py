from app.common.permission_utils import normalize_permission


def get_user_permissions(current_user):

    return {
        "company": normalize_permission(current_user.get("company")),
        "region": normalize_permission(current_user.get("region")),
        "route": normalize_permission(current_user.get("route")),
        "salesman": normalize_permission(current_user.get("salesman")),
        "outlet_channel": normalize_permission(current_user.get("outlet_channel")),
        "item_category": normalize_permission(current_user.get("item_category_id")),
        "item": normalize_permission(current_user.get("item_id")),
    }