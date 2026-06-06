from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.dependencies.auth import get_current_user
from app.reports.vehicles_report.schemas.vehicles_schema import VehiclesRequest
from app.core.database import get_db
from app.reports.vehicles_report.utils.vehicles_helper import prepare_dashboard_context

router = APIRouter(tags=["vehicles_report"], dependencies=[Depends(get_current_user)])

VALID_TRIP = """
    tt.start_odometer IS NOT NULL
    AND tt.end_odometer   IS NOT NULL
    AND tt.end_odometer  >= tt.start_odometer
"""


# 1. KPI summary — the four top tiles + bad-data breakdown
@router.post("/dashboard/kpi-summary")
def kpi_summary(payload: VehiclesRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            COUNT(*) AS total_trips,
            COUNT(*) FILTER (WHERE {VALID_TRIP}) AS valid_trips,
            COALESCE(SUM(tt.end_odometer - tt.start_odometer)
                     FILTER (WHERE {VALID_TRIP}), 0) AS total_distance,
            COUNT(*) FILTER (WHERE tt.end_odometer IS NULL) AS open_trips
        FROM tbl_trip tt
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
    """
    row = db.execute(text(query), ctx["params"]).mappings().first()
    data = dict(row) if row else {}
    return data


@router.post("/dashboard/distance-trend")
def distance_trend(payload: VehiclesRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        SELECT
            tt.trip_date,
            COUNT(*) AS valid_trip_count,
            SUM(tt.end_odometer - tt.start_odometer) AS total_distance
        FROM tbl_trip tt
        {ctx['join_sql']}
        WHERE {ctx['where_sql']}
          AND {VALID_TRIP}
        GROUP BY tt.trip_date
        ORDER BY tt.trip_date
    """
    rows = db.execute(text(query), ctx["params"]).mappings().all()
    return [dict(r) for r in rows]


@router.post("/dashboard/distance-per-vehicle")
def distance_per_vehicle(payload: VehiclesRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        WITH trip_agg AS (
            SELECT
                tt.vehicle_id,
                COUNT(*) AS valid_trip_count,
                SUM(tt.end_odometer - tt.start_odometer) AS total_distance
            FROM tbl_trip tt
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
              AND {VALID_TRIP}
            GROUP BY tt.vehicle_id
        )
        SELECT
            v.id AS vehicle_id,
            v.vehicle_code,
            v.number_plat,
            COALESCE(ta.valid_trip_count, 0) AS valid_trip_count,
            COALESCE(ta.total_distance, 0)   AS total_distance
        FROM tbl_vehicle v
        LEFT JOIN trip_agg ta ON ta.vehicle_id = v.id
        ORDER BY total_distance DESC
    """
    rows = db.execute(text(query), ctx["params"]).mappings().all()
    return [dict(r) for r in rows]

@router.post("/dashboard/distance-per-route")
def distance_per_route(payload: VehiclesRequest, db: Session = Depends(get_db)):
    ctx = prepare_dashboard_context(payload)
    query = f"""
        WITH trip_agg AS (
            SELECT
                tt.vehicle_id,
                COUNT(*) AS valid_trip_count,
                SUM(tt.end_odometer - tt.start_odometer) AS total_distance
            FROM tbl_trip tt
            {ctx['join_sql']}
            WHERE {ctx['where_sql']}
              AND {VALID_TRIP}
            GROUP BY tt.vehicle_id
        )
        SELECT
            r.id AS route_id,
            r.route_name,
            v.vehicle_code,
            COALESCE(ta.valid_trip_count, 0) AS valid_trip_count,
            COALESCE(ta.total_distance, 0)   AS total_distance
        FROM tbl_route r
        LEFT JOIN tbl_vehicle v ON v.id = r.vehicle_id
        LEFT JOIN trip_agg ta   ON ta.vehicle_id = r.vehicle_id
        ORDER BY total_distance DESC
    """
    rows = db.execute(text(query), ctx["params"]).mappings().all()
    return [dict(r) for r in rows]