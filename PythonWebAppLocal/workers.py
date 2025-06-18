# workers.py - Consolidated AI and response handling
# This file contains all the functionality for AI interactions and processing responses
# for graph generation in our application.

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

# --- Constants and Configuration ---
# These paths help locate important files and set up configuration
GRAPH_STORE_PATH = os.path.join(os.path.dirname(__file__), "graphs.json")  # Stores user graphs
EXAMPLE_GRAPHS_PATH = os.path.join(os.path.dirname(__file__), "examplegraphs.json")  # Example graphs
GRAPH_MAX = 30  # Maximum number of data points to include in a graph (prevents overloading)
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")  # Directory for caching data
os.makedirs(CACHE_DIR, exist_ok=True)  # Create cache directory if it doesn't exist

# --- Template and Data Management ---
def load_graph_templates() -> List[Dict[str, Any]]:
    """
    Loads graph templates from saved files to give the AI examples of what we want.
    
    This helps the AI understand what format to generate data in, making responses
    more accurate and consistent with what our application expects.
    
    Returns:
        A list of graph templates that can be used as examples for the AI
    """
    try:
        # First try to use graphs.json which includes user-created graphs
        if os.path.exists(GRAPH_STORE_PATH):
            with open(GRAPH_STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        # If that doesn't exist, use our built-in example graphs
        elif os.path.exists(EXAMPLE_GRAPHS_PATH):
            with open(EXAMPLE_GRAPHS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        # If neither exists, return a simple default template
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

def create_system_prompt_with_template(template: Dict[str, Any]) -> str:
    """
    Creates instructions for the AI that include an example of what we want.
    
    By showing the AI an example of our expected output format, we can get more
    consistent and accurate results. This is like giving the AI a template to fill in.
    
    Args:
        template: An example graph to show the AI what format we want
        
    Returns:
        A string containing instructions for the AI with the template embedded
    """
    return (
        "You are a data visualization assistant. Your task is to generate data for plots "
        "based on user requests. Respond with accurate and well-formatted JSON only. "
        f"Follow this template structure exactly:\n{json.dumps(template, indent=2)}\n"
        "Adapt the template to match the user's request while maintaining the same JSON format. "
        "Do not include explanatory text, markdown formatting, or code blocks in your response, "
        "just return the raw JSON object."
    )

def find_relevant_template(prompt: str, templates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Picks a template that matches what the user is asking for.
    
    This helps the AI generate more relevant responses by starting with a
    template that's similar to what the user wants.
    
    Args:
        prompt: The user's request
        templates: Available graph templates to choose from
        
    Returns:
        The most relevant template for the user's request
    """
    # These keywords help match user requests with appropriate templates
    keywords = ["temperature", "humidity", "weather", "sales", "stock", "price", 
                "energy", "performance", "time", "count", "frequency", "scatter"]
    
    prompt_lower = prompt.lower()
    relevant_templates = []
    
    # Look for templates with titles that match keywords in the prompt
    for template in templates:
        template_title = template.get("title", "").lower()
        for keyword in keywords:
            if keyword in prompt_lower and keyword in template_title:
                relevant_templates.append(template)
                break
    
    # Choose a relevant template or fall back to a random one if none match
    if relevant_templates:
        return random.choice(relevant_templates)
    elif templates:
        return random.choice(templates)
    else:
        # Default template if no templates are available
        return {
            "title": "Sample Chart",
            "series": [
                {
                    "label": "Data",
                    "x": [1, 2, 3, 4, 5],
                    "y": [10, 20, 15, 25, 30]
                }
            ]
        }

def validate_graph_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Checks and fixes graph data to make sure it will work with our application.
    
    This prevents errors from invalid data by ensuring the structure is correct
    and all the necessary fields are present.
    
    Args:
        data: The graph data to validate
        
    Returns:
        Clean, validated graph data that will work with our application
    """
    # Start with a basic structure and fill in what we can from the data
    result = {
        "description": data.get("description", ""),
        "title": data.get("title", "Chart"),
        "series": data.get("series", [])
    }
    
    # Check and fix each series in the graph
    for item in result["series"]:
        # Make sure x and y arrays are the same length
        if len(item.get('x', [])) != len(item.get('y', [])):
            max_len = min(len(item.get('x', [])), len(item.get('y', [])))
            item['x'] = item.get('x', [])[:max_len]
            item['y'] = item.get('y', [])[:max_len]
            
        # Make sure there's a label for the series
        if not item.get('label'):
            item['label'] = 'Data'
            
        # Limit data points for performance
        if len(item.get('x', [])) > GRAPH_MAX:
            item['x'] = item['x'][:GRAPH_MAX]
            item['y'] = item['y'][:GRAPH_MAX]
    
    return result

# --- InfluxDB Data Fetching (Commented Out) ---
"""
# This section would be used to fetch real data from InfluxDB
# based on keywords generated by the LLM

from influxdb_client import InfluxDBClient
import re

# InfluxDB connection settings
URL    = os.getenv("INFLUXDB_URL", "http://localhost:8086")
TOKEN  = os.getenv("INFLUXDB_TOKEN", "<YOUR_TOKEN>")
ORG    = os.getenv("INFLUXDB_ORG", "<YOUR_ORG>")
BUCKET = os.getenv("INFLUXDB_BUCKET", "sensors")

# Create InfluxDB client
_client    = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
_query_api = _client.query_api()

async def extract_keywords_from_prompt(prompt: str) -> List[str]:
    '''
    Use the LLM to extract relevant keywords from the user's prompt.
    This helps identify what data they might be looking for.
    '''
    client = AsyncOpenAI(
        base_url='http://localhost:11434/v1/',
        api_key='ollama'
    )
    
    system_message = (
        "Extract key search terms from the user's query about sensor data. "
        "Return ONLY a JSON array of strings with the keywords. "
        "Example: if the user asks about 'temperature in the server room yesterday', "
        "return: ['temperature', 'server room', 'yesterday']"
    )
    
    response = await client.chat.completions.create(
        model="llama3.2",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json"}
    )
    
    try:
        keywords = json.loads(response.choices[0].message.content)
        return keywords if isinstance(keywords, list) else []
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return []

async def fetch_influxdb_data(keywords: List[str], time_window: str = "24h") -> Dict[str, Any]:
    '''
    Fetch data from InfluxDB based on extracted keywords.
    
    Args:
        keywords: List of keywords to search for in measurements, tags, etc.
        time_window: Time range to query (e.g., "24h", "7d", etc.)
        
    Returns:
        Formatted graph data with series from InfluxDB
    '''
    # Build filters from keywords
    measurement_filters = []
    tag_filters = []
    
    for keyword in keywords:
        # Clean the keyword for safe use in queries
        clean_keyword = re.sub(r'[^a-zA-Z0-9_]', '', keyword)
        if clean_keyword:
            # Create measurement filter
            measurement_filters.append(f'r["_measurement"] =~ /{clean_keyword}/')
            # Create tag filters
            tag_filters.append(f'r["location"] =~ /{clean_keyword}/')
            tag_filters.append(f'r["sensor"] =~ /{clean_keyword}/')
    
    # If no valid keywords, return empty data
    if not measurement_filters:
        return {"description": "No valid search terms found", "title": "", "series": []}
    
    # Build the Flux query with our keyword filters
    measurement_filter = " or ".join(measurement_filters)
    tag_filter = " or ".join(tag_filters)
    
    flux = f'''
    from(bucket:"{BUCKET}")
      |> range(start: -{time_window})
      |> filter(fn: (r) => {measurement_filter} or {tag_filter})
      |> keep(columns: ["_time", "_value", "_measurement", "location", "sensor"])
    '''
    
    try:
        # Execute query
        tables = _query_api.query(flux)
        
        # Process results
        series_data = {}
        for table in tables:
            for record in table.records:
                # Create a unique identifier for each series
                measurement = record.get_measurement()
                tags = f"{record.values.get('location', '')}/{record.values.get('sensor', '')}"
                series_id = f"{measurement}-{tags}"
                
                # Initialize series if not exists
                if series_id not in series_data:
                    series_data[series_id] = {
                        "label": f"{measurement} ({tags})",
                        "x": [],
                        "y": []
                    }
                
                # Add data point
                series_data[series_id]["x"].append(record.get_time().isoformat())
                series_data[series_id]["y"].append(record.get_value())
        
        # Format the result
        result = {
            "description": f"Data for {', '.join(keywords)}",
            "title": f"Sensor Data for {', '.join(keywords)}",
            "series": list(series_data.values())
        }
        
        return validate_graph_data(result)  # Validate before returning
        
    except Exception as e:
        print(f"Error querying InfluxDB: {e}")
        return {
            "description": f"Error fetching data: {str(e)}",
            "title": "",
            "series": []
        }

async def analyze_prompt_with_influxdb(prompt: str) -> Dict[str, Any]:
    '''
    Analyze prompt and fetch appropriate data from InfluxDB.
    
    This is the main function that would be called to process a user's request
    and return data from InfluxDB based on what they're asking for.
    '''
    # 1. Extract keywords from the prompt
    keywords = await extract_keywords_from_prompt(prompt)
    
    # 2. Determine the appropriate time window
    time_window = "24h"  # Default
    if any(word in prompt.lower() for word in ["week", "weekly"]):
        time_window = "7d"
    elif any(word in prompt.lower() for word in ["month", "monthly"]):
        time_window = "30d"
    elif any(word in prompt.lower() for word in ["hour", "hourly"]):
        time_window = "1h"
    
    # 3. Fetch data from InfluxDB
    return await fetch_influxdb_data(keywords, time_window)
"""

# --- LLM-based Graph Generation (Main Function) ---
async def analyze_prompt(prompt: str) -> Dict[str, Any]:
    """
    Takes a user's request and generates appropriate graph data.
    
    This is the main function that processes what the user is asking for
    and returns data to create a visualization.
    
    Args:
        prompt: The user's request for a graph or visualization
        
    Returns:
        A dictionary with description, title, and data series for the graph
    """
    # Configure AsyncOpenAI client for local Ollama instance
    client = AsyncOpenAI(
        base_url='http://localhost:11434/v1/',
        api_key='ollama'  # Required but ignored by Ollama
    )
    
    # Original OpenAI API configuration (commented out)
    # client = AsyncOpenAI()  # uses OPENAI_API_KEY env-var
    
    # Load graph templates and find a relevant one
    templates = await asyncio.to_thread(load_graph_templates)
    template = find_relevant_template(prompt, templates)
    
    # Create system prompt with the template
    system_message = create_system_prompt_with_template(template)
    
    # Call the LLM with template guidance
    try:
        # Make the API call to the language model
        response = await client.chat.completions.create(
            model="llama3.2",  # Using local Ollama model
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Lower temperature for more predictable outputs
            response_format={"type": "json"}  # Force JSON output without markdown
        )
        
        # Extract the raw content
        raw_content = response.choices[0].message.content
        
        # Parse the JSON response
        parsed = json.loads(raw_content)
        
        # Validate and return the result
        return validate_graph_data(parsed)
        
    except Exception as e:
        print(f"Error during LLM processing: {e}")
        return {
            "description": f"Error generating visualization: {str(e)}",
            "title": "",
            "series": []
        }

# --- ChatWorker: Background LLM Calls ---
class ChatWorker(QThread):
    """
    A worker thread that runs the AI call in the background so the UI doesn't freeze.
    
    This allows the application to stay responsive while waiting for the AI
    to generate data for a graph.
    """
    # Signal sent when results are ready (with description, title, and data series)
    result_ready = Signal(str, str, list)
    
    def __init__(self, chat_history):
        """
        Sets up the worker with chat history and initializes the AI client.
        
        Args:
            chat_history: List of previous messages between the user and AI
        """
        super().__init__()
        self.chat_history = chat_history
        
        # Original code using OpenAI API with API key (commented out)
        # import os
        # api_key = os.getenv("OPENAI_API_KEY")
        # if not api_key:
        #     print("ERROR: OPENAI_API_KEY environment variable not set in ChatWorker")
        #     raise ValueError("OPENAI_API_KEY environment variable not set")
        # else:
        #     print("OPENAI_API_KEY found in ChatWorker, initializing OpenAI client")
        # self.client = OpenAI(api_key=api_key)
        
        # Using Ollama with OpenAI API protocol for local model (llama3.2)
        print("Initializing OpenAI client with Ollama base URL for local LLM")
        self.client = OpenAI(
            base_url='http://localhost:11434/v1/',
            api_key='ollama'  # Required by the OpenAI SDK but ignored by Ollama
        )
        
    def run(self):
        """
        Executes the AI call in the background and sends results when done.
        
        This method runs in a separate thread, gets data from the AI,
        and then signals the main thread when results are ready.
        """
        # Extract the user's prompt from the chat history
        user_prompt = ""
        for message in self.chat_history:
            if message["role"] == "user":
                user_prompt = message["content"]
                break
        
        if not user_prompt:
            user_prompt = self.chat_history[-1]["content"] if self.chat_history else ""
        
        # Load graph templates
        templates = load_graph_templates()
        template = find_relevant_template(user_prompt, templates)
        
        # Create enhanced prompt with template
        system_message = create_system_prompt_with_template(template)
        
        # Prepare messages for the API call
        messages = [
            {"role": "system", "content": system_message}
        ]
        messages.extend(self.chat_history)
        
        try:
            # Call the LLM with the enhanced prompt
            completion = self.client.chat.completions.create(
                model="llama3.2",
                messages=messages,
                temperature=0.3,
                response_format={"type": "json"}  # Force JSON output without markdown
            )
            
            # Extract the raw content
            raw = completion.choices[0].message.content.strip()
                
        except Exception as e:
            print(f"Error connecting to Ollama: {e}")
            raw = '{"description": "Sorry, I could not connect to the local LLM.", "title": "", "series": []}'

        try:
            # Parse and validate the response
            parsed = json.loads(raw)
            data = validate_graph_data(parsed)
            
            desc = data.get("description", "")
            title = data.get("title", "")
            series = data.get("series", [])
                
        except Exception as e:
            print(f"Error parsing JSON from LLM response: {e}")
            print(f"Raw response: {raw}")
            desc = raw
            title = ""
            series = []

        # Send the results back to the main thread
        self.result_ready.emit(desc, title, series)

# --- call_openai: FastAPI Helper ---
def call_openai(chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    A helper function for FastAPI endpoints to call the AI and get results.
    
    This synchronous version is designed to be called from a web API endpoint,
    doing the same work as ChatWorker but returning the result directly.
    
    Args:
        chat_history: List of previous messages between the user and AI
        
    Returns:
        A dictionary with description, title, and data series for the graph
    """
    # Extract the user's prompt from the chat history
    user_prompt = ""
    for message in chat_history:
        if message["role"] == "user":
            user_prompt = message["content"]
            break
    
    if not user_prompt:
        user_prompt = chat_history[-1]["content"] if chat_history else ""
    
    # Load graph templates
    templates = load_graph_templates()
    template = find_relevant_template(user_prompt, templates)
    
    # Create enhanced prompt with template
    system_message = create_system_prompt_with_template(template)
    
    # Prepare messages for the API call
    messages = [
        {"role": "system", "content": system_message}
    ]
    messages.extend(chat_history)
    
    # Original code using OpenAI API with API key (commented out)
    # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Using Ollama with OpenAI API protocol for local model
    client = OpenAI(
        base_url='http://localhost:11434/v1/',
        api_key='ollama'  # Required but ignored by Ollama
    )
    
    try:
        # Call the LLM with the enhanced prompt
        response = client.chat.completions.create(
            model="llama3.2",
            messages=messages,
            temperature=0.3,
            response_format={"type": "json"}  # Force JSON output without markdown
        )
        
        # Extract the raw content
        raw = response.choices[0].message.content.strip()
            
    except Exception as e:
        print(f"Error connecting to Ollama: {e}")
        return {
            "description": f"Error connecting to LLM: {str(e)}",
            "title": "",
            "series": []
        }

    try:
        # Parse and validate the response
        parsed = json.loads(raw)
        return validate_graph_data(parsed)
        
    except Exception as e:
        print(f"Error parsing JSON from LLM response: {e}")
        print(f"Raw response: {raw}")
        return {"description": raw, "title": "", "series": []}
