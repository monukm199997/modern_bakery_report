def apply_permission_filters(request_ids, user_permissions):
    
    if user_permissions:
        return user_permissions

    return request_ids