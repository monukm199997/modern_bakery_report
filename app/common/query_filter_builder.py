

def add_filter(where, params, column, value, param_name):
    if value:
        where.append(f"{column} = ANY(:{param_name})")
        params[param_name] = value