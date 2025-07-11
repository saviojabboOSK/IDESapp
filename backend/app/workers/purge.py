# Data purge worker for automatic cleanup of old sensor snapshots based on configurable retention policies, maintaining optimal storage usage while preserving critical historical data.

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import shutil
import os
from typing import Optional, Dict, List, Any
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

class PurgeWorker:
    """Worker for cleaning up old sensor data files."""

    def __init__(self):
        self.data_dir = Path(settings.data_dir)
        self.archive_dir = self.data_dir / "archive"
        self.data_dir.mkdir(exist_ok=True)
        self.archive_dir.mkdir(exist_ok=True)

    async def purge_old_data(self):
        """Remove sensor data files older than the retention policy."""
        try:
            logger.info("Starting data purge process...")
            cutoff_date = datetime.utcnow() - timedelta(weeks=settings.data_retention_weeks)
            
            files_to_process = list(self.data_dir.glob("sensors_*.json"))
            
            tasks = [self.process_file_for_purge(file_path, cutoff_date) for file_path in files_to_process]
            results = await asyncio.gather(*tasks)
            
            purged_files_info = [res for res in results if res]
            
            if not purged_files_info:
                logger.info("No old data to purge.")
                return

            await self._archive_and_delete(purged_files_info)
            
            logger.info(f"Data purge completed: {len(purged_files_info)} files removed.")

        except Exception as e:
            logger.error(f"Data purge failed: {e}", exc_info=True)

    async def process_file_for_purge(self, file_path: Path, cutoff_date: datetime) -> Optional[Dict]:
        """Check if a file is old enough to be purged and return its info."""
        try:
            date_str = file_path.stem.replace("sensors_", "")
            file_date = datetime.strptime(date_str, "%Y_%m_%d")
            
            if file_date < cutoff_date:
                return {"path": file_path, "date": file_date, "size": file_path.stat().st_size}
        except (ValueError, FileNotFoundError) as e:
            logger.warning(f"Could not process file {file_path}: {e}")
        return None

    async def _archive_and_delete(self, files_to_purge: List[Dict]):
        """Archive summaries and then delete the original files."""
        archive_data = {
            "archive_date": datetime.utcnow().isoformat(),
            "purged_files_summary": [],
        }

        for file_info in files_to_purge:
            file_path = file_info["path"]
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                summary = self._create_summary(file_path.name, file_info, data)
                archive_data["purged_files_summary"].append(summary)
                
                # After successful summary, delete the file
                os.remove(file_path)
                logger.debug(f"Purged: {file_path.name}")

            except (IOError, json.JSONDecodeError, FileNotFoundError) as e:
                logger.error(f"Failed to process or delete {file_path}: {e}", exc_info=True)
        
        if archive_data["purged_files_summary"]:
            archive_file = self.archive_dir / f"archive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            with open(archive_file, 'w') as f:
                json.dump(archive_data, f, indent=2, default=str)
            logger.info(f"Archived summary for {len(files_to_purge)} files.")

    def _create_summary(self, filename: str, file_info: Dict, data: Dict) -> Dict:
        """Create a statistical summary for a single data file."""
        summary = {
            "filename": filename,
            "date": file_info["date"],
            "size": file_info["size"],
            "metrics": {},
        }
        for metric, values in data.items():
            if isinstance(values, list) and np.issubdtype(np.array(values).dtype, np.number):
                summary["metrics"][metric] = {
                    "min": np.min(values),
                    "max": np.max(values),
                    "avg": np.mean(values),
                }
        return summary

    async def get_storage_info(self) -> Dict[str, Any]:
        """Get current storage usage information."""
        try:
            total_size = sum(f.stat().st_size for f in self.data_dir.rglob('*') if f.is_file())
            disk_usage = shutil.disk_usage(self.data_dir)
            return {
                "data_directory": str(self.data_dir),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "disk_free_gb": round(disk_usage.free / (1024**3), 2),
                "retention_policy_weeks": settings.data_retention_weeks,
            }
        except Exception as e:
            logger.error(f"Failed to get storage info: {e}", exc_info=True)
            return {"error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "purge",
            "status": "idle", # or "running" if in the middle of a purge
            "retention_weeks": settings.data_retention_weeks,
            "data_directory": str(self.data_dir),
        }