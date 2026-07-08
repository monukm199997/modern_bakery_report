
from collections import OrderedDict

SALES_DOC_TYPES = (
    "'ZVCS','YDO','YDI','YSCR','ZSCS','ZFCD','YFCD','YSDR'"
)


DRILL_DOWN_MAP = OrderedDict({

    "customer": {
        "select": [
            "ac.osa_code AS customer_code",
            "ac.name AS customer_name",
        ],
        "group_by": [
            "ac.osa_code",
            "ac.name",
        ],
        "order_by": [
            "ac.name",
        ],
    },

    "salesman": {
        "select": [
            "sm.osa_code AS salesman_code",
            "sm.name AS salesman_name",
        ],
        "group_by": [
            "sm.osa_code",
            "sm.name",
        ],
        "order_by": [
            "sm.name",
        ],
    },

    "channel": {
        "select": [
            """
            oc.outlet_channel_code AS channel_code,
            oc.outlet_channel AS channel
            """
        ],
        "group_by": [
            "oc.outlet_channel_code",
            "oc.outlet_channel",
        ],
        "order_by": [
            "oc.outlet_channeL",
        ],
    },

})


HIERARCHY_MAP = {

    "region": {
        "select": [
            "rg.region_code AS region_code",
            "rg.region_name AS region_name",
        ],
        "group_by": [
            "rg.region_code",
            "rg.region_name",
        ],
        "order_by": [
            "rg.region_code",
        ],
    },

    "route": {
        "select": [
            "rt.route_code AS route_code",
            "rt.route_name AS route_name",
        ],
        "group_by": [
            "rt.route_code",
            "rt.route_name",
        ],
        "order_by": [
            "rt.route_code",
        ],
    },

}



ITEM_COLUMNS = {

    "select": [
        "ic.category_name AS category",
        "i.code AS item_code",
        "i.name AS item_name",
        "COUNT(DISTINCT sdh.customer_id) AS customer_count",
    ],

    "group_by": [
        "ic.category_name",
        "i.code",
        "i.name",
    ],

    "order_by": [
        "ic.category_name",
        "i.code",
    ],

}



BASE_FROM = """
FROM sales_documents_header sdh
JOIN sales_documents_detail sdd ON sdd.header_id = sdh.id
JOIN items i ON i.id = sdd.item_id
LEFT JOIN item_categories ic ON ic.id = i.category_id
LEFT JOIN agent_customers ac ON ac.id = sdh.customer_id
LEFT JOIN tbl_route rt ON rt.id = sdh.route_id
LEFT JOIN tbl_region rg ON rg.id = rt.region_id
LEFT JOIN salesman sm ON sm.id = sdh.salesman_id
LEFT JOIN outlet_channel oc ON oc.id = ac.outlet_channel_id

"""