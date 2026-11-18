"""NEXORA ERP — Celery & Redis Background Processing Pipeline."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.ai_service import (
    run_business_anomaly_detection,
    run_inventory_demand_forecast,
    run_sales_revenue_forecast,
)

celery_app = Celery(
    "nexora_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.default_timezone,
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


@celery_app.task(name="nexora.tasks.run_demand_forecast", bind=True, max_retries=2)
def task_run_demand_forecast(self, organization_id: str, model_choice: str = "XGBOOST") -> dict:
    """Idempotent background task to compute inventory demand forecasts."""
    with SessionLocal() as db:
        result = run_inventory_demand_forecast(
            db,
            organization_id=organization_id,
            model_choice=model_choice,
        )
        return {
            "status": "COMPLETED",
            "forecast_run_id": result["forecast_run_id"],
            "summary": result["summary"],
        }


@celery_app.task(name="nexora.tasks.run_sales_forecast", bind=True, max_retries=2)
def task_run_sales_forecast(self, organization_id: str, horizon_months: int = 6) -> dict:
    """Idempotent background task to compute monthly sales revenue forecasts."""
    with SessionLocal() as db:
        result = run_sales_revenue_forecast(
            db,
            organization_id=organization_id,
            horizon_months=horizon_months,
        )
        return {
            "status": "COMPLETED",
            "next_month_predicted_revenue": result["next_month_predicted_revenue"],
        }


@celery_app.task(name="nexora.tasks.run_anomaly_scan", bind=True, max_retries=2)
def task_run_anomaly_scan(self, organization_id: str) -> dict:
    """Scheduled background task to detect operational and financial anomalies."""
    with SessionLocal() as db:
        result = run_business_anomaly_detection(db, organization_id=organization_id)
        return {
            "status": "COMPLETED",
            "total_anomalies": result["total_anomalies"],
            "new_anomalies_detected": result["new_anomalies_detected"],
        }
