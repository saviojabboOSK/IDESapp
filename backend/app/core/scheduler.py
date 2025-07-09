# Background task scheduler for automated sensor data collection, forecasting, data purging, and external weather API integration using APScheduler with configurable intervals.

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import asyncio
import logging
from datetime import datetime

from app.workers.influx import InfluxWorker
from app.workers.forecasting import ForecastingWorker
from app.workers.purge import PurgeWorker
from app.workers.ext_weather import ExternalWeatherWorker
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None

async def start_scheduler():
    """Initialize and start the background task scheduler."""
    global scheduler
    
    if scheduler is not None:
        logger.warning("Scheduler already running")
        return
    
    scheduler = AsyncIOScheduler()
    
    # Initialize workers
    influx_worker = InfluxWorker()
    forecast_worker = ForecastingWorker()
    purge_worker = PurgeWorker()
    weather_worker = ExternalWeatherWorker()
    
    # Schedule sensor data collection every 30 seconds
    scheduler.add_job(
        influx_worker.collect_sensor_data,
        trigger=IntervalTrigger(seconds=settings.collection_interval),
        id="sensor_collection",
        name="Sensor Data Collection",
        replace_existing=True
    )
    
    # Schedule forecasting every hour
    scheduler.add_job(
        forecast_worker.generate_forecasts,
        trigger=IntervalTrigger(hours=1),
        id="forecasting",
        name="Generate Forecasts",
        replace_existing=True
    )
    
    # Schedule data purging daily at 2 AM
    scheduler.add_job(
        purge_worker.purge_old_data,
        trigger=CronTrigger(hour=2, minute=0),
        id="data_purge",
        name="Data Purge",
        replace_existing=True
    )
    
    # Schedule external weather data collection every 15 minutes
    scheduler.add_job(
        weather_worker.fetch_weather_data,
        trigger=IntervalTrigger(minutes=15),
        id="weather_collection",
        name="External Weather Collection",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background scheduler started with all workers")

async def stop_scheduler():
    """Stop the background task scheduler."""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown(wait=True)
        scheduler = None
        logger.info("Background scheduler stopped")

def get_scheduler_status():
    """Get current scheduler and job status."""
    if scheduler is None:
        return {"status": "stopped", "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running",
        "jobs": jobs,
        "timezone": str(scheduler.timezone)
    }