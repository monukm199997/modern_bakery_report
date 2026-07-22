
def apply_permission_filter(selected_ids, allowed_ids):

    if allowed_ids is None:
        return selected_ids

    if selected_ids is None:
        return allowed_ids

    return [x for x in selected_ids if x in allowed_ids]
