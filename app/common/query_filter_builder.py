
# def add_filter(where, params, column, value, param_name):
#     if value:
#         where.append(f"{column} = ANY(:{param_name})")
#         params[param_name] = value

def add_filter(where, params, column, value, param_name):

    # None means no filter
    if value is None:
        return

    # Empty list means impossible result
    if value == []:
        where.append("1 = 0")
        return

    where.append(f"{column} = ANY(:{param_name})")
    params[param_name] = value