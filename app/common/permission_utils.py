import json


def normalize_permission(value):

    # None or empty means unrestricted
    if value is None:
        return None

    if isinstance(value, list):
        return value if value else None

    if isinstance(value, str):

        value = value.strip()

        if value in ("", "[]"):
            return None

        try:
            parsed = json.loads(value)
            return parsed if parsed else None
        except Exception:
            return None

    return None