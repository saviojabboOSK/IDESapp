# Data purge worker for automatic cleanup of old sensor snapshots based on configurable retention policies, maintaining optimal storage usage while preserving critical historical data.

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import json
import shutil

from app.core.config import settings

logger = logging.getLogger(__name__)

class PurgeWorker:
    """Worker for cleaning up old sensor data files."""
    
    def __init__(self):
        self.last_purge_time = datetime.now()
        
    async def purge_old_data(self):
        """Remove sensor data files older than retention policy."""
        try:
            logger.info("Starting data purge process...")
            
            data_dir = Path(settings.data_dir)
            if not data_dir.exists():
                logger.info("Data directory does not exist, nothing to purge")
                return
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(weeks=settings.data_retention_weeks)
            
            # Find files to purge
            files_to_purge = []
            total_size_before = 0
            
            for file_path in data_dir.glob("sensors_*.json"):
                try:
                    # Extract date from filename
                    filename = file_path.name
                    date_str = filename.replace("sensors_", "").replace(".json", "")
                    file_date = datetime.strptime(date_str, "%Y_%m_%d")
                    
                    file_size = file_path.stat().st_size
                    total_size_before += file_size
                    
                    if file_date < cutoff_date:
                        files_to_purge.append({
                            "path": file_path,
                            "date": file_date,
                            "size": file_size
                        })
                        
                except ValueError:
                    logger.warning(f"Could not parse date from filename: {filename}")
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")
            
            # Archive important data before deletion
            archived_data = await self._archive_critical_data(files_to_purge)
            
            # Delete old files
            purged_files = 0
            purged_size = 0
            
            for file_info in files_to_purge:
                try:
                    file_path = file_info["path"]
                    file_size = file_info["size"]
                    
                    file_path.unlink()
                    purged_files += 1
                    purged_size += file_size
                    
                    logger.debug(f"Purged: {file_path.name} ({file_size} bytes)")
                    
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")
            
            # Clean up forecast files
            await self._cleanup_old_forecasts()
            
            # Update purge statistics
            await self._save_purge_stats(purged_files, purged_size, total_size_before)
            
            self.last_purge_time = datetime.now()
            
            logger.info(f"Data purge completed: {purged_files} files, {purged_size / 1024 / 1024:.2f} MB freed")
            
        except Exception as e:
            logger.error(f"Data purge failed: {e}")
    
    async def _archive_critical_data(self, files_to_purge: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Archive summary statistics before purging data."""
        archive_data = {
            "archive_date": datetime.now().isoformat(),
            "retention_weeks": settings.data_retention_weeks,
            "purged_files": [],
            "summary_statistics": {}
        }
        
        try:
            data_dir = Path(settings.data_dir)
            archive_dir = data_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            
            for file_info in files_to_purge:
                file_path = file_info["path"]
                
                try:
                    # Load data to calculate summary statistics
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    # Calculate basic statistics for each metric
                    file_summary = {
                        "filename": file_path.name,
                        "date": file_info["date"].isoformat(),
                        "size": file_info["size"],
                        "data_points": len(data.get("timestamps", [])),
                        "metrics": {}
                    }
                    
                    for metric, values in data.items():
                        if metric != "timestamps" and isinstance(values, list) and values:
                            try:
                                file_summary["metrics"][metric] = {
                                    "count": len(values),
                                    "min": min(values),
                                    "max": max(values),
                                    "avg": sum(values) / len(values),
                                    "first": values[0],
                                    "last": values[-1]
                                }
                            except (TypeError, ValueError):
                                pass  # Skip non-numeric data
                    
                    archive_data["purged_files"].append(file_summary)
                    
                except Exception as e:
                    logger.warning(f"Could not archive data from {file_path}: {e}")
            
            # Save archive data
            archive_file = archive_dir / f"archive_{datetime.now().strftime('%Y_%m_%d')}.json"
            with open(archive_file, 'w') as f:
                json.dump(archive_data, f, indent=2)
            
            logger.info(f"Archived summary data for {len(files_to_purge)} files")
            
        except Exception as e:
            logger.error(f"Failed to archive critical data: {e}")
        
        return archive_data
    
    async def _cleanup_old_forecasts(self):
        """Clean up old forecast files."""
        try:
            data_dir = Path(settings.data_dir)
            
            # Clean up forecasts older than 1 week
            cutoff_time = datetime.now() - timedelta(weeks=1)
            
            forecast_file = data_dir / "forecasts.json"
            if forecast_file.exists():
                try:
                    with open(forecast_file, 'r') as f:
                        forecasts = json.load(f)
                    
                    # Remove old forecast entries
                    cleaned_forecasts = {}
                    for metric, forecast_data in forecasts.items():
                        if metric == "last_updated":
                            cleaned_forecasts[metric] = forecast_data
                            continue
                            
                        if isinstance(forecast_data, dict) and "generated_at" in forecast_data:
                            try:
                                generated_time = datetime.fromisoformat(forecast_data["generated_at"])
                                if generated_time > cutoff_time:
                                    cleaned_forecasts[metric] = forecast_data
                            except ValueError:
                                pass  # Skip invalid timestamps
                    
                    # Save cleaned forecasts
                    with open(forecast_file, 'w') as f:
                        json.dump(cleaned_forecasts, f, indent=2)
                    
                    logger.debug("Cleaned old forecasts")
                    
                except Exception as e:
                    logger.warning(f"Failed to clean forecasts: {e}")
            
        except Exception as e:
            logger.error(f"Forecast cleanup failed: {e}")
    
    async def _save_purge_stats(self, files_count: int, size_freed: int, total_size_before: int):
        """Save purge statistics for monitoring."""
        try:
            data_dir = Path(settings.data_dir)
            stats_file = data_dir / "purge_stats.json"
            
            # Load existing stats
            stats = {"purge_history": []}
            if stats_file.exists():
                try:
                    with open(stats_file, 'r') as f:
                        stats = json.load(f)
                except Exception:
                    pass
            
            # Add new purge record
            purge_record = {
                "timestamp": self.last_purge_time.isoformat(),
                "files_purged": files_count,
                "size_freed_bytes": size_freed,
                "size_freed_mb": round(size_freed / 1024 / 1024, 2),
                "total_size_before_bytes": total_size_before,
                "retention_weeks": settings.data_retention_weeks
            }
            
            stats["purge_history"].append(purge_record)
            
            # Keep only last 50 purge records
            stats["purge_history"] = stats["purge_history"][-50:]
            stats["last_purge"] = purge_record
            
            # Save updated stats
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save purge stats: {e}")
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """Get current storage usage information."""
        try:
            data_dir = Path(settings.data_dir)
            if not data_dir.exists():
                return {"error": "Data directory does not exist"}
            
            # Calculate total data directory size
            total_size = 0
            file_count = 0
            files_by_type = {}
            
            for file_path in data_dir.rglob("*"):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    total_size += file_size
                    file_count += 1
                    
                    file_type = file_path.suffix or "no_extension"
                    if file_type not in files_by_type:
                        files_by_type[file_type] = {"count": 0, "size": 0}
                    
                    files_by_type[file_type]["count"] += 1
                    files_by_type[file_type]["size"] += file_size
            
            # Get disk usage
            disk_usage = shutil.disk_usage(data_dir)
            
            return {
                "data_directory": str(data_dir),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "file_count": file_count,
                "files_by_type": files_by_type,
                "disk_usage": {
                    "total_gb": round(disk_usage.total / 1024 / 1024 / 1024, 2),
                    "used_gb": round(disk_usage.used / 1024 / 1024 / 1024, 2),
                    "free_gb": round(disk_usage.free / 1024 / 1024 / 1024, 2)
                },
                "retention_policy": f"{settings.data_retention_weeks} weeks"
            }
            
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}")
            return {"error": str(e)}
    
    async def force_purge_older_than(self, days: int) -> Dict[str, Any]:
        """Force purge data older than specified days (admin function)."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            data_dir = Path(settings.data_dir)
            
            if not data_dir.exists():
                return {"error": "Data directory does not exist"}
            
            purged_files = []
            total_size = 0
            
            for file_path in data_dir.glob("sensors_*.json"):
                try:
                    filename = file_path.name
                    date_str = filename.replace("sensors_", "").replace(".json", "")
                    file_date = datetime.strptime(date_str, "%Y_%m_%d")
                    
                    if file_date < cutoff_date:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        
                        purged_files.append({
                            "filename": filename,
                            "date": file_date.isoformat(),
                            "size": file_size
                        })
                        total_size += file_size
                        
                except Exception as e:
                    logger.error(f"Error in force purge of {file_path}: {e}")
            
            return {
                "files_purged": len(purged_files),
                "total_size_freed": total_size,
                "purged_files": purged_files,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Force purge failed: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "purge",
            "status": "running",
            "last_purge": self.last_purge_time.isoformat(),
            "retention_weeks": settings.data_retention_weeks,
            "data_directory": settings.data_dir
        }