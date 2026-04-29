
def apply_permission_filter(selected_ids, allowed_ids):

    # no permission restriction
    if allowed_ids is None:
        return selected_ids

    # nothing selected -> show all allowed
    if selected_ids is None:
        return allowed_ids

    # selected but not allowed -> may become []
    return [x for x in selected_ids if x in allowed_ids]

def apply_permission(selected_ids, allowed_ids):

    # no permission restriction
    if allowed_ids is None:
        return selected_ids

    # user has not selected anything
    # keep None so query remains dynamic
    if selected_ids is None:
        return None

    # keep only allowed selections
    return [x for x in selected_ids if x in allowed_ids]