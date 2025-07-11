# Background task scheduler for automated sensor data collection, forecasting, data purging, and external weather API integration using APScheduler with configurable intervals.

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import logging
from app.workers.influx import InfluxWorker
from app.workers.forecasting import ForecastingWorker
from app.workers.purge import PurgeWorker
from app.workers.ext_weather import ExternalWeatherWorker
from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def setup_scheduler_jobs():
    """Configure and add all recurring jobs to the scheduler."""
    # Initialize workers
    influx_worker = InfluxWorker()
    forecast_worker = ForecastingWorker()
    purge_worker = PurgeWorker()
    weather_worker = ExternalWeatherWorker()

    # Schedule sensor data collection
    scheduler.add_job(
        influx_worker.collect_sensor_data,
        trigger=IntervalTrigger(seconds=settings.collection_interval),
        id="sensor_collection",
        name="Sensor Data Collection",
        replace_existing=True,
        misfire_grace_time=60  # Allow job to run up to 60s late
    )

    # Schedule forecasting
    scheduler.add_job(
        forecast_worker.generate_forecasts,
        trigger=IntervalTrigger(hours=1),
        id="forecasting",
        name="Generate Forecasts",
        replace_existing=True,
        misfire_grace_time=300 # 5 minutes
    )

    # Schedule data purging
    scheduler.add_job(
        purge_worker.purge_old_data,
        trigger=CronTrigger(hour=2, minute=0),
        id="data_purge",
        name="Data Purge",
        replace_existing=True,
        misfire_grace_time=600 # 10 minutes
    )

    # Schedule external weather data collection
    scheduler.add_job(
        weather_worker.fetch_weather_data,
        trigger=IntervalTrigger(minutes=15),
        id="weather_collection",
        name="External Weather Collection",
        replace_existing=True,
        misfire_grace_time=120 # 2 minutes
    )

async def start_scheduler():
    """Initialize and start the background task scheduler."""
    if not scheduler.running:
        setup_scheduler_jobs()
        scheduler.start()
        logger.info("Background scheduler started with all workers")
    else:
        logger.warning("Scheduler already running")

async def stop_scheduler():
    """Stop the background task scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")

def get_scheduler_status():
    """Get current scheduler and job status."""
    if not scheduler.running:
        return {"status": "stopped", "jobs": []}

    jobs = [
        {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]

    return {
        "status": "running",
        "jobs": jobs,
        "timezone": str(scheduler.timezone),
    }