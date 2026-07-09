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

from app.reports.team_master_report.routes.team_master_tableview import router as team_master_tableview
from app.reports.team_master_report.routes.team_master_export import router as team_master_export

from app.reports.customer_master_report.routes.customer_master_tableview import router as customer_master_tableview
from app.reports.customer_master_report.routes.customer_master_export import router as customer_master_export

from app.reports.sales_new_report.routes.sales_tableview import router as sales_new_tableview
from app.reports.sales_new_report.routes.sales_export import router as sales_new_export
from app.reports.sales_new_report.routes.sales_pivote_export import router as sales_pivote_export

from app.reports.vehicles_permit_report.routes.vehicles_permit_tableview import router as vehicles_permit_tableview
from app.reports.vehicles_permit_report.routes.vehicles_permit_export import router as vehicles_permit_export

from app.reports.item_loading_report.routes.item_loading_tableview import router as item_loading_tableview
from app.reports.item_loading_report.routes.item_loading_export import router as item_loading_export

from app.reports.numerical_distribution_report.routes.numerical_distribution_tableview import router as numerical_distribution_tableview
from app.reports.numerical_distribution_report.routes.numerical_distribution_export import router as numerical_distribution_export

from app.reports.group_level_report.routes.group_level_tableview import router as group_level_tableview
from app.reports.group_level_report.routes.group_level_export import router as group_level_export

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

app.include_router(team_master_tableview, prefix="/api/team-master-report")
app.include_router(team_master_export, prefix="/api/team-master-report")

app.include_router(customer_master_tableview, prefix="/api/customer_master_report")
app.include_router(customer_master_export, prefix="/api/customer_master_report")

app.include_router(sales_new_tableview, prefix="/api/sales-new-report")
app.include_router(sales_new_export, prefix="/api/sales-new-report")
app.include_router(sales_pivote_export, prefix="/api/sales-new-report")

app.include_router(vehicles_permit_tableview, prefix="/api/vehicles_permit_report")
app.include_router(vehicles_permit_export, prefix="/api/vehicles_permit_report")

app.include_router(item_loading_tableview, prefix="/api/item-loading-report")
app.include_router(item_loading_export, prefix="/api/item-loading-report")

app.include_router(numerical_distribution_tableview, prefix="/api/numerical_distribution_report")
app.include_router(numerical_distribution_export, prefix="/api/numerical_distribution_report")

app.include_router(group_level_tableview, prefix="/api/group_level_report")
app.include_router(group_level_export, prefix="/api/group_level_report")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )
