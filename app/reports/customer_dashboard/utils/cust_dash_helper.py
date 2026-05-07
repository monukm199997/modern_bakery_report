from app.reports.customer_dashboard.schemas.schemas import CustomerDashboardRequest


def get_invoice_date(filters:CustomerDashboardRequest):
    where_fragments = []
    params = {}

    where_fragments.append("ih.invoice_date BETWEEN :from_date AND :to_date")
    params["from_date"] = filters.from_date
    params["to_date"] = filters.to_date

    return where_fragments, params
