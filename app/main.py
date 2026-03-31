from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.reports.sales_report.routes.company_level_dashboard import router as company_level_dashboard
from app.reports.sales_report.routes.region_level_dashboard import router as region_level_dashboard
from app.reports.sales_report.routes.tableview import router as sales_tableview
from app.reports.sales_report.routes.export import router as sales_report_export
from app.reports.filters.filters import router as filters

app = FastAPI(title="Modern Bakery Reports API")

app.include_router(company_level_dashboard, prefix="/api/sales-report") 
app.include_router(region_level_dashboard, prefix="/api/sales-report") 
app.include_router(sales_tableview, prefix="/api/sales-report") 
app.include_router(sales_report_export,prefix="/api/sales-report")
app.include_router(filters, prefix="/api/filters")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )
