# workers.py - Consolidated AI and response handling with LLM-based query processing
# This file contains all the functionality for AI interactions and processing responses
# for graph generation in our application, now using LLM for intelligent query understanding.

import json                 # For parsing and generating JSON data
import os                   # For file operations and environment variables
import random               # For selecting random templates
import httpx                # For HTTP requests to external APIs
import datetime             # For date handling
import math                 # For mathematical operations
import asyncio              # For asynchronous operations
from PySide6.QtCore import QThread, Signal  # For threading in the UI
from openai import OpenAI, AsyncOpenAI      # For LLM API interactions
from typing import Dict, List, Any, Tuple, Optional, Union  # For type hints
import json, random, hashlib
from datetime import datetime, timedelta
import re

# Import the structured prompts
from llm_prompts import (
    get_query_analysis_prompt,
    get_graph_generation_prompt,
    get_analysis_prompt,
    get_forecast_prompt,
    get_validation_prompt,
    get_error_recovery_prompt
)

# Try real InfluxDB first – fall back to mock generator
try:
    from influx_service import fetch_timeseries as influx_fetch
except ImportError:
    influx_fetch = None

# --- Constants and Configuration ---
# These paths help locate important files and set up configuration
GRAPH_STORE_PATH = os.path.join(os.path.dirname(__file__), "graphs.json")  # Stores user graphs
EXAMPLE_GRAPHS_PATH = os.path.join(os.path.dirname(__file__), "examplegraphs.json")  # Example graphs
GRAPH_MAX = 30  # Maximum number of data points to include in a graph (prevents overloading)
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")  # Directory for caching data
os.makedirs(CACHE_DIR, exist_ok=True)  # Create cache directory if it doesn't exist

# --- AI Model Configuration ---
MODEL_NAME = "gemma3:1b"  # The LLM to use for generating responses

# --- Response Types ---
# Define constants for response types
RESPONSE_TYPE_GENERAL  = "General"     # NEW – free-form LLM answer (analysis / forecast / Q&A)
RESPONSE_TYPE_ANALYSIS = "Analysis"    # legacy (kept for backwards-compat logs)
RESPONSE_TYPE_GRAPH    = "Graph"
RESPONSE_TYPE_FLOORPLAN = "Floorplan"
RESPONSE_TYPE_FORECAST = "Forecast"

# --- LLM-based Query Processing ---
async def determine_response_type(prompt: str, chat_history: List[Dict[str, str]] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Uses LLM to determine what type of response to generate and extract query parameters.
    
    Args:
        prompt: The user's input prompt
        chat_history: Previous conversation context for better understanding
        
    Returns:
        A tuple containing:
        - response_type: One of the defined response types        - query_params: Dictionary with extracted parameters (metrics, location, time_window, etc.)
    """
    try:
        # Use local LLM to analyze the user's intent
        client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama'
        )
        
        # Use structured prompt template with chat history context
        analysis_prompt = get_query_analysis_prompt(prompt, chat_history or [])
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": analysis_prompt}],
            temperature=0.1,
            max_tokens=200
        )
          # Parse the LLM response
        raw_content = response.choices[0].message.content.strip()
        
        # Clean up common malformed JSON issues
        if raw_content.startswith('"\n  "'):
            # Handle cases where LLM returns quoted JSON
            raw_content = raw_content.strip('"')
        if raw_content.startswith('\n'):
            raw_content = raw_content.lstrip('\n').strip()
        
        # Try to extract JSON from the response
        try:
            result = json.loads(raw_content)
        except json.JSONDecodeError:
            # Try to extract JSON from within the text
            import re
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError(f"Could not parse LLM response as JSON: {raw_content}")
        
        response_type = result.get("response_type", RESPONSE_TYPE_GENERAL)
        query_params = {
            "metrics": result.get("metrics", []),
            "location": result.get("location"),
            "time_window": result.get("time_window", "24h"),
            "confidence": result.get("confidence", 0.8)
        }
        
        print(f"LLM determined: {response_type} with params: {query_params}")
        return response_type, query_params
        
    except Exception as e:
        print(f"Error in LLM query analysis: {e}")
        # Fallback to simple pattern matching
        return await determine_response_type_fallback(prompt, chat_history or [])

async def determine_response_type_fallback(prompt: str, chat_history: List[Dict[str, str]] = None) -> Tuple[str, Dict[str, Any]]:
    """Fallback method using pattern matching when LLM fails."""
    prompt_lower = prompt.lower()
    
    # Extract basic parameters using simple patterns
    metrics = []
    location = None
    time_window = "24h"
    
    # Basic metric detection
    if "temperature" in prompt_lower or "temp" in prompt_lower:
        metrics.append("temperature")
    if "humidity" in prompt_lower:
        metrics.append("humidity")
    if "rainfall" in prompt_lower or "rain" in prompt_lower:
        metrics.append("rainfall")
    if "pressure" in prompt_lower:
        metrics.append("pressure")
      # Location detection - find all locations mentioned
    locations = ["chicago", "new york", "los angeles", "miami", "san diego", "california"]
    found_locations = []
    for loc in locations:
        if loc in prompt_lower:
            found_locations.append(loc)
    
    # If multiple locations found, use all of them; otherwise use the first one
    if len(found_locations) > 1:
        location = found_locations  # Keep as list for multiple locations
    elif len(found_locations) == 1:
        location = found_locations[0]
    else:
        location = None# Time window detection (improved to catch more patterns)
    if any(phrase in prompt_lower for phrase in ["30 day", "30 days", "month", "past month"]):
        time_window = "30d"
    elif any(phrase in prompt_lower for phrase in ["7 day", "7 days", "week", "past week"]):
        time_window = "7d"
    elif any(phrase in prompt_lower for phrase in ["24 hour", "24 hours", "day", "past day"]):
        time_window = "24h"
    elif any(phrase in prompt_lower for phrase in ["12 hour", "12 hours"]):
        time_window = "12h"
    elif any(phrase in prompt_lower for phrase in ["6 hour", "6 hours"]):
        time_window = "6h"
    elif any(phrase in prompt_lower for phrase in ["hour", "past hour"]):
        time_window = "1h"
    # Look for specific numbers with time units
    import re
    time_match = re.search(r'(\d+)\s*(day|days|hour|hours|week|weeks|month|months)', prompt_lower)
    if time_match:
        number = int(time_match.group(1))
        unit = time_match.group(2)
        if 'day' in unit:
            time_window = f"{number}d"
        elif 'hour' in unit:
            time_window = f"{number}h"
        elif 'week' in unit:
            time_window = f"{number*7}d"
        elif 'month' in unit:
            time_window = f"{number*30}d"
      # Response type detection
    if any(word in prompt_lower for word in ["graph", "plot", "chart", "visualize", "show", "generate"]):
        response_type = RESPONSE_TYPE_GRAPH
    elif any(word in prompt_lower for word in ["floor", "map", "layout", "location"]):
        response_type = RESPONSE_TYPE_FLOORPLAN
    else:
        # Default to general response for analysis, forecasts, and other queries
        response_type = RESPONSE_TYPE_GENERAL
    
    query_params = {
        "metrics": metrics,
        "location": location,
        "time_window": time_window,
        "confidence": 0.6
    }
    
    print(f"Fallback determined: {response_type} with params: {query_params}")
    return response_type, query_params

# --- Enhanced Data Fetching with LLM-extracted Parameters ---
async def fetch_data_from_influxdb(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data based on LLM-extracted query parameters instead of simple keywords.
    
    Args:
        query_params: Dictionary with metrics, location, time_window, etc.
        
    Returns:
        Dictionary with series data formatted for graph generation
    """
    metrics = query_params.get("metrics", [])
    location = query_params.get("location")
    time_window = query_params.get("time_window", "24h")
    
    print(f"Fetching data for metrics: {metrics}, location: {location}, time_window: {time_window}")
    
    # Try real InfluxDB first
    if influx_fetch:
        try:
            # For real InfluxDB, we would use the extracted parameters
            result = await influx_fetch(metrics, time_window)
            print(f"InfluxDB returned data with {len(result.get('series', []))} series")
            return result
        except Exception as e:
            print(f"InfluxDB fetch failed ({e}); falling back to mock data generation")

    # Mock data generation based on extracted parameters
    if not metrics:
        metrics = ["temperature", "humidity", "rainfall"]  # Reasonable defaults
        print(f"No metrics provided, using defaults: {metrics}")
    
    mock_data = await generate_enhanced_mock_data(metrics, location, time_window)
    print(f"Mock data generated with {len(mock_data.get('series', []))} series")
    return mock_data

async def generate_enhanced_mock_data(metrics: List[str], location: Union[str, List[str]], time_window: str) -> Dict[str, Any]:
    """
    Generate realistic mock data based on LLM-extracted parameters.
    
    Args:
        metrics: List of sensor metrics to generate
        location: Location for context-appropriate data
        time_window: Time period for data generation
        
    Returns:
        Dictionary with realistic time series data
    """
    try:
        # Parse time window
        hours = 24  # default
        if time_window and time_window.endswith('h'):
            hours = int(time_window[:-1])
        elif time_window and time_window.endswith('d'):
            hours = int(time_window[:-1]) * 24
        elif time_window and time_window.endswith('m'):
            hours = int(time_window[:-1]) * 24 * 30
        
        print(f"Generating mock data for {hours} hours")
        
        # Ensure we have metrics
        if not metrics:
            metrics = ["temperature"]
            print("No metrics provided, defaulting to temperature")
        
        # Location-based baselines
        location_baselines = {
            "chicago": {"temperature": 65, "humidity": 70, "rainfall": 0.1},
            "new york": {"temperature": 68, "humidity": 65, "rainfall": 0.12},
            "los angeles": {"temperature": 75, "humidity": 55, "rainfall": 0.02},
            "miami": {"temperature": 80, "humidity": 85, "rainfall": 0.2},
            "san diego": {"temperature": 72, "humidity": 60, "rainfall": 0.05},
            "california": {"temperature": 75, "humidity": 58, "rainfall": 0.03}
        }        # Handle multiple locations or single location
        locations_to_process = []
        if isinstance(location, list):
            locations_to_process = location
        elif location:
            locations_to_process = [location]
        else:
            locations_to_process = ["default"]  # Fallback
        
        # Get baselines for each location
        series = []
        base_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Determine time unit and step for x-axis labels
        if hours <= 12:
            # For short periods, use hour labels
            time_unit = "hour"
            step_size = 1
            label_func = lambda i: f"-{hours-i}"
        elif hours <= 72:
            # For 1-3 days, use hour labels but step by hours
            time_unit = "hour"  
            step_size = max(1, hours // 24)
            label_func = lambda i: f"-{(hours-i)//1}"
        elif hours <= 168:  # 1 week
            # For up to a week, use day labels
            time_unit = "day"
            step_size = max(1, hours // 24)
            label_func = lambda i: f"-{(hours-i)//24}"
        else:
            # For longer periods, use day labels
            time_unit = "day"
            step_size = max(1, hours // 30)  # Show max 30 points
            label_func = lambda i: f"-{(hours-i)//24}"
        
        print(f"Using {time_unit} labels with step size {step_size}")
          # Generate data for each location and metric combination
        for loc in locations_to_process:
            baselines = location_baselines.get(loc, {"temperature": 70, "humidity": 65, "rainfall": 0.1})
            
            for metric in metrics:
                if metric not in baselines:
                    # Default values for unknown metrics
                    baseline = 50
                    variance = 10
                else:
                    baseline = baselines[metric]
                    if metric == "temperature":
                        variance = 8
                    elif metric == "humidity":
                        variance = 15
                    elif metric == "rainfall":
                        variance = baseline * 2  # rainfall is more variable
                    else:
                        variance = baseline * 0.2
                
                # Generate time series points
                points = []
                data_points = min(hours // step_size, GRAPH_MAX)
                print(f"Generating {data_points} data points for {metric} in {loc}")
                
                for i in range(data_points):
                    # Use relative time labels instead of timestamps
                    time_label = label_func(i * step_size)
                    
                    # Calculate the actual time for data generation (but don't use in output)
                    actual_time = base_time + timedelta(hours=i * step_size)
                    
                    # Add some realistic variation
                    if metric == "temperature":
                        # Temperature varies by time of day
                        hour_of_day = actual_time.hour
                        daily_cycle = 5 * math.sin((hour_of_day - 6) * math.pi / 12)
                        value = baseline + daily_cycle + random.gauss(0, variance/3)
                    elif metric == "rainfall":
                        # Rainfall is often zero with occasional precipitation
                        if random.random() < 0.8:
                            value = 0
                        else:
                            value = random.expovariate(1/baseline) if baseline > 0 else 0
                    else:
                        # General metrics with normal variation
                        value = baseline + random.gauss(0, variance)
                    
                    points.append([time_label, round(value, 2)])
                
                # Create a descriptive name that includes location for multiple locations
                if len(locations_to_process) > 1:
                    series_name = f"{metric.title()} ({loc.title()})"
                else:
                    series_name = metric.title()
                
                series.append({
                    "name": series_name,
                    "data": points
                })
                
                print(f"Generated {len(points)} points for {metric} in {loc}")
        
        result = {
            "series": series,
            "time_unit": time_unit,
            "x_axis_label": f"Time ({time_unit}s ago)"
        }
        print(f"Final mock data result: {len(series)} series, total points: {sum(len(s['data']) for s in series)}")
        return result
        
    except Exception as e:
        print(f"Error in mock data generation: {e}")
        # Absolute fallback - return minimal valid data
        return {
            "series": [
                {
                    "name": "Temperature",
                    "data": [
                        ["-2", 70.0],
                        ["-1", 72.0]
                    ]
                }
            ]
        }

# --- LLM-based Graph Generation ---
async def generate_graph_response_with_llm(prompt: str, query_params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Use LLM to generate appropriate graph structure and descriptions.
    
    Args:
        prompt: Original user prompt
        query_params: Extracted query parameters
        data: Raw data from InfluxDB/mock
        
    Returns:
        Formatted graph response with LLM-generated metadata
    """
    try:
        client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama'
        )        
        # Create context for the LLM
        metrics = query_params.get("metrics", [])
        location = query_params.get("location", "")
        time_window = query_params.get("time_window", "24h")
        
        # Use structured prompt template
        graph_prompt = get_graph_generation_prompt(prompt, metrics, location, time_window)
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": graph_prompt}],
            temperature=0.3,
            max_tokens=150
        )
          # Parse LLM response
        raw_content = response.choices[0].message.content.strip()
        
        # Clean up common malformed JSON issues
        if raw_content.startswith('"\n  "'):
            raw_content = raw_content.strip('"')
        if raw_content.startswith('\n'):
            raw_content = raw_content.lstrip('\n').strip()
        
        # Try to extract JSON from the response
        try:
            llm_result = json.loads(raw_content)
        except json.JSONDecodeError:
            # Try to extract JSON from within the text
            import re
            json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
            if json_match:
                llm_result = json.loads(json_match.group())
            else:
                # Fallback to default values
                llm_result = {
                    "title": "Data Visualization", 
                    "description": "Graph generated from your data",
                    "chart_type": "line"
                }        # Convert data format for frontend
        series_out = []
        for item in data.get("series", []):
            label = item.get("name", "Series")
            xs = [pt[0] for pt in item.get("data", [])]
            ys = [pt[1] for pt in item.get("data", [])]
            series_out.append({"label": label, "x": xs, "y": ys})
        
        # Ensure we have data - if not, force mock data generation
        if not series_out:
            print("No series data available, generating fallback data")
            metrics = query_params.get("metrics", ["temperature"])
            location = query_params.get("location", "chicago") 
            time_window = query_params.get("time_window", "24h")
            fallback_data = await generate_enhanced_mock_data(metrics, location, time_window)
            
            for item in fallback_data.get("series", []):
                label = item.get("name", "Series")
                xs = [pt[0] for pt in item.get("data", [])]
                ys = [pt[1] for pt in item.get("data", [])]
                series_out.append({"label": label, "x": xs, "y": ys})        
        result = {
            "description": llm_result.get("description", "Graph generated from your data"),
            "title": llm_result.get("title", "Data Visualization"),
            "series": series_out,
            "chart_type": llm_result.get("chart_type", "line"),
            "responseType": RESPONSE_TYPE_GRAPH,
            "x_axis_label": data.get("x_axis_label", "Time"),
            "time_unit": data.get("time_unit", "hour")
        }
        
        # Validate and fix the result
        return validate_and_fix_graph_response(result)
        
    except Exception as e:
        print(f"Error in LLM graph generation: {e}")
        # Fallback to simple graph generation
        return await generate_graph_response_fallback(prompt, query_params, data)

def validate_and_fix_graph_response(result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and fix a graph response using schema validation."""
    is_valid, errors, corrected = validate_graph_with_schema(result)
    
    if not is_valid:
        print(f"Graph validation errors: {errors}")
        print("Using corrected data")
        return corrected
    
    return result

async def generate_graph_response_fallback(prompt: str, query_params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback graph generation when LLM fails."""
    print(f"Using fallback graph generation. Data has {len(data.get('series', []))} series")
    
    series_out = []
    for item in data.get("series", []):
        label = item.get("name", "Series")
        xs = [pt[0] for pt in item.get("data", [])]
        ys = [pt[1] for pt in item.get("data", [])]
        series_out.append({"label": label, "x": xs, "y": ys})
        print(f"Converted series '{label}' with {len(xs)} points")
    
    # If no series were generated from existing data, create fresh mock data
    if not series_out:
        print("No series data available, generating fresh mock data")
        metrics = query_params.get("metrics", ["temperature"])
        location = query_params.get("location", "chicago")
        time_window = query_params.get("time_window", "24h")
        
        # Generate fresh mock data
        mock_data = await generate_enhanced_mock_data(metrics, location, time_window)
        
        for item in mock_data.get("series", []):
            label = item.get("name", "Series")
            xs = [pt[0] for pt in item.get("data", [])]
            ys = [pt[1] for pt in item.get("data", [])]
            series_out.append({"label": label, "x": xs, "y": ys})
            print(f"Generated mock series '{label}' with {len(xs)} points")
    
    # Final fallback if everything fails
    if not series_out:
        print("Creating absolute minimum fallback data")
        current_time = datetime.utcnow().isoformat() + "Z"
        prev_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        series_out = [{
            "label": "Temperature",
            "x": [prev_time, current_time],
            "y": [70.0, 72.0]
        }]    
    metrics = query_params.get("metrics", [])
    location = query_params.get("location", "")
    time_window = query_params.get("time_window", "24h")
    
    title = f"{', '.join(metrics).title()} over {time_window}" if metrics else "Data Visualization"
    if location:
        # Handle both single location (string) and multiple locations (list)
        if isinstance(location, list):
            location_str = " vs ".join([loc.title() for loc in location])
        else:
            location_str = location.title()
        title += f" in {location_str}"
    
    description = f"Showing {', '.join(metrics)} data over the last {time_window}" if metrics else "Data visualization"
      # Determine time unit for axis labeling
    time_window = query_params.get("time_window", "24h")
    if time_window.endswith('h'):
        time_unit = "hour"
    elif time_window.endswith('d'):
        time_unit = "day"
    else:
        time_unit = "hour"
    
    result = {
        "description": description,
        "title": title,
        "series": series_out,
        "responseType": RESPONSE_TYPE_GRAPH,
        "x_axis_label": f"Time ({time_unit}s ago)",
        "time_unit": time_unit
    }
    
    print(f"Fallback graph result: {len(series_out)} series")
    return result

# --- LLM-based General Response Generation ---
async def generate_general_response_with_llm(prompt: str, query_params: Dict[str, Any], data: Dict[str, Any], chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Use LLM to generate conversational, easy-to-read responses for analysis, forecasts, and general questions.
    
    Args:
        prompt: Original user prompt  
        query_params: Extracted query parameters
        data: Raw data for context
        
    Returns:
        General response with conversational insights
    """
    try:
        client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama'
        )        
        # Prepare data summary for LLM context
        data_summary = []
        for series in data.get("series", []):
            values = [pt[1] for pt in series.get("data", [])]
            if values:
                avg_val = sum(values) / len(values)
                min_val = min(values)
                max_val = max(values)
                latest_val = values[-1]
                data_summary.append(f"{series.get('name', 'Series')}: avg={avg_val:.1f}, min={min_val:.1f}, max={max_val:.1f}, current={latest_val:.1f}")
          # Build chat history context
        conversation_context = ""
        if chat_history and len(chat_history) > 1:
            recent_messages = chat_history[-4:]  # Last 2 exchanges
            context_items = []
            for msg in recent_messages[:-1]:  # Exclude current message
                role = msg.get("role", "")
                content = msg.get("content", "").strip()
                if content and role in ["user", "assistant"]:
                    context_items.append(f"{role.title()}: {content[:150]}")
            
            if context_items:
                conversation_context = f"\nRecent conversation:\n{chr(10).join(context_items)}\n"
          # Create an analytical prompt for the LLM 
        context_prompt = f"""You are a data analyst providing technical analysis. Give direct, analytical responses without conversational filler.

{conversation_context}
Current question: {prompt}

Available data: {'; '.join(data_summary) if data_summary else 'No specific data available'}
Location: {query_params.get('location', 'Not specified')}
Time period: {query_params.get('time_window', 'Not specified')}

Requirements:
- Provide analytical findings, not conversational commentary
- Use precise technical language
- State facts and patterns directly
- Include specific numbers when available
- Avoid phrases like "Hey there", "Cool!", "Honestly", etc.
- No emotional language or filler words
- Focus on data trends, comparisons, and analytical insights
- Be concise and factual"""
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": context_prompt}],
            temperature=0.3,
            max_tokens=400
        )
        
        return {
            "description": response.choices[0].message.content.strip(),
            "title": "Data Insights",
            "series": [],
            "responseType": RESPONSE_TYPE_GENERAL
        }
        
    except Exception as e:
        print(f"Error in LLM general response generation: {e}")
        # Simple fallback response
        metrics = query_params.get('metrics', [])
        location = query_params.get('location', '')
        time_window = query_params.get('time_window', '24h')        
        if metrics:
            response_text = f"Looking at the {', '.join(metrics)} data"
            if location:
                # Handle both single location (string) and multiple locations (list)
                if isinstance(location, list):
                    location_str = " and ".join([loc.title() for loc in location])
                else:
                    location_str = location.title()
                response_text += f" from {location_str}"
            if time_window:
                response_text += f" over the past {time_window}"
            response_text += ". The data shows normal variations within expected ranges. "
            
            if "forecast" in prompt.lower() or "predict" in prompt.lower():
                response_text += "Based on current trends, we can expect similar patterns to continue in the near term."
            elif "analysis" in prompt.lower() or "analyze" in prompt.lower():
                response_text += "The patterns indicate stable conditions with some natural fluctuation."
            else:
                response_text += "Feel free to ask for more specific analysis or forecasting insights."
        else:
            response_text = "I can help you analyze data, create forecasts, or answer questions about your sensor readings. What would you like to know?"
        
        return {
            "description": response_text,
            "title": "Data Insights",
            "series": [],
            "responseType": RESPONSE_TYPE_GENERAL
        }

# --- Main Analysis Function (Refactored) ---
async def analyze_prompt(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Main function that processes user requests using LLM-based understanding.
    
    Args:
        chat_history: List of previous messages between the user and AI
        
    Returns:
        Appropriate response based on LLM analysis of user intent
    """
    try:
        # Extract the latest user prompt from chat_history
        prompt = ""
        for msg in reversed(chat_history):
            if msg.get("role") == "user":
                prompt = msg.get("content", "").strip()
                break
        
        if not prompt:
            raise ValueError("No user prompt detected in chat history")        # Step 1: Use LLM to determine response type and extract parameters
        response_type, query_params = await determine_response_type(prompt, chat_history)
        
        # Step 2: Fetch data based on LLM-extracted parameters
        data = await fetch_data_from_influxdb(query_params)        # Step 3: Generate appropriate response using LLM
        if response_type == RESPONSE_TYPE_GRAPH:
            result = await generate_graph_response_with_llm(prompt, query_params, data)
        elif response_type == RESPONSE_TYPE_FLOORPLAN:
            result = await generate_floorplan_response(prompt, query_params)
        else:  # RESPONSE_TYPE_GENERAL (covers analysis, forecasts, general questions)
            result = await generate_general_response_with_llm(prompt, query_params, data, chat_history)
        # Add standard fields
        result["is_fav"] = False
        if "responseType" not in result:
            result["responseType"] = response_type
          # Validate graph responses
        if response_type == RESPONSE_TYPE_GRAPH:
            result = validate_and_fix_graph_response(result)
            # Save the graph to graphs.json so it appears in the UI
            if result.get("series") and len(result["series"]) > 0:
                save_success = save_graph_to_file(result)
                if save_success:
                    print(f"Graph '{result.get('title', 'Untitled')}' saved to graphs.json")
                else:
                    print(f"Failed to save graph '{result.get('title', 'Untitled')}' to graphs.json")
        
        print(f"Generated {response_type} response with {len(result.get('series', []))} series")
        return result
        
    except Exception as e:
        print(f"Error during prompt analysis: {e}")
        return {
            "description": f"I encountered an error processing your request: {str(e)}",
            "title": "Error",
            "series": [],
            "is_fav": False,
            "responseType": RESPONSE_TYPE_GENERAL
        }

async def generate_floorplan_response(prompt: str, query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generates a floorplan visualization response (placeholder for now).
    
    Args:
        prompt: The user's original prompt
        query_params: Extracted query parameters
        
    Returns:
        A dictionary with description and title fields
    """
    return {
        "description": "Floorplan visualization functionality is coming soon. This feature will display sensor data overlaid on floor maps.",
        "title": "Floorplan Visualization (Coming Soon)",
        "series": [],
        "responseType": RESPONSE_TYPE_FLOORPLAN
    }

# --- Template and Data Management (Legacy Support) ---
def load_graph_templates() -> List[Dict[str, Any]]:
    """
    Loads graph templates from saved files (kept for backward compatibility).
    """
    try:
        if os.path.exists(GRAPH_STORE_PATH):
            with open(GRAPH_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        elif os.path.exists(EXAMPLE_GRAPHS_PATH):
            with open(EXAMPLE_GRAPHS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return [{
                "title": "Sample Temperature Chart",
                "series": [
                    {
                        "label": "Temperature (°F)",
                        "x": [1, 2, 3, 4, 5],
                        "y": [72, 74, 73, 75, 71]
                    }
                ]
            }]
    except Exception as e:
        print(f"Error loading graph templates: {e}")
        return []

def save_graph_to_file(graph_data: Dict[str, Any]) -> bool:
    """
    Saves a graph to the graphs.json file so it appears in the UI.
    
    Args:
        graph_data: The graph data to save (must include title, series, etc.)
        
    Returns:
        bool: True if saved successfully, False otherwise
    """
    try:
        # Load existing graphs
        existing_graphs = load_graph_templates()
        
        # Ensure the graph has required fields
        graph_to_save = {
            "title": graph_data.get("title", "Untitled Graph"),
            "series": graph_data.get("series", []),
            "is_fav": graph_data.get("is_fav", False)
        }
        
        # Add optional fields if they exist
        if "description" in graph_data:
            graph_to_save["description"] = graph_data["description"]
        if "responseType" in graph_data:
            graph_to_save["responseType"] = graph_data["responseType"]
        
        # Check if a graph with the same title already exists
        # If so, update it; otherwise, add it as a new graph
        title_exists = False
        for i, existing_graph in enumerate(existing_graphs):
            if existing_graph.get("title") == graph_to_save["title"]:
                existing_graphs[i] = graph_to_save
                title_exists = True
                break
        
        if not title_exists:
            existing_graphs.append(graph_to_save)
        
        # Save back to file
        with open(GRAPH_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_graphs, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved graph: {graph_to_save['title']}")
        return True
        
    except Exception as e:
        print(f"Error saving graph to file: {e}")
        return False

# --- Schema Validation ---
try:
    import jsonschema
    SCHEMA_VALIDATION_AVAILABLE = True
except ImportError:
    SCHEMA_VALIDATION_AVAILABLE = False
    print("jsonschema not available - skipping schema validation")

def load_graph_schema() -> dict:
    """Load the JSON schema for graph validation."""
    try:
        schema_path = os.path.join(os.path.dirname(__file__), "graph_schema.json")
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading graph schema: {e}")
        return {}

def validate_graph_with_schema(graph_data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
    """
    Validate graph data against the JSON schema and attempt corrections.
    
    Args:
        graph_data: The graph data to validate
        
    Returns:
        Tuple of (is_valid, error_list, corrected_data)
    """
    if not SCHEMA_VALIDATION_AVAILABLE:
        return True, [], graph_data  # Skip validation if jsonschema not available
        
    schema = load_graph_schema()
    if not schema:
        return True, [], graph_data  # Skip validation if schema not available
    
    try:
        # First try direct validation
        jsonschema.validate(graph_data, schema)
        return True, [], graph_data
        
    except jsonschema.ValidationError as e:
        errors = [str(e)]
        
        # Attempt to fix common issues
        corrected = graph_data.copy()
        
        # Ensure required fields exist
        if "title" not in corrected:
            corrected["title"] = "Data Visualization"
        if "description" not in corrected:
            corrected["description"] = "Generated graph data"
        if "responseType" not in corrected:
            corrected["responseType"] = "Graph"
        if "series" not in corrected:
            corrected["series"] = []
        
        # Fix series data
        fixed_series = []
        for series in corrected.get("series", []):
            if isinstance(series, dict):
                fixed_series_item = {
                    "label": series.get("label", "Data"),
                    "x": series.get("x", []),
                    "y": series.get("y", [])
                }
                
                # Ensure x and y have same length
                min_len = min(len(fixed_series_item["x"]), len(fixed_series_item["y"]))
                fixed_series_item["x"] = fixed_series_item["x"][:min_len]
                fixed_series_item["y"] = fixed_series_item["y"][:min_len]
                
                # Ensure max length
                if min_len > 1000:
                    fixed_series_item["x"] = fixed_series_item["x"][:1000]
                    fixed_series_item["y"] = fixed_series_item["y"][:1000]
                
                if min_len > 0:  # Only add series with data
                    fixed_series.append(fixed_series_item)
        
        corrected["series"] = fixed_series        
        # Try validation again
        try:
            if SCHEMA_VALIDATION_AVAILABLE:
                jsonschema.validate(corrected, schema)
            return True, [], corrected
        except jsonschema.ValidationError as e2:
            return False, errors + [str(e2)], corrected
            
    except Exception as e:
        return False, [f"Validation error: {str(e)}"], graph_data

# --- Enhanced Response Generation with Validation ---

# --- ChatWorker: Background LLM Calls ---
class ChatWorker(QThread):
    """
    A worker thread that runs the AI call in the background so the UI doesn't freeze.
    """
    result_ready = Signal(str, str, list)
    
    def __init__(self, chat_history):
        super().__init__()
        self.chat_history = chat_history
        print("Initializing OpenAI client with Ollama base URL for local LLM")
        self.client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama'
        )
        
    def run(self):
        """
        Executes the AI call in the background and sends results when done.
        """
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(analyze_prompt(self.chat_history))
            loop.close()
            
            desc = result.get("description", "")
            if "responseType" in result:
                desc = f"[{result['responseType']}] {desc}"
            title = result.get("title", "")
            series = result.get("series", [])
                
        except Exception as e:
            print(f"Error processing prompt: {e}")
            desc = f"Sorry, I encountered an error processing your request: {str(e)}"
            title = "Error"
            series = []

        self.result_ready.emit(desc, title, series)

# --- FastAPI Helper ---
def call_openai(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    A helper function for FastAPI endpoints to call the AI and get results.
    """
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(analyze_prompt(chat_history))
        loop.close()
        
        if "responseType" not in result:
            result["responseType"] = RESPONSE_TYPE_GENERAL
            
        print(f"Response type: {result.get('responseType')} with {len(result.get('series', []))} data series")
        return result
        
    except Exception as e:
        print(f"Error in call_openai: {e}")
        return {
            "description": f"Error processing request: {str(e)}",
            "title": "Error",
            "series": [],
            "is_fav": False,
            "responseType": RESPONSE_TYPE_GENERAL
        }

async def analyze_prompt_with_timeout(chat_history: List[Dict[str, str]], timeout: int = 60) -> Dict[str, Any]:
    """
    A wrapper around analyze_prompt that supports timeouts and cancellation.
    """
    try:
        return await asyncio.wait_for(analyze_prompt(chat_history), timeout=timeout)
    except asyncio.CancelledError:
        print("AI request was cancelled")
        return {
            "description": "The request was cancelled by the user.",
            "title": "Request Cancelled", 
            "series": [],
            "is_fav": False,
            "responseType": RESPONSE_TYPE_GENERAL
        }
    except asyncio.TimeoutError:
        print(f"AI request timed out after {timeout} seconds")
        return {
            "description": f"The request took too long and timed out. Please try again with a simpler request.",
            "title": "Request Timeout",
            "series": [],
            "is_fav": False,
            "responseType": RESPONSE_TYPE_GENERAL
        }
    except Exception as e:
        print(f"Error in analyze_prompt_with_timeout: {e}")
        return {
            "description": f"Error processing your request: {str(e)}",
            "title": "Error",
            "series": [],
            "is_fav": False,
            "responseType": RESPONSE_TYPE_GENERAL
        }

# --- Legacy Functions (for backward compatibility) ---
def generate_weather_example_data(location="San Diego", days=5, seed=None):
    """Legacy function kept for backward compatibility."""
    import random
    import datetime
    
    if seed is not None:
        random.seed(seed)
    
    today = datetime.datetime.now()
    timestamps = []
    temps = []
    humidity = []
    rainfall = []
    
    # Location-based defaults
    location_data = {
        "San Diego": (72, 65, 0.15),
        "New York": (65, 70, 0.30),
        "Chicago": (60, 65, 0.25),
        "Miami": (78, 80, 0.40),
        "California": (75, 60, 0.10)
    }
    
    base_temp, base_humidity, rain_chance = location_data.get(location, (70, 65, 0.20))
    
    for i in range(days):
        date = today - datetime.timedelta(days=(days-i-1))
        for hour in [8, 12, 16, 20]:
            timestamps.append(date.replace(hour=hour).strftime("%m/%d/%Y %H:%M"))
            
            hour_adjustment = {8: -5, 12: 2, 16: 5, 20: -3}[hour]
            trend_adjustment = (i - days//2) * 0.5
            
            daily_temp = base_temp + random.uniform(-5, 5) + hour_adjustment + trend_adjustment
            temps.append(round(daily_temp, 1))
            
            daily_humidity = base_humidity - (hour_adjustment * 1.5) + random.uniform(-8, 8)
            humidity.append(round(max(min(daily_humidity, 100), 0), 1))
            
            if random.random() < rain_chance:
                rainfall.append(round(random.uniform(0.1, 0.8), 2))
            else:
                rainfall.append(0)
    
    return {
        "timestamps": timestamps,
        "temperature": temps,
        "humidity": humidity,
        "rainfall": rainfall,
        "location": location
    }
