# workers.py - Unified LLM-based response handling
# This file contains simplified AI interaction functionality using a single
# LLM approach to determine the best response format based on context and data.

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

# Try real InfluxDB first – fall back to mock generator
try:
    from influx_service import fetch_timeseries as influx_fetch
except ImportError:
    influx_fetch = None

# --- Constants and Configuration ---
GRAPH_STORE_PATH = os.path.join(os.path.dirname(__file__), "graphs.json")
EXAMPLE_GRAPHS_PATH = os.path.join(os.path.dirname(__file__), "examplegraphs.json")
GRAPH_MAX = 30  # Maximum number of data points to include in a graph
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# --- AI Model Configuration ---
MODEL_NAME = "gemma3:1b"

# --- Core Data Processing Functions ---

def extract_query_parameters(prompt: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Extract basic query parameters from user prompt and chat history using pattern matching.
    
    Args:
        prompt: The user's input prompt
        chat_history: Previous conversation context to extract metrics from
        
    Returns:
        Dictionary with extracted parameters (metrics, time_window, etc.)
    """
    prompt_lower = prompt.lower()
    
    # Extract metrics from current prompt
    current_metrics = []
    if "temperature" in prompt_lower or "temp" in prompt_lower:
        current_metrics.append("temperature")
    if "humidity" in prompt_lower:
        current_metrics.append("humidity")
    if "rainfall" in prompt_lower or "rain" in prompt_lower:
        current_metrics.append("rainfall")
    if "pressure" in prompt_lower:
        current_metrics.append("pressure")
    
    # Extract metrics from chat history if current prompt doesn't specify any
    historical_metrics = []
    if chat_history and not current_metrics:
        print(f"No current metrics found, checking chat history ({len(chat_history)} messages)")
        # Look through recent messages for previously mentioned metrics
        for i, msg in enumerate(reversed(chat_history[-10:])):  # Check last 10 messages
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                print(f"  Checking message {i}: '{content[:50]}...'")
                if "temperature" in content or "temp" in content:
                    historical_metrics.append("temperature")
                if "humidity" in content:
                    historical_metrics.append("humidity")
                if "rainfall" in content or "rain" in content:
                    historical_metrics.append("rainfall")
                if "pressure" in content:
                    historical_metrics.append("pressure")
        
        # Remove duplicates while preserving order
        seen = set()
        historical_metrics = [x for x in historical_metrics if not (x in seen or seen.add(x))]
        print(f"  Found historical metrics: {historical_metrics}")
    else:
        print(f"Found current metrics: {current_metrics} or no chat history available")
    
    # Use current metrics if available, otherwise fall back to historical context
    metrics = current_metrics if current_metrics else historical_metrics
    
    # Extract time window
    time_window = "24h"  # default
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
    
    return {
        "metrics": metrics,
        "time_window": time_window,
        "context_source": "current" if current_metrics else "historical"
    }

async def fetch_data_from_influxdb(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch data based on extracted query parameters.
    
    Args:
        query_params: Dictionary with metrics, time_window, etc.
        
    Returns:
        Dictionary with series data formatted for analysis
    """
    metrics = query_params.get("metrics", [])
    time_window = query_params.get("time_window", "24h")
    
    print(f"Fetching data for metrics: {metrics}, time_window: {time_window}")
    
    # Try real InfluxDB first
    if influx_fetch:
        try:
            result = await influx_fetch(metrics, time_window)
            print(f"InfluxDB returned data with {len(result.get('series', []))} series")
            return result
        except Exception as e:
            print(f"InfluxDB fetch failed ({e}); falling back to mock data generation")

    # Fall back to mock data generation
    if not metrics:
        metrics = ["temperature", "humidity", "rainfall"]
        print(f"No metrics provided, using defaults: {metrics}")
    
    mock_data = await generate_mock_data(metrics, time_window)
    print(f"Mock data generated with {len(mock_data.get('series', []))} series")
    return mock_data

async def generate_mock_data(metrics: List[str], time_window: str) -> Dict[str, Any]:
    """
    Generate realistic mock data based on extracted parameters.
    
    Args:
        metrics: List of sensor metrics to generate
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
        
        # Metric baselines (removed location-specific logic)
        metric_baselines = {
            "temperature": {"baseline": 72, "variance": 8},
            "humidity": {"baseline": 65, "variance": 15},
            "rainfall": {"baseline": 0.1, "variance": 0.2},
            "pressure": {"baseline": 1013, "variance": 20}
        }
        
        # Generate data
        series = []
        base_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Determine time unit and step for x-axis labels
        if hours <= 12:
            time_unit = "hour"
            step_size = 1
            label_func = lambda i: f"-{hours-i}"
        elif hours <= 72:
            time_unit = "hour"  
            step_size = max(1, hours // 24)
            label_func = lambda i: f"-{(hours-i)//1}"
        elif hours <= 168:  # 1 week
            time_unit = "day"
            step_size = max(1, hours // 24)
            label_func = lambda i: f"-{(hours-i)//24}"
        else:
            time_unit = "day"
            step_size = max(1, hours // 30)
            label_func = lambda i: f"-{(hours-i)//24}"
        
        print(f"Using {time_unit} labels with step size {step_size}")
        
        # Generate data for each metric
        for metric in metrics:
            baseline_data = metric_baselines.get(metric, {"baseline": 50, "variance": 10})
            baseline = baseline_data["baseline"]
            variance = baseline_data["variance"]
            
            # Generate time series points
            points = []
            data_points = min(hours // step_size, GRAPH_MAX)
            print(f"Generating {data_points} data points for {metric}")
            
            for i in range(data_points):
                time_label = label_func(i * step_size)
                actual_time = base_time + timedelta(hours=i * step_size)
                
                # Add realistic variation
                if metric == "temperature":
                    hour_of_day = actual_time.hour
                    daily_cycle = 5 * math.sin((hour_of_day - 6) * math.pi / 12)
                    value = baseline + daily_cycle + random.gauss(0, variance/3)
                elif metric == "rainfall":
                    if random.random() < 0.8:
                        value = 0
                    else:
                        value = random.expovariate(1/baseline) if baseline > 0 else 0
                else:
                    value = baseline + random.gauss(0, variance)
                
                points.append([time_label, round(value, 2)])
            
            series.append({
                "name": metric.title(),
                "data": points
            })
            
            print(f"Generated {len(points)} points for {metric}")
        
        result = {
            "series": series,
            "time_unit": time_unit,
            "x_axis_label": f"Time ({time_unit}s ago)"
        }
        print(f"Final mock data result: {len(series)} series, total points: {sum(len(s['data']) for s in series)}")
        return result
        
    except Exception as e:
        print(f"Error in mock data generation: {e}")
        return {
            "series": [
                {
                    "name": "Temperature",
                    "data": [["-2", 70.0], ["-1", 72.0]]
                }
            ]
        }

def build_comprehensive_context(prompt: str, query_params: Dict[str, Any], data: Dict[str, Any], chat_history: List[Dict[str, str]] = None) -> str:
    """
    Build a comprehensive context for the LLM that includes all available information.
    
    Args:
        prompt: Original user prompt
        query_params: Extracted query parameters
        data: Available sensor data
        chat_history: Previous conversation context
        
    Returns:
        Formatted context string for the LLM
    """
    # Start with natural system instructions
    context = """You are a friendly and helpful assistant for an IoT sensor monitoring system. You can chat naturally with users and help them with their sensor data needs.

IMPORTANT: Use the conversation history provided below to maintain context and continuity. Remember what the user has told you and build upon previous exchanges.

When users greet you with "Hello", "Hi", or similar, just respond warmly and naturally - NO prefixes, NO formal language.

You can:
- Have normal conversations and answer general questions
- Create graphs and visualizations when users want to see data
- Analyze sensor data and provide insights
- Explain trends and patterns in the data

Be conversational and natural. Don't add prefixes like "[General]" or "Okay, let's begin." Just respond naturally to what the user says.

For simple greetings like "Hello!" just say something like "Hello! What would you like me to help you with?" - keep it casual and friendly.

USER'S CURRENT REQUEST: {prompt}
""".format(prompt=prompt)
    
    # Add data context only if relevant
    if query_params.get("metrics") or data.get("series"):
        context += "\nAVAILABLE SENSOR DATA:\n"
        
        if query_params.get("metrics"):
            metrics_source = query_params.get("context_source", "current")
            context += f"Metrics: {', '.join(query_params['metrics'])} (from {metrics_source} context)\n"
        
        if query_params.get("time_window"):
            context += f"Time Period: {query_params['time_window']}\n"
        
        if data.get("series"):
            context += "Data Summary:\n"
            for series in data["series"]:
                values = [pt[1] for pt in series.get("data", [])]
                if values:
                    avg_val = sum(values) / len(values)
                    min_val = min(values)
                    max_val = max(values)
                    latest_val = values[-1]
                    context += f"- {series.get('name', 'Unknown')}: avg={avg_val:.1f}, min={min_val:.1f}, max={max_val:.1f}, current={latest_val:.1f}\n"
    
    # Add conversation context if available
    if chat_history and len(chat_history) > 1:
        context += "\nCONVERSATION HISTORY:\n"
        recent_messages = chat_history[-8:]  # Last 4 exchanges
        for msg in recent_messages[:-1]:  # Exclude current message
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if content and role in ["user", "assistant"] and not content.startswith("[[GRAPH_DATA]]"):
                # Show full context for recent messages to help LLM understand
                if role == "user":
                    context += f"User said: {content}\n"
                elif role == "assistant":
                    context += f"You replied: {content}\n"
    
    # Add response format instructions
    context += """
RESPONSE FORMAT:
- For greetings, general questions, or casual conversation: Just respond naturally in plain text
- For data visualization requests: Respond with JSON like this:
  {"response_type": "graph", "title": "Chart Title", "description": "Natural description", "analysis": "Your analysis"}
- For data analysis requests: Respond with JSON like this:
  {"response_type": "text", "title": "Analysis", "content": "Your detailed analysis"}

Be natural, helpful, and conversational. No formal prefixes or rigid structure needed.
"""
    
    return context

async def generate_unified_response(prompt: str, query_params: Dict[str, Any], data: Dict[str, Any], chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Generate a unified response using LLM with comprehensive context.
    
    Args:
        prompt: Original user prompt
        query_params: Extracted query parameters
        data: Available sensor data
        chat_history: Previous conversation context
        
    Returns:
        Formatted response dictionary
    """
    try:
        client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama'
        )
        
        # Build comprehensive context
        context = build_comprehensive_context(prompt, query_params, data, chat_history)
        print(f"LLM Context being sent:\n{context}")
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": context}],
            temperature=0.3,
            max_tokens=800
        )
        
        raw_content = response.choices[0].message.content.strip()
        print(f"LLM Raw response: {raw_content}")
        
        # Try to parse as JSON first
        try:
            # Clean up potential JSON formatting issues
            if raw_content.startswith('```json'):
                raw_content = raw_content.replace('```json', '').replace('```', '').strip()
            elif raw_content.startswith('```'):
                raw_content = raw_content.replace('```', '').strip()
            
            llm_response = json.loads(raw_content)
            
            # Process based on response type
            if llm_response.get("response_type") == "graph":
                return format_graph_response(llm_response, data, query_params)
            else:
                return format_text_response(llm_response)
                
        except json.JSONDecodeError:
            # If not JSON, treat as plain text response (for casual conversation)
            return {
                "description": raw_content,
                "title": "Chat",
                "series": [],
                "is_fav": False,
                "responseType": "Chat"
            }
        
    except Exception as e:
        print(f"Error in unified response generation: {e}")
        return generate_fallback_response(prompt, query_params, data)

def format_graph_response(llm_response: Dict[str, Any], data: Dict[str, Any], query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Format LLM response as a graph response."""
    # Convert data format for frontend
    series_out = []
    for item in data.get("series", []):
        label = item.get("name", "Series")
        xs = [pt[0] for pt in item.get("data", [])]
        ys = [pt[1] for pt in item.get("data", [])]
        series_out.append({"label": label, "x": xs, "y": ys})
    
    # Ensure we have data
    if not series_out:
        print("No series data available, generating fallback data")
        metrics = query_params.get("metrics", ["temperature"])
        time_window = query_params.get("time_window", "24h")
        # Note: In a real implementation, you'd generate fallback data here
        series_out = [{
            "label": "Temperature",
            "x": ["-2", "-1"],
            "y": [70.0, 72.0]
        }]
    
    result = {
        "description": llm_response.get("analysis", llm_response.get("description", "Graph generated from sensor data")),
        "title": llm_response.get("title", "Data Visualization"),
        "series": series_out,
        "is_fav": False,
        "x_axis_label": data.get("x_axis_label", "Time"),
        "time_unit": data.get("time_unit", "hour"),
        "responseType": "Graph"
    }
    
    # Save graph for UI
    save_graph_to_file(result)
    
    return result

def format_text_response(llm_response: Dict[str, Any]) -> Dict[str, Any]:
    """Format LLM response as a text response."""
    return {
        "description": llm_response.get("content", llm_response.get("description", "Analysis complete")),
        "title": llm_response.get("title", "Data Insights"),
        "series": [],
        "is_fav": False,
        "insights": llm_response.get("insights", []),
        "responseType": "Analysis"
    }

def generate_fallback_response(prompt: str, query_params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a fallback response when LLM fails."""
    metrics = query_params.get('metrics', [])
    time_window = query_params.get('time_window', '24h')
    
    # Check for casual greetings
    prompt_lower = prompt.lower().strip()
    if any(greeting in prompt_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
        return {
            "description": "Hello! I'm here to help you with your sensor data. I can create graphs, analyze data trends, or just chat with you. What would you like to do?",
            "title": "Chat",
            "series": [],
            "is_fav": False,
            "responseType": "Chat"
        }
    
    # Determine if this looks like a graph request
    wants_graph = any(word in prompt_lower for word in ["graph", "plot", "chart", "visualize", "show"])
    
    if wants_graph and data.get("series"):
        # Generate graph response
        series_out = []
        for item in data.get("series", []):
            label = item.get("name", "Series")
            xs = [pt[0] for pt in item.get("data", [])]
            ys = [pt[1] for pt in item.get("data", [])]
            series_out.append({"label": label, "x": xs, "y": ys})
        
        title = f"{', '.join(metrics).title()} over {time_window}" if metrics else "Data Visualization"
        description = f"Here's your {', '.join(metrics)} data over the last {time_window}." if metrics else "Here's the data visualization you requested."
        
        result = {
            "description": description,
            "title": title,
            "series": series_out,
            "is_fav": False,
            "x_axis_label": data.get("x_axis_label", "Time"),
            "time_unit": data.get("time_unit", "hour"),
            "responseType": "Graph"
        }
        
        save_graph_to_file(result)
        return result
    else:
        # Generate casual text response
        if metrics:
            response_text = f"I can see you're interested in {', '.join(metrics)} data. Would you like me to create a graph, provide analysis, or is there something specific you'd like to know?"
        else:
            response_text = "I'm here to help with your sensor data! I can create visualizations, analyze trends, answer questions, or just chat. What can I do for you?"
        
        return {
            "description": response_text,
            "title": "Chat",
            "series": [],
            "is_fav": False,
            "responseType": "Chat"
        }

# --- Main Analysis Function ---
async def analyze_prompt(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Main function that processes user requests using unified LLM approach.
    
    Args:
        chat_history: List of previous messages between the user and AI
        
    Returns:
        Appropriate response based on LLM analysis of user intent
    """
    try:
        print(f"Analyze prompt called with chat_history: {chat_history}")
        
        # Extract the latest user prompt from chat_history
        prompt = ""
        for msg in reversed(chat_history):
            if msg.get("role") == "user":
                prompt = msg.get("content", "").strip()
                break
        
        if not prompt:
            raise ValueError("No user prompt detected in chat history")
        
        print(f"Processing prompt: {prompt}")
        print(f"Total chat history length: {len(chat_history)}")
        print(f"Assistant messages in history: {len([msg for msg in chat_history if msg.get('role') == 'assistant'])}")
        
        # Check for simple greetings ONLY if it's the start of conversation or a very simple greeting
        prompt_lower = prompt.lower().strip()
        is_simple_greeting = (
            len(prompt.split()) <= 2 and  # Very short phrases only
            prompt_lower in ["hello", "hi", "hey", "hello!", "hi!", "hey!", "good morning", "good afternoon", "good evening"] and
            len([msg for msg in chat_history if msg.get("role") == "assistant"]) <= 1  # First or second interaction only
        )
        
        if is_simple_greeting:
            print("Detected simple greeting at start of conversation, using fallback response")
            return {
                "description": "Hello! What would you like me to help you with?",
                "title": "Chat",
                "series": [],
                "is_fav": False,
                "responseType": "Chat"
            }
        
        # Step 1: Extract basic parameters from prompt with chat history context
        query_params = extract_query_parameters(prompt, chat_history)
        print(f"Extracted parameters: {query_params}")
        
        # Step 2: Fetch relevant data
        data = await fetch_data_from_influxdb(query_params)
        print(f"Fetched data with {len(data.get('series', []))} series")
        
        # Step 3: Generate unified response using LLM
        result = await generate_unified_response(prompt, query_params, data, chat_history)
        
        print(f"Generated response with title: {result.get('title', 'No title')}")
        return result
        
    except Exception as e:
        print(f"Error during prompt analysis: {e}")
        return {
            "description": f"I encountered an error processing your request: {str(e)}",
            "title": "Error",
            "series": [],
            "is_fav": False
        }

# --- Utility Functions ---

def load_graph_templates() -> List[Dict[str, Any]]:
    """Load graph templates from saved files."""
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
    """Save a graph to the graphs.json file."""
    try:
        existing_graphs = load_graph_templates()
        
        graph_to_save = {
            "title": graph_data.get("title", "Untitled Graph"),
            "series": graph_data.get("series", []),
            "is_fav": graph_data.get("is_fav", False)
        }
        
        if "description" in graph_data:
            graph_to_save["description"] = graph_data["description"]
        
        # Check if graph with same title exists
        title_exists = False
        for i, existing_graph in enumerate(existing_graphs):
            if existing_graph.get("title") == graph_to_save["title"]:
                existing_graphs[i] = graph_to_save
                title_exists = True
                break
        
        if not title_exists:
            existing_graphs.append(graph_to_save)
        
        # Save to file
        with open(GRAPH_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_graphs, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully saved graph: {graph_to_save['title']}")
        return True
        
    except Exception as e:
        print(f"Error saving graph to file: {e}")
        return False

# --- Worker Classes for UI Integration ---

class ChatWorker(QThread):
    """Worker thread for running AI calls in the background."""
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
        """Execute the AI call in the background."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(analyze_prompt(self.chat_history))
            loop.close()
            
            desc = result.get("description", "")
            title = result.get("title", "")
            series = result.get("series", [])
                
        except Exception as e:
            print(f"Error processing prompt: {e}")
            desc = f"Sorry, I encountered an error processing your request: {str(e)}"
            title = "Error"
            series = []

        self.result_ready.emit(desc, title, series)

# --- FastAPI Helper Functions ---

def call_openai(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """Helper function for FastAPI endpoints to call the AI."""
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(analyze_prompt(chat_history))
        loop.close()
        
        print(f"Generated response with {len(result.get('series', []))} data series")
        return result
        
    except Exception as e:
        print(f"Error in call_openai: {e}")
        return {
            "description": f"Error processing request: {str(e)}",
            "title": "Error",
            "series": [],
            "is_fav": False
        }

async def analyze_prompt_with_timeout(chat_history: List[Dict[str, str]], timeout: int = 60) -> Dict[str, Any]:
    """Wrapper around analyze_prompt with timeout support."""
    try:
        return await asyncio.wait_for(analyze_prompt(chat_history), timeout=timeout)
    except asyncio.CancelledError:
        print("AI request was cancelled")
        return {
            "description": "The request was cancelled by the user.",
            "title": "Request Cancelled", 
            "series": [],
            "is_fav": False
        }
    except asyncio.TimeoutError:
        print(f"AI request timed out after {timeout} seconds")
        return {
            "description": f"The request took too long and timed out. Please try again with a simpler request.",
            "title": "Request Timeout",
            "series": [],
            "is_fav": False
        }
    except Exception as e:
        print(f"Error in analyze_prompt_with_timeout: {e}")
        return {
            "description": f"Error processing your request: {str(e)}",
            "title": "Error",
            "series": [],
            "is_fav": False
        }

# --- Legacy Compatibility Functions ---

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
