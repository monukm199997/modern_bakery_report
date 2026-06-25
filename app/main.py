from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.reports.filters.filters import router as filters

from app.reports.sales_report.routes.company_level_dashboard import router as company_level_dashboard
from app.reports.sales_report.routes.region_level_dashboard import router as region_level_dashboard
from app.reports.sales_report.routes.tableview import router as sales_tableview
from app.reports.sales_report.routes.export import router as sales_report_export
from app.reports.sales_report.routes.group_sale_export import router as group_sale_export
from app.reports.sales_report.routes.group_sales_tableview import router as group_sale_tableview

from app.reports.customer_sales_report.routes.dashboard import router as customer_dashboard
from app.reports.customer_sales_report.routes.tableview import router as customer_tableview
from app.reports.customer_sales_report.routes.export import router as customer_export

from app.reports.customer_dashboard.routes.customer_dashboard import router as customer_primary_dashboard
from app.reports.sales_dashboard.routes.sales_dashboard import router as sales_primary_dashboard

from app.reports.target_commison_report.routes.target_commison_export import router as target_commison_export
from app.reports.target_commison_report.routes.target_commison_table import router as target_commison_table

from app.reports.sales_comparison_report.routes.sales_comparison_table import router as sales_comparison_table
from app.reports.sales_comparison_report.routes.sales_comparison_export import router as sales_comparison_export
from app.reports.sales_comparison_report.routes.sales_comparison_dashboard import router as sales_comparison_dashboard

from app.reports.vehicles_report.routes.vehicles_tableview import router as vehicles_tableview
from app.reports.vehicles_report.routes.vehicles_export import router as vehicles_export
from app.reports.vehicles_report.routes.vehicles_dashboard import router as vehicles_dashboard

from app.reports.item_dashboard.routes.item_dash import router as item_dashboard

from app.reports.visit_report.routes.visit_tableview import router as visit_tableview
from app.reports.visit_report.routes.visit_export import router as visit_export


app = FastAPI(title="Modern Bakery Reports API")

app.include_router(filters, prefix="/api/filters")

app.include_router(company_level_dashboard, prefix="/api/sales-report") 
app.include_router(region_level_dashboard, prefix="/api/sales-report") 
app.include_router(sales_tableview, prefix="/api/sales-report") 
app.include_router(sales_report_export,prefix="/api/sales-report")
app.include_router(group_sale_export,prefix="/api/sales-report")
app.include_router(group_sale_tableview,prefix="/api/sales-report")

app.include_router(customer_dashboard, prefix="/api/customer-sales-report")
app.include_router(customer_tableview, prefix="/api/customer-sales-report")
app.include_router(customer_export, prefix="/api/customer-sales-report")

app.include_router(customer_primary_dashboard, prefix="/api/customer-dashboard")
app.include_router(sales_primary_dashboard, prefix="/api/sales-dashboard")

app.include_router(target_commison_export, prefix="/api/target-commison-report")
app.include_router(target_commison_table, prefix="/api/target-commison-report")

app.include_router(sales_comparison_table, prefix="/api/sales-comparison-report")
app.include_router(sales_comparison_export, prefix="/api/sales-comparison-report")
app.include_router(sales_comparison_dashboard, prefix="/api/sales-comparison-report")

app.include_router(vehicles_tableview, prefix="/api/vehicles-report")
app.include_router(vehicles_export, prefix="/api/vehicles-report")
app.include_router(vehicles_dashboard, prefix="/api/vehicles-report")

app.include_router(item_dashboard, prefix="/api/item-dashboard")

app.include_router(visit_tableview, prefix="/api/visit_report")
app.include_router(visit_export, prefix="/api/visit_report")




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )
