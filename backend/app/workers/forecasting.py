# Forecasting worker that analyzes historical sensor data patterns to generate predictive models for temperature, humidity, CO2, and other metrics with accuracy tracking and visualization.

import asyncio
import json
import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.core.config import settings

logger = logging.getLogger(__name__)

class ForecastingWorker:
    """Worker for generating sensor data forecasts using SARIMAX models."""
    
    def __init__(self):
        self.connection_manager = None
        self.models = {} # Cache for trained models

    async def generate_forecasts(self):
        """Generate forecasts for all available sensor metrics."""
        try:
            logger.info("Starting forecast generation...")
            historical_data = await self._load_historical_data()
            if not historical_data:
                logger.warning("No historical data available for forecasting.")
                return

            metrics_to_forecast = ["temperature", "humidity", "co2"]
            tasks = [self._generate_metric_forecast(metric, historical_data[metric]) for metric in metrics_to_forecast if metric in historical_data]
            results = await asyncio.gather(*tasks)

            forecasts = {res['metric']: res for res in results if res}
            
            if forecasts:
                await self._save_forecasts(forecasts)
                await self._broadcast_forecasts(forecasts)
                logger.info(f"Forecast generation completed for {len(forecasts)} metrics.")
            
        except Exception as e:
            logger.error(f"Forecast generation failed: {e}", exc_info=True)
    
    async def _load_historical_data(self) -> Dict[str, List[float]]:
        """Load and combine historical data from the last 4 weeks."""
        data_dir = Path(settings.data_dir)
        if not data_dir.exists():
            return {}

        # Efficiently find unique weekly files for the last 4 weeks
        files_to_load = set()
        for i in range(28):
            date = datetime.utcnow() - timedelta(days=i)
            week_start = date - timedelta(days=date.weekday())
            filename = f"sensors_{week_start.strftime('%Y_%m_%d')}.json"
            files_to_load.add(data_dir / filename)

        all_data = []
        for file_path in files_to_load:
            if file_path.exists():
                try:
                    with open(file_path, 'r') as f:
                        all_data.append(json.load(f))
                except (IOError, json.JSONDecodeError) as e:
                    logger.warning(f"Failed to load {file_path}: {e}")
        
        if not all_data:
            return {}

        # Combine and sort data
        combined = {key: [] for key in all_data[0].keys()}
        for data_part in all_data:
            for key in combined.keys():
                combined[key].extend(data_part.get(key, []))
        
        if not combined.get("timestamps"):
            return {}

        # Sort by timestamp
        sorted_indices = np.argsort(combined["timestamps"])
        for key in combined.keys():
            combined[key] = np.array(combined[key])[sorted_indices].tolist()

        return combined
    
    async def _generate_metric_forecast(self, metric: str, values: List[float]) -> Optional[Dict[str, Any]]:
        """Generate forecast for a specific metric using a SARIMAX model."""
        if len(values) < 50: # SARIMAX needs a reasonable amount of data
            return None
        
        try:
            data = np.asarray(values, dtype=float)
            
            # Using a simple SARIMAX model (seasonal ARIMA)
            # These parameters (p,d,q)(P,D,Q,s) would ideally be tuned per metric
            model = SARIMAX(data, order=(1, 1, 1), seasonal_order=(1, 1, 1, 24))
            model_fit = model.fit(disp=False)
            
            # Forecast 48 hours ahead
            forecast = model_fit.get_forecast(steps=48)
            forecast_values = forecast.predicted_mean.tolist()
            conf_int = forecast.conf_int()
            
            now = datetime.utcnow()
            forecast_timestamps = [(now + timedelta(hours=i+1)).isoformat() for i in range(48)]
            
            return {
                "metric": metric,
                "timestamps": forecast_timestamps,
                "values": forecast_values,
                "upper_bound": conf_int.iloc[:, 1].tolist(),
                "lower_bound": conf_int.iloc[:, 0].tolist(),
                "model": "SARIMAX",
                "generated_at": now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate forecast for {metric}: {e}", exc_info=True)
            return None
    
    async def _save_forecasts(self, forecasts: Dict[str, Any]):
        """Save generated forecasts to a single JSON file."""
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(exist_ok=True)
        forecast_file = data_dir / "forecasts.json"
        
        try:
            existing_forecasts = {}
            if forecast_file.exists():
                with open(forecast_file, 'r') as f:
                    existing_forecasts = json.load(f)
            
            existing_forecasts.update(forecasts)
            existing_forecasts["last_updated"] = datetime.utcnow().isoformat()
            
            with open(forecast_file, 'w') as f:
                json.dump(existing_forecasts, f, indent=2)
            
            logger.debug("Forecasts saved successfully.")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to save forecasts: {e}", exc_info=True)
    
    async def _broadcast_forecasts(self, forecasts: Dict[str, Any]):
        """Broadcast forecast updates via WebSocket."""
        if self.connection_manager:
            try:
                await self.connection_manager.broadcast_forecast_update(forecasts)
            except Exception as e:
                logger.error(f"Failed to broadcast forecasts: {e}", exc_info=True)
    
    def set_connection_manager(self, manager):
        """Set the WebSocket connection manager for broadcasting."""
        self.connection_manager = manager
    
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status information."""
        return {
            "worker": "forecasting",
            "status": "running",
            "models_in_use": list(self.models.keys()),
        }