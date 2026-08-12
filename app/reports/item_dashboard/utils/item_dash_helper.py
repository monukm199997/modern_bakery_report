from app.reports.item_dashboard.schemas.item_dash_schema import ItemDashboardRequest
from app.utils.helper import validate_mandatory, quantity_expr_sql
from sqlalchemy import text
from datetime import date, timedelta, datetime
from app.reports.item_dashboard.utils.sql_query_helper import STOCK_BASE_SQL,SALES_BASE_SQL, REVENUE_NET_SALES, VOLUME_NET_SALES

def get_stock_quantity():
    return """
    ROUND(
        SUM(
            d.qty::numeric 
        ),
        3
    )
    """

def choose_granularity(
    from_date_str: str,
    to_date_str: str,
    date_column: str
):
    d1 = datetime.fromisoformat(from_date_str).date()
    d2 = datetime.fromisoformat(to_date_str).date()
    days = (d2-d1).days+1
    if days <= 31:
        granularity="daily"
        period_label_sql=f"TO_CHAR({date_column},'YYYY-MM-DD')"
        order_by_sql=date_column

    elif days<=183:
        granularity="weekly"
        period_label_sql=f"""
        CONCAT(
            TO_CHAR(
                GREATEST(
                    DATE_TRUNC('week',{date_column}),DATE '{from_date_str}'), 'DD Mon'),
                ' - ',
            TO_CHAR(
                LEAST(
                    DATE_TRUNC('week',{date_column}) + INTERVAL '6 days', DATE '{to_date_str}'), 'DD Mon')
                )
        """
        order_by_sql=f"DATE_TRUNC('week',{date_column})"

    else:
        granularity="monthly"
        period_label_sql=f"""
        TO_CHAR(
        DATE_TRUNC('month',{date_column}), 'Mon-YYYY')
        """
        order_by_sql=f"""
        DATE_TRUNC('month',{date_column})
        """
    return (
    granularity,
    period_label_sql,
    order_by_sql
    )

def build_sales_query_parts(payload):
    joins = []
    where = []
    params = {}
    where.append("""ih.invoice_date BETWEEN :from_date AND :to_date""")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("""LEFT JOIN salesman s ON s.id=ih.salesman_id""")
        where.append("s.company_id=ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("""LEFT JOIN tbl_route rt ON rt.id=ih.route_id""")
        where.append("rt.region_id=ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where.append("ih.route_id=ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
    
    if payload.item_category_ids:
        where.append("i.category_id = ANY(:item_category_ids)")
        params["item_category_ids"] = payload.item_category_ids

    if payload.item_ids:
        where.append("id.item_id = ANY(:item_ids)")
        params["item_ids"] = payload.item_ids

    quantity = VOLUME_NET_SALES
    return {
        "join_sql":"\n".join(joins),
        "where_sql":" AND ".join(where) if where else "1=1",
        "params":params,
        "quantity": quantity
    }

def prepare_sales_context(payload):
    validate_mandatory(payload)
    return build_sales_query_parts(payload)

def build_stock_query_parts(payload):
    joins = []
    where_fragments = []
    params = {}
    where_fragments.append("h.created_at::date BETWEEN :from_date AND :to_date")
    params["from_date"] = payload.from_date
    params["to_date"] = payload.to_date

    if payload.company_ids:
        joins.append("""LEFT JOIN salesman s ON s.id = h.salesman_id""")
        where_fragments.append("s.company_id = ANY(:company_ids)")
        params["company_ids"] = payload.company_ids

    if payload.region_ids:
        joins.append("""LEFT JOIN tbl_route rt ON rt.id = h.route_id""")
        where_fragments.append("rt.region_id = ANY(:region_ids)")
        params["region_ids"] = payload.region_ids

    if payload.route_ids:
        where_fragments.append("h.route_id = ANY(:route_ids)")
        params["route_ids"] = payload.route_ids
    
    if payload.item_category_ids:
        where_fragments.append("i.category_id = ANY(:item_category_ids)")
        params["item_category_ids"] = payload.item_category_ids

    if payload.item_ids:
        where_fragments.append("d.item_id = ANY(:item_ids)")
        params["item_ids"] = payload.item_ids

    joins = list(dict.fromkeys(joins))
    return (
        "\n".join(joins),
        " AND ".join(where_fragments) if where_fragments else "1=1",
        params,
    )

def prepare_stock_context(payload):
    validate_mandatory(payload)
    quantity = get_stock_quantity()
    joins, where_sql, params = build_stock_query_parts(payload)

    return {
        "join_sql": joins,
        "where_sql": where_sql,
        "params": params,
        "quantity": quantity
    }

def total_items(db):
    sql = """
    SELECT COUNT(*)
    FROM items
    WHERE deleted_at IS NULL
    """
    return db.execute(text(sql)).scalar() or 0

def active_items(db):
    sql = """
    SELECT COUNT(*)
    FROM items
    WHERE deleted_at IS NULL
    AND status=1
    """
    return db.execute(text(sql)).scalar() or 0

def total_stock(payload, db):
    ctx = prepare_stock_context(payload)
    sql = f"""
    SELECT
        COALESCE({ctx['quantity']},0) total_stock
    {STOCK_BASE_SQL}
    LEFT JOIN items i ON i.id=d.item_id
    {ctx['join_sql']}
    WHERE
    h.deleted_at IS NULL
    AND d.deleted_at IS NULL
    AND {ctx['where_sql']}
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def stocked_skus(payload, db):
    ctx = prepare_stock_context(payload)
    sql = f"""
    SELECT
    COUNT(DISTINCT d.item_id)
    {STOCK_BASE_SQL}
    LEFT JOIN items i ON i.id=d.item_id
    {ctx['join_sql']}
    WHERE
    h.deleted_at IS NULL
    AND d.deleted_at IS NULL
    AND d.qty>0
    AND {ctx['where_sql']}
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def inventory_value(payload, db):
    ctx = prepare_stock_context(payload)
    sql = f"""
    SELECT
    COALESCE(SUM(d.qty*d.price),0)
    {STOCK_BASE_SQL}
    LEFT JOIN items i ON i.id=d.item_id
    {ctx['join_sql']}
    WHERE
    h.deleted_at IS NULL
    AND d.deleted_at IS NULL
    AND {ctx['where_sql']}
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def out_of_stock(payload, db):
    ctx = prepare_stock_context(payload)
    sql = f"""
    SELECT COUNT(*)
    FROM(
        SELECT
            d.item_id,
            {ctx['quantity']} AS qty
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY d.item_id
        )x
    WHERE qty<=0
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def low_stock(payload, db):
    ctx = prepare_stock_context(payload)
    sql = f"""
    SELECT COUNT(*)
    FROM(
        SELECT
            d.item_id,
            {ctx['quantity']} qty
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY d.item_id
        )x
    WHERE qty>0
    AND qty<=5
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def over_stock(payload, db):
    ctx = prepare_stock_context(payload)
    sql = f"""
    SELECT COUNT(*)
    FROM(
        SELECT
            d.item_id,
            {ctx['quantity']} qty
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY d.item_id
        )x
    WHERE qty>=100
    """
    return db.execute(text(sql), ctx["params"]).scalar() or 0

def fast_movers(payload, db):
    ctx_sales = prepare_sales_context(payload)
    sql = f"""
    SELECT COUNT(*)
    FROM(
        SELECT
            id.item_id,
            {ctx_sales['quantity']} AS value
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id=id.item_id
        {ctx_sales['join_sql']}
        WHERE
            {ctx_sales['where_sql']}
        GROUP BY id.item_id
        ORDER BY value DESC
        LIMIT 30
        )x
    """
    return db.execute(text(sql), ctx_sales["params"]).scalar() or 0

def dead_stock(payload, db):
    stock_ctx = prepare_stock_context(payload)
    sales_ctx = prepare_sales_context(payload)
    cutoff_date = date.today() - timedelta(days=90)
    params = stock_ctx["params"].copy()

    if "company_ids" in sales_ctx["params"]:
        params["company_ids"] = sales_ctx["params"]["company_ids"]

    if "region_ids" in sales_ctx["params"]:
        params["region_ids"] = sales_ctx["params"]["region_ids"]

    if "route_ids" in sales_ctx["params"]:
        params["route_ids"] = sales_ctx["params"]["route_ids"]

    params["cutoff_date"] = cutoff_date
    sales_where = []
    sales_where.append(
        "ih.invoice_date >= :cutoff_date"
    )
    if payload.company_ids:
        sales_where.append(
            "s.company_id = ANY(:company_ids)"
        )
    if payload.region_ids:
        sales_where.append(
            "rt.region_id = ANY(:region_ids)"
        )
    if payload.route_ids:
        sales_where.append(
            "ih.route_id = ANY(:route_ids)"
        )
    sales_where_sql = " AND ".join(sales_where)
    sql = f"""
    WITH stocked AS(
        SELECT
            d.item_id
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {stock_ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND d.qty>0
            AND {stock_ctx['where_sql']}
        GROUP BY d.item_id
    ),
    recent_sales AS(
        SELECT
            id.item_id
        FROM invoice_headers ih
        JOIN invoice_details id ON id.header_id=ih.id
        LEFT JOIN salesman s ON s.id=ih.salesman_id
        LEFT JOIN tbl_route rt ON rt.id=ih.route_id
        LEFT JOIN items i ON i.id=id.item_id
        WHERE
            {sales_where_sql}
        GROUP BY id.item_id
    )
    SELECT COUNT(*)
    FROM stocked s
    WHERE NOT EXISTS(
        SELECT 1
        FROM recent_sales r
        WHERE r.item_id=s.item_id
    )
    """
    return (db.execute(text(sql), params).scalar() or 0 )

def get_stock_health_route(payload, db, page, page_size):
    ctx = prepare_stock_context(payload)
    offset = (page-1)*page_size
    sql = f"""
    WITH item_stock AS(
        SELECT
            h.route_id,
            d.item_id,
            {ctx['quantity']} qty
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY
            h.route_id,
            d.item_id
        )

    SELECT
        rt.route_name,
        COUNT(*) FILTER(
            WHERE qty<=0
            ) out,
        COUNT(*) FILTER(
            WHERE qty>0
            AND qty<=5
            ) low,
        COUNT(*) FILTER(
            WHERE qty>5
            AND qty<100
            ) healthy,

        COUNT(*) FILTER(
            WHERE qty>=100
            ) overstock

    FROM item_stock s
    JOIN tbl_route rt ON rt.id=s.route_id
    GROUP BY
        rt.route_name
    ORDER BY rt.route_name
    LIMIT :limit
    OFFSET :offset
    """

    count_sql = f"""
    SELECT COUNT(*)
    FROM(
        SELECT DISTINCT
            h.route_id
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND {ctx['where_sql']}
    )x
    """
    params = {
    **ctx["params"],
    "limit":page_size,
    "offset":offset
    }

    total = db.execute(text(count_sql), ctx["params"]).scalar()
    rows = db.execute(text(sql),params).fetchall()
    result = [dict(r._mapping) for r in rows]

    return{
    "total_records":total,
    "page":page,
    "page_size":page_size,
    "rows": result
    }

def get_route_stock_distribution(payload, db, limit):
    ctx = prepare_stock_context(payload)
    sql = f"""
        SELECT
            rt.id,
            rt.route_name,
            {ctx['quantity']} stock
        {STOCK_BASE_SQL}
        LEFT JOIN salesman s ON s.id = h.salesman_id
        LEFT JOIN tbl_route rt ON rt.id = h.route_id
        LEFT JOIN items i ON i.id = d.item_id
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY
            rt.id,
            rt.route_name
        ORDER BY stock DESC
        LIMIT :limit
        """
    params = {
    **ctx["params"],
    "limit":limit
    }
    rows = db.execute(text(sql),params).mappings().all()
    total_stock = sum(float(r["stock"] or 0) for r in rows)
    result = []

    for row in rows:
        stock = float(row["stock"] or 0)
        pct = 0

        if total_stock:
            pct = round(stock*100/total_stock, 2)

        result.append({
        "route_id":row["id"],
        "route_name":row["route_name"],
        "stock":stock,
        "percentage":pct
        })

    return{
    "total_stock":total_stock,
    "routes":result

    }

def get_purchase_trend(payload, db):
    ctx = prepare_stock_context(payload)
    _, period_sql, order_sql = choose_granularity(
        payload.from_date,
        payload.to_date,
        "h.created_at"
    )

    sql = f"""
    SELECT
        {period_sql} AS period,
        TO_CHAR({order_sql},'YYYY-MM-DD') AS sort_date,
        COALESCE(
            {ctx['quantity']},
            0
        ) AS purchase
    {STOCK_BASE_SQL}
    LEFT JOIN items i ON i.id=d.item_id
    {ctx['join_sql']}
    WHERE
        h.deleted_at IS NULL
        AND d.deleted_at IS NULL
        AND {ctx['where_sql']}
    GROUP BY
        sort_date,
        period
    ORDER BY
        sort_date
    """
    rows = db.execute(text(sql),ctx["params"]).mappings().all()
    return [{
        "period":row["period"],
        "sort_date":row["sort_date"],
        "purchase":float(
        row["purchase"] or 0
        )
        }
        for row in rows
    ]

def get_sales_trend(payload, db):
    ctx = prepare_sales_context(payload)
    _, period_sql, order_sql = choose_granularity(
        payload.from_date,
        payload.to_date,
        "ih.invoice_date"
    )
    sql = f"""
    SELECT
        {period_sql} AS period,
        TO_CHAR({order_sql},'YYYY-MM-DD') AS sort_date,
        COALESCE(
            {ctx['quantity']},
            0
        ) AS sales
    {SALES_BASE_SQL}
    LEFT JOIN items i ON i.id=id.item_id
    {ctx['join_sql']}
    WHERE
    {ctx['where_sql']}
    GROUP BY
        sort_date,
        period
    ORDER BY
        sort_date
    """
    rows = db.execute(text(sql),ctx["params"]).mappings().all()
    return [{
        "period":row["period"],
        "sort_date":row["sort_date"],
        "sales":float(
        row["sales"] or 0
        )}
        for row in rows
    ]

def get_fast_slow_movers(payload, db, limit):

    ctx = prepare_sales_context(payload)
    base_sql = f"""
        SELECT
            i.id,
            i.code,
            i.name,
            COALESCE({ctx['quantity']}, 0) qty
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id=id.item_id
        {ctx['join_sql']}
        WHERE
            i.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY
            i.id,
            i.code,
            i.name
        """
    fast_sql = f"""
        {base_sql}
        ORDER BY
        qty DESC,
        i.name
        LIMIT :limit
        """
    
    slow_sql = f"""
        {base_sql}
        ORDER BY
        qty ASC,
        i.name
        LIMIT :limit
        """
    
    params = {
        **ctx["params"],
        "limit": limit
        }
    
    fast = db.execute(text(fast_sql),params).fetchall()
    fast_move_rows = [dict(r._mapping) for r in fast]
    slow = db.execute(text(slow_sql),params).fetchall()
    slow_move_rows = [dict(r._mapping) for r in slow]

    return{
            "fast_movers":fast_move_rows,
            "slow_movers":slow_move_rows
            }

def get_sales_categories(payload, db, page, page_size):
    ctx=prepare_sales_context(payload)
    offset=(page-1)*page_size
    sql=f"""
        SELECT
            c.id,
            c.category_name,
            {ctx['quantity']} quantity,
            {REVENUE_NET_SALES} AS revenue
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id=id.item_id
        {ctx['join_sql']}
        LEFT JOIN item_categories c ON c.id=i.category_id
        WHERE
            {ctx['where_sql']}
        GROUP BY
            c.id,
            c.category_name
        ORDER BY
            quantity DESC
        LIMIT :limit
        OFFSET :offset
    """

    count_sql=f"""
    SELECT COUNT(*)
    FROM(
        SELECT
            c.id
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id=id.item_id
        {ctx['join_sql']}
        LEFT JOIN item_categories c ON c.id=i.category_id
        WHERE
            {ctx['where_sql']}
        GROUP BY
            c.id
    )x
    """

    params={
    **ctx["params"],
    "limit":page_size,
    "offset":offset
    }

    total=db.execute(text(count_sql), ctx["params"]).scalar()
    rows=db.execute(text(sql), params).fetchall()
    result = [dict(r._mapping) for r in rows]
    return{
    "total_records":total,
    "page":page,
    "page_size":page_size,
    "rows":result
    }

def get_item_aging(payload, db):

    stock_ctx=prepare_stock_context(payload)
    sales_ctx=prepare_sales_context(payload)

    sql=f"""
        WITH stocked AS(
            SELECT
                d.item_id
            {STOCK_BASE_SQL}
            LEFT JOIN items i ON i.id=d.item_id
            {stock_ctx['join_sql']}
            WHERE
                h.deleted_at IS NULL
                AND d.deleted_at IS NULL
                AND {stock_ctx['where_sql']}
            GROUP BY
                d.item_id
                HAVING SUM(d.qty)>0
            ),

            last_sale AS(
                SELECT
                    id.item_id,
                    MAX(ih.invoice_date) last_sale
                FROM invoice_headers ih
                LEFT JOIN invoice_details id ON id.header_id=ih.id
                LEFT JOIN items i ON i.id=id.item_id
                {sales_ctx['join_sql']}
                WHERE
                    {sales_ctx['where_sql']}
                GROUP BY
                    id.item_id
                )

            SELECT
                COUNT(*) FILTER(
                WHERE
                    last_sale IS NOT NULL
                    AND
                    CURRENT_DATE-last_sale<=30
                    ) b0,

                COUNT(*) FILTER(
                WHERE
                    CURRENT_DATE-last_sale
                    BETWEEN 31 AND 60
                    ) b1,

                COUNT(*) FILTER(
                WHERE
                    CURRENT_DATE-last_sale
                    BETWEEN 61 AND 90
                    ) b2,

                COUNT(*) FILTER(
                WHERE
                    CURRENT_DATE-last_sale
                    BETWEEN 91 AND 180
                    ) b3,

                COUNT(*) FILTER(
                WHERE
                    CURRENT_DATE-last_sale>180
                    ) b4,

                COUNT(*) FILTER(
                WHERE
                    last_sale IS NULL
                    ) b5

            FROM stocked s
            LEFT JOIN last_sale l ON l.item_id=s.item_id
            """

    row = db.execute(text(sql),{**stock_ctx["params"],**sales_ctx["params"]}).mappings().first()

    return{
            "0_30":int(row["b0"] or 0),
            "31_60":int(row["b1"] or 0),
            "61_90":int(row["b2"] or 0),
            "91_180":int(row["b3"] or 0),
            "180_plus":int(row["b4"] or 0),
            "never_sold":int(row["b5"] or 0)
        }

def get_low_stock_alert(payload, db, page, page_size, threshold):
    ctx = prepare_stock_context(payload)
    offset = (page - 1) * page_size
    sql = f"""
    WITH stock_summary AS (
        SELECT
            h.route_id,
            d.item_id,
            {ctx['quantity']} current_qty
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY
            h.route_id,
            d.item_id
    )
    SELECT
        i.code AS item_code,
        i.name AS item_name,
        r.route_name,
        c.category_name AS category,
        ss.current_qty
    FROM stock_summary ss
    LEFT JOIN items i ON i.id = ss.item_id
    LEFT JOIN item_categories c ON c.id=i.category_id
    LEFT JOIN tbl_route r ON r.id = ss.route_id
    WHERE
        ss.current_qty <= :threshold
    ORDER BY
        ss.current_qty,
        i.name
    LIMIT :limit
    OFFSET :offset
    """

    count_sql = f"""
    SELECT COUNT(*)
    FROM(
        SELECT
            h.route_id,
            d.item_id
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id=d.item_id
        {ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {ctx['where_sql']}
        GROUP BY
            h.route_id,
            d.item_id
        HAVING {ctx['quantity']} <= :threshold

    )x
    """

    params = {
        **ctx["params"],
        "threshold": threshold,
        "limit": page_size,
        "offset": offset
    }

    total = db.execute(text(count_sql),params).scalar()
    rows = db.execute(text(sql),params).mappings().all()

    return {
        "total_records": total,
        "page": page,
        "page_size": page_size,
        "threshold": threshold,
        "rows": [
            {
                "item_code": r["item_code"],
                "item_name": r["item_name"],
                "route_name": r["route_name"],
                "category": r["category"],
                "current_qty": float(
                    r["current_qty"] or 0
                ),
                "threshold": threshold
            }
            for r in rows
        ]
    }

def get_top_selling_items(payload, db, page, page_size):
    ctx = prepare_sales_context(payload)
    offset = (page - 1) * page_size

    sql = f"""
        SELECT
            i.id,
            i.code AS item_code,
            i.name AS item_name,
            c.category_name AS category,
            {ctx['quantity']} quantity,
            {REVENUE_NET_SALES} AS revenue
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        LEFT JOIN item_categories c ON c.id=i.category_id
        {ctx['join_sql']}
        WHERE
            {ctx['where_sql']}
        GROUP BY i.id, i.code, i.name, c.category_name
        ORDER BY
            quantity DESC,
            i.name
        LIMIT :limit
        OFFSET :offset
        """
    
    count_sql = f"""
        SELECT COUNT(*)
        FROM(
            SELECT
                i.id
            {SALES_BASE_SQL}
            LEFT JOIN items i ON i.id = id.item_id
            {ctx['join_sql']}
            WHERE
                {ctx['where_sql']}
            GROUP BY
                i.id
        )x
        """
    params = {
        **ctx["params"],
        "limit": page_size,
        "offset": offset
    }
    total = db.execute(text(count_sql), ctx["params"]).scalar()
    rows = db.execute(text(sql), params).fetchall()
    result = [dict(r._mapping) for r in rows]

    return {
        "total_records": total,
        "page": page,
        "page_size": page_size,
        "rows": result
    }

def get_reorder_forecast(payload, db, page, page_size):
    stock_ctx=prepare_stock_context(payload)
    sales_ctx=prepare_sales_context(payload)
    offset=(page-1)*page_size

    days=(
    datetime.fromisoformat(payload.to_date).date()
    -
    datetime.fromisoformat(payload.from_date).date()
    ).days+1

    sql=f"""
    WITH stock AS(
        SELECT
            d.item_id,
            {stock_ctx['quantity']} stock_now
        {STOCK_BASE_SQL}
        LEFT JOIN items i ON i.id = d.item_id
        {stock_ctx['join_sql']}
        WHERE
            h.deleted_at IS NULL
            AND d.deleted_at IS NULL
            AND {stock_ctx['where_sql']}
        GROUP BY
            d.item_id
        ),

    sales AS(
        SELECT
            id.item_id,
            {sales_ctx['quantity']} sold_qty
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        {sales_ctx['join_sql']}
        WHERE
            {sales_ctx['where_sql']}
        GROUP BY
            id.item_id
        )

    SELECT
        i.code AS item_code,
        i.name,
        COALESCE(s.stock_now, 0) stock_now,
        COALESCE(sa.sold_qty, 0) sold_qty
    FROM items i
    LEFT JOIN stock s ON s.item_id=i.id
    LEFT JOIN sales sa ON sa.item_id=i.id
    WHERE
        COALESCE(s.stock_now, 0)>0
    ORDER BY
        CASE
            WHEN COALESCE(sa.sold_qty, 0) = 0
            THEN 999999
        ELSE
            COALESCE(s.stock_now, 0)/(sa.sold_qty/:days)
        END
    LIMIT :limit
    OFFSET :offset
    """

    params={
    **stock_ctx["params"],
    **sales_ctx["params"],
    "days":days,
    "limit":page_size,
    "offset":offset
    }

    rows= db.execute(text(sql),params).mappings().all()
    result=[]

    for r in rows:
        daily_use=0
        if days:
            daily_use=(r["sold_qty"] or 0)/days

        days_zero=999999

        if daily_use>0:
            days_zero=round(float(r["stock_now"] or 0)/daily_use, 1)

        result.append({
        "item_code": r["item_code"],
        "item_name": r["name"],
        "stock_now": float(r["stock_now"] or 0),
        "daily_use": round(daily_use, 2),
        "days_to_zero": days_zero
        })

    return{
        "page":page,
        "page_size":page_size,
        "rows":result
    }

def get_consumption_trend(payload, db):
    ctx = prepare_sales_context(payload)

    granularity, period_sql, order_sql = choose_granularity(
        payload.from_date,
        payload.to_date,
        "ih.invoice_date"
    )

    sql = f"""
        SELECT
            {period_sql} AS  period,
            {ctx['quantity']} AS quantity,
            {REVENUE_NET_SALES} AS revenue,
            {order_sql} AS sort_key
        {SALES_BASE_SQL}
        LEFT JOIN items i ON i.id = id.item_id
        {ctx['join_sql']}
        WHERE
            {ctx['where_sql']}
        GROUP BY
            period,
            sort_key
        ORDER BY
            sort_key
        """

    rows = db.execute(text(sql), ctx["params"]).fetchall()
    result = [dict(r._mapping) for r in rows]
    return {
        "granularity": granularity,
        "series": result
    }

