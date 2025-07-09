# Local LLM service implementation for Ollama or similar self-hosted language models with HTTP API interface for privacy-focused sensor data analysis without external dependencies.

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from app.llm.base import LLMService

logger = logging.getLogger(__name__)

class LocalLLMService(LLMService):
    """Local LLM service implementation for Ollama and similar services."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2", **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout
            )
        return self.session
    
    async def generate_response(self, prompt: str, **kwargs) -> str:
        """Generate response using local LLM service."""
        try:
            session = await self._get_session()
            
            # Prepare request payload for Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 1000),
                    "top_p": kwargs.get("top_p", 0.9)
                }
            }
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result.get("response", "No response generated")
                else:
                    error_text = await response.text()
                    logger.error(f"Local LLM error {response.status}: {error_text}")
                    return f"Error: Local LLM service returned status {response.status}"
                    
        except aiohttp.ClientError as e:
            logger.error(f"Local LLM connection error: {e}")
            return f"Error: Could not connect to local LLM service - {str(e)}"
        except Exception as e:
            logger.error(f"Local LLM unexpected error: {e}")
            return f"Error: Unexpected error in local LLM service - {str(e)}"
    
    async def check_availability(self) -> bool:
        """Check if local LLM service is available."""
        try:
            session = await self._get_session()
            
            # Try to get version/health info
            async with session.get(f"{self.base_url}/api/version") as response:
                if response.status == 200:
                    self.is_available = True
                    return True
                    
            # Fallback: try a simple generate request
            test_payload = {
                "model": self.model,
                "prompt": "Hello",
                "stream": False,
                "options": {"max_tokens": 5}
            }
            
            async with session.post(
                f"{self.base_url}/api/generate",
                json=test_payload
            ) as response:
                self.is_available = response.status == 200
                return self.is_available
                
        except Exception as e:
            logger.warning(f"Local LLM availability check failed: {e}")
            self.is_available = False
            return False
    
    async def list_available_models(self) -> List[str]:
        """Get list of available models from local service."""
        try:
            session = await self._get_session()
            
            async with session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model.get("name", "") for model in data.get("models", [])]
                    return [m for m in models if m]  # Filter empty names
                    
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            
        return [self.model]  # Return current model as fallback
    
    async def switch_model(self, model_name: str) -> bool:
        """Switch to different model."""
        old_model = self.model
        self.model = model_name
        
        # Test if new model works
        if await self.check_availability():
            logger.info(f"Switched to model: {model_name}")
            return True
        else:
            # Revert to old model
            self.model = old_model
            logger.error(f"Failed to switch to model: {model_name}")
            return False
    
    async def analyze_sensor_data(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """Enhanced sensor data analysis with local LLM."""
        # Add context for better local LLM understanding
        enhanced_query = f"""
As an expert in indoor environmental monitoring, {query}

Context: You are analyzing data from an Indoor Digital Environment System (IDES) that monitors building conditions.

Sensor Data Summary:
{self._format_sensor_data(data)}

Please provide a concise, practical response focusing on:
1. Direct answer to the question
2. Any concerning trends or anomalies
3. Recommended actions if applicable

Keep technical language simple and actionable.
"""
        
        try:
            response = await self.generate_response(enhanced_query)
            return {
                "analysis": response,
                "status": "success",
                "model": self.model,
                "service": "local"
            }
        except Exception as e:
            return {
                "analysis": f"Local analysis failed: {str(e)}",
                "status": "error",
                "model": self.model,
                "service": "local"
            }
    
    async def close(self):
        """Close HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            
    def get_service_info(self) -> Dict[str, Any]:
        """Get service configuration information."""
        return {
            "service_type": "local",
            "base_url": self.base_url,
            "model": self.model,
            "is_available": self.is_available,
            "description": "Local LLM service (Ollama compatible)"
        }