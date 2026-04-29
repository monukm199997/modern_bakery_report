from app.common.current_user_permissions import get_user_permissions
from app.common.filter_permission import apply_permission


def apply_payload_permissions(payload, current_user):

    perms = get_user_permissions(current_user)

    payload.company_ids = apply_permission(
        getattr(payload, "company_ids", None),
        perms["company"]
    )

    payload.region_ids = apply_permission(
        getattr(payload, "region_ids", None),
        perms["region"]
    )

    payload.route_ids = apply_permission(
        getattr(payload, "route_ids", None),
        perms["route"]
    )

    payload.salesman_ids = apply_permission(
        getattr(payload, "salesman_ids", None),
        perms["salesman"]
    )

    payload.customer_channel_ids = apply_permission(
        getattr(payload, "customer_channel_ids", None),
        perms["outlet_channel"]
    )

    payload.item_category_ids = apply_permission(
        getattr(payload, "item_category_ids", None),
        perms["item_category"]
    )

    payload.item_ids = apply_permission(
        getattr(payload, "item_ids", None),
        perms["item"]
    )

    # ---------------------------------------------------
    # Hierarchy propagation
    # ---------------------------------------------------
    # If lower level is unrestricted ([] => None)
    # then automatically restrict by upper level permission
    # ---------------------------------------------------

    # Company -> Region
    if (
        getattr(payload, "region_ids", None) is None
        and perms["region"] is not None
    ):
        payload.region_ids = perms["region"]

    # Region -> Route
    if (
        getattr(payload, "route_ids", None) is None
        and perms["route"] is None
        and getattr(payload, "region_ids", None) is not None
    ):
        # keep route unrestricted, region restriction will control it
        pass

    # Route -> Salesman
    if (
        getattr(payload, "salesman_ids", None) is None
        and perms["salesman"] is None
        and (
            getattr(payload, "route_ids", None) is not None
            or getattr(payload, "region_ids", None) is not None
        )
    ):
        # keep salesman unrestricted, route/region restriction controls it
        pass

    # Item Category -> Item
    if (
        getattr(payload, "item_ids", None) is None
        and perms["item"] is None
        and getattr(payload, "item_category_ids", None) is not None
    ):
        # keep item unrestricted inside permitted category
        pass

    return payload


# from app.common.current_user_permissions import get_user_permissions
# from app.common.filter_permission import apply_permission


# def apply_payload_permissions(payload, current_user):

#     perms = get_user_permissions(current_user)

#     payload.company_ids = apply_permission(
#         getattr(payload, "company_ids", None),
#         perms["company"]
#     )

#     payload.region_ids = apply_permission(
#         getattr(payload, "region_ids", None),
#         perms["region"]
#     )

#     payload.route_ids = apply_permission(
#         getattr(payload, "route_ids", None),
#         perms["route"]
#     )

#     payload.salesman_ids = apply_permission(
#         getattr(payload, "salesman_ids", None),
#         perms["salesman"]
#     )

#     payload.customer_channel_ids = apply_permission(
#         getattr(payload, "customer_channel_ids", None),
#         perms["salesman"]
#     )

#     payload.item_category_ids = apply_permission(
#         getattr(payload, "item_category_ids", None),
#         perms["item_category"]
#     )

#     payload.item_ids = apply_permission(
#         getattr(payload, "item_ids", None),
#         perms["item"]
#     )

#     return payload