def apply_permission(selected_ids, allowed_ids):

    # [] or None in permission means unrestricted
    if not allowed_ids:
        return selected_ids

    # User did not select anything -> show only allowed values
    if not selected_ids:
        return allowed_ids

    # User selected something -> keep only intersection
    return [x for x in selected_ids if x in allowed_ids]