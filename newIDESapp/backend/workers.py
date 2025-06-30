"""
backend/workers.py

This module handles the main business logic for processing user queries and generating
intelligent responses. It serves as the intermediary between user input, database queries,
and LLM-generated responses.

Main responsibilities:
- Parse and analyze user prompts to extract intent and parameters
- Handle confirmation responses ("yes", "sure") by recycling previous queries
- Extract relevant metrics and time windows from natural language
- Fetch data from InfluxDB when needed
- Generate summaries of retrieved data
- Coordinate with LLM service to produce intelligent responses

Key Functions:
- analyze_prompt(): Main entry point that processes user input and chat history
- _extract_query(): Extracts metrics and time windows from natural language
- _summarise(): Creates concise summaries of time series data
"""

import re
from typing import Dict, List, Any

from influx_service import fetch_timeseries
from llm_service   import smart_response

async def analyze_prompt(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Main entry point for processing user queries and generating responses.
    
    This function intelligently handles user input by:
    1. Detecting confirmation responses ("yes", "sure") and recycling previous queries
    2. Extracting relevant metrics and time parameters from natural language
    3. Fetching data from InfluxDB when appropriate (skips for hypothetical questions)
    4. Generating data summaries for the LLM context
    5. Coordinating with the LLM service to produce intelligent responses
    
    Args:
        chat_history: List of chat messages with "role" and "content" keys
        
    Returns:
        Dict containing graph data with "title", "description", and "series" keys
        
    Note: For hypothetical questions or when no metrics are detected, 
          skips database queries to avoid unnecessary API calls.
    """
    # ── Grab latest user and assistant messages ───────────────────────────
    last_user   = next((m for m in reversed(chat_history) if m["role"] == "user"), None)
    last_bot    = next((m for m in reversed(chat_history) if m["role"] == "assistant"), None)

    if not last_user:
        return {"title": "Error", "description": "Empty prompt", "series": []}

    user_txt = last_user["content"].strip().lower()

    # ── Detect short confirmation responses ───────────────────────────────
    # If user just said "yes"/"sure" and bot was asking for confirmation,
    # recycle the previous substantial user query instead of treating this as new input
    if user_txt in {"yes", "yep", "yeah", "sure", "ok", "okay"} and last_bot:
        # Walk backwards through chat history to find the previous non-confirmation user prompt
        prev_prompt = None
        skip_next   = True  # Skip the immediate confirmation message
        for m in reversed(chat_history):
            if m["role"] == "user":
                if skip_next:
                    skip_next = False
                    continue
                prev_prompt = m["content"]
                break
        prompt = prev_prompt or user_txt  # Fallback to confirmation if no previous prompt found
    else:
        prompt = last_user["content"]

    # ── Extract query parameters and fetch database data ──────────────────
    query = _extract_query(prompt, chat_history)

    # Skip database queries for hypothetical questions or when no metrics detected
    if "hypothetical" in prompt.lower() or not query["metrics"]:
        db_data = {"series": []}
    else:
        try:
            db_data = await fetch_timeseries(query["metrics"], query["time_window"])
        except Exception:
            # Gracefully handle database errors by proceeding without data
            db_data = {"series": []}

    # Generate summary of retrieved data for LLM context
    summary = _summarise(db_data)

    # Coordinate with LLM service to generate intelligent response
    return await smart_response(
        prompt,
        query["metrics"],
        query["time_window"],
        summary,
        chat_history,
    )


def _extract_query(prompt: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Extract relevant metrics and time window parameters from natural language input.
    
    This function performs intelligent parsing to identify:
    1. Which sensor metrics the user is asking about (temperature, humidity, etc.)
    2. What time window they're interested in (hours, days, weeks, months, years)
    
    If metrics aren't found in the current prompt, it searches back through chat history
    to maintain context from previous questions.
    
    Args:
        prompt: The user's current input text
        chat_history: Previous conversation context
        
    Returns:
        Dict with "metrics" (list of sensor types) and "time_window" (duration string)
        
    Supported metrics: temperature, humidity, rainfall, pressure
    Time formats: "1h", "6h", "12h", "7d", "30d", or "365d" (for 1 year)
    """
    txt = prompt.lower()

    # ── Metric detection ──────────────────────────────────────────────────
    # Look for sensor types mentioned in current prompt
    metrics = [m for m in ("temperature", "humidity", "rainfall", "pressure") if m in txt]
    
    # If no metrics found, search back through chat history for context
    if not metrics:
        for m in reversed(chat_history):
            if m["role"] == "user":
                found = [
                    k for k in ("temperature", "humidity", "rainfall", "pressure")
                    if k in m["content"].lower()
                ]
                if found:
                    metrics = found
                    break

    # ── Time window detection ─────────────────────────────────────────────
    # Handle explicit year requests (converts years to days for InfluxDB)
    m = re.search(r"(\d+)\s*year", txt)
    if m:
        years = int(m.group(1))
        window = f"{years*365}d"  # Convert years to days
    else:
        # Default time patterns - checks for common durations
        window = "24h"  # Default to last 24 hours
        for num, unit in (
            ("30", "d"), ("7", "d"), ("12", "h"), ("6", "h"), ("1", "h")
        ):
            if re.search(rf"\b{num}\s*(day|hour|week|month)", txt):
                window = f"{num}{unit}"
                break

    return {"metrics": metrics, "time_window": window}


def _summarise(db: Dict[str, Any]) -> str:
    """
    Generate a concise summary of time series data for LLM context.
    
    Creates a brief statistical summary of each data series including:
    - Average value across the time period
    - Latest/most recent value
    - Sensor label for identification
    
    Args:
        db: Database result dict containing "series" list
        
    Returns:
        String summary in format: "Temperature avg=23.5 latest=24.1; Humidity avg=67.2 latest=65.8"
        Empty string if no data available
        
    Note: This summary is included in the LLM prompt to provide context about
          the actual data values when generating responses.
    """
    parts = []
    for s in db.get("series", []):
        ys = s.get("y", [])  # Get the y-axis values (sensor readings)
        if not ys:
            continue
        # Calculate basic statistics for this sensor
        avg_val = sum(ys) / len(ys)
        latest_val = ys[-1]
        parts.append(f"{s['label']} avg={avg_val:.1f} latest={latest_val:.1f}")
    
    return "; ".join(parts)
