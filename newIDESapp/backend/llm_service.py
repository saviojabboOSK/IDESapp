# backend/llm_service.py
# 
# This module handles all interactions with the OpenAI LLM (Large Language Model).
# It provides the core functionality for:
# - Building context-aware prompts for the LLM
# - Making API calls to OpenAI's chat completion endpoint
# - Parsing and structuring LLM responses for graphs, analysis, and chat
# - Converting raw LLM output into standardized response formats

import os, json, re
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv, find_dotenv

# ─── Load environment variables (.env file) ────────────────────────────────
# This ensures API keys and configuration are loaded before importing OpenAI
load_dotenv(find_dotenv(raise_error_if_not_found=False))

from openai import AsyncOpenAI, OpenAIError

# ─── OpenAI Configuration ──────────────────────────────────────────────────
# Load API key from environment - this is required for OpenAI API access
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set; add it to .env or export it")

# Model configuration - can be overridden in .env file
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-preview")

# Initialize async OpenAI client for making API calls
_CLIENT = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Optional local model example (commented-out)
# Uncomment these lines to use a local LLM server like Ollama instead of OpenAI
# from openai import AsyncOpenAI
# _CLIENT = AsyncOpenAI(base_url=os.getenv("LOCAL_LLM_URL"), api_key="ollama")
# MODEL_NAME = os.getenv("LOCAL_LLM_MODEL")

# ─── Main LLM Prompt Template ──────────────────────────────────────────────
# This template is used for ALL LLM interactions in the system.
# It provides structured instructions for handling different types of user requests:
# - Graph/visualization generation with proper data formatting
# - Analysis and explanations
# - General conversation
# The template uses Python string formatting to inject dynamic context
MAIN_TEMPLATE = """
Your name is IDES, and you are an AI assistant for a sensor data visualization system. Analyze the user's request and provide appropriate responses. Always be friendly to the user and provide helpful, accurate information.

Do not tolerate any form of abuse or harassment. If the user is abusive, politely inform them that such behavior is not acceptable and suggest they rephrase their request.

- If the user answers with a short confirmation such as "yes", immediately proceed with the requested graph or analysis without asking follow-up questions.

If the user asks for more than one type of response at once (e.g., a graph and an analysis), you may ask "I see you want ____ and ____, which would you like to do first?" and then provide the response for that part after the user responds. 
This does not include if the user asks for two metrics or locations in a single graph request, which you should handle as described below.

FOR WHEN THE USER ASKS FOR A GRAPH:

When you are asked for a time period, use relative timing. For example, if the user asks for past 30 days, go from -30 (30 days ago) to 0 (today).

User Request: {prompt}
Available Metrics: {metrics}
Time Window: {time_window}
Data Summary: {data_summary}
Recent Chat History: {chat_history}

Instructions:
- If the user wants a graph/chart/visualization, respond with JSON in this EXACT format:
  {{
    "response_type": "graph",
    "title": "descriptive title for the visualization",
    "analysis": "brief explanation of what the data shows", 
    "series": [
      {{
        "label": "<Location> <Metric> (<Unit>)",
        "x": [<time points>],
        "y": [<values>]
      }},
      // ...repeat for each location and metric requested
    ]
  }}

CRITICAL LABELING RULES FOR MULTIPLE LOCATIONS/METRICS:
- ALWAYS include the location name in each series label
- Format: "<Location> <Metric> (<Unit>)" - e.g., "Chicago Temperature (°F)", "New York Humidity (%)"
- For multiple locations with same metric: Create separate series for each location
- For multiple metrics per location: Create separate series for each metric per location
- NEVER use generic labels like "Temperature" or "Humidity" when multiple locations are involved

EXAMPLES OF PROPER MULTI-LOCATION LABELING:
- Single location, multiple metrics: "San Diego Temperature (°F)", "San Diego Humidity (%)"
- Multiple locations, single metric: "Chicago Temperature (°F)", "New York Temperature (°F)"
- Multiple locations, multiple metrics: "Chicago Temperature (°F)", "Chicago Humidity (%)", "New York Temperature (°F)", "New York Humidity (%)"

// The above are EXAMPLES. Always generalize to any location(s) and metric(s) the user requests.

CRITICAL SERIES REQUIREMENTS:
- Each series MUST have "label", "x", and "y" fields
- "x" array: time points (numbers 1,2,3... for hours/days OR date strings like "2023-10-01")
- "y" array: actual numeric values matching the x array length
- For hypothetical data, generate realistic values for the requested location and metrics
- Always include proper units in labels: "Temperature (°F)", "Humidity (%)", "Rainfall (mm)", "Pressure (hPa)"
- Generate appropriate number of data points based on time window:
  * 1 hour: 1 point
  * 24 hours: 24 points (hourly)
  * 7 days: 7 points (daily)
  * 30 days: 30 points (daily)
  * For "past X days", use X number of points

- If the user wants analysis/explanation, respond with JSON in this format:
  {{
    "response_type": "analysis", 
    "title": "Analysis Title",
    "content": "detailed analysis text"
  }}

- For general conversation, respond naturally in plain text.

ALWAYS generate complete data arrays with realistic values when creating graphs. Never return empty series or incomplete data structures.

Response:
"""

# ─── LLM API Functions ─────────────────────────────────────────────────────

async def call_llm(context: str) -> str:
    """
    Low-level wrapper for making OpenAI API calls.
    
    Args:
        context: The complete prompt string to send to the LLM
        
    Returns:
        The LLM's response as a string
        
    Raises:
        RuntimeError: If the OpenAI API call fails (wraps OpenAIError)
        
    This function handles:
    - Making the actual API call to OpenAI
    - Setting appropriate temperature (0.5 for balanced creativity/consistency)
    - Setting max_tokens limit (16384 for detailed graph data)
    - Converting OpenAI errors into RuntimeError with clean messages
    """
    try:
        resp = await _CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": context}],
            temperature=0.5,  # Balanced temperature for creative but consistent responses
            max_tokens=16384,  # High limit to allow detailed graph data generation
        )
        return resp.choices[0].message.content.strip()
    except OpenAIError as e:
        # Convert OpenAI errors to clean RuntimeError for upstream handling
        raise RuntimeError(f"LLM request failed: {e}") from e

# ─── Response Processing Functions ─────────────────────────────────────────

async def smart_response(
    prompt: str,
    metrics: List[str],
    time_window: str,
    data_summary: str,
    chat_history: List[Dict[str,str]],
) -> Dict[str,Any]:
    """
    Main function for processing user requests through the LLM.
    
    Args:
        prompt: The user's input/question
        metrics: List of available metrics (temperature, humidity, etc.)
        time_window: Time range for data (24h, 7d, 30d, etc.)
        data_summary: Summary of any database data retrieved
        chat_history: Previous conversation messages for context
        
    Returns:
        Structured response dictionary with:
        - title: Display title
        - description: Response text or analysis
        - series: Graph data (if applicable)
        - responseType: "Graph", "Analysis", or "Chat"
        - is_fav: Boolean for favorites system
        
    This function:
    1. Builds the complete context prompt
    2. Calls the LLM with the context
    3. Parses the LLM response (JSON or plain text)
    4. Converts to standardized response format
    """
    # Build the complete prompt with context
    ctx = _build_context(prompt, metrics, time_window, data_summary, chat_history)
    
    # Get raw response from LLM
    raw = await call_llm(ctx)
    
    # Clean up any markdown code blocks that might wrap JSON
    cleaned = re.sub(r"```(?:json)?|```", "", raw, flags=re.I).strip()

    # Try to parse as JSON first
    try:
        obj = json.loads(cleaned)
    except json.JSONDecodeError:
        # If not JSON, treat as plain chat response
        return _as_chat(cleaned)

    # Parse structured responses based on type
    rtype = obj.get("response_type", "").lower()
    
    if rtype == "graph":
        return {
            "title":        obj.get("title", "Visualization"),
            "description":  obj.get("analysis", obj.get("description", "")),
            "series":       obj.get("series", []),
            "responseType": "Graph",
            "is_fav":       False,
        }
    elif rtype == "analysis":
        return {
            "title":        obj.get("title", "Analysis"),
            "description":  obj.get("content", obj.get("description", "")),
            "series":       [],
            "responseType": "Analysis",
            "is_fav":       False,
        }
    else:
        # Fallback to chat format for unknown types
        return _as_chat(cleaned)

def _as_chat(text: str) -> Dict[str,Any]:
    """
    Convert plain text response to standardized chat format.
    
    Args:
        text: The response text from the LLM
        
    Returns:
        Standardized response dictionary for chat messages
    """
    return {
        "title":        "Chat",
        "description":  text,
        "series":       [],
        "responseType": "Chat",
        "is_fav":       False,
    }

class _SafeDict(dict):
    """
    Dictionary subclass that handles missing keys gracefully.
    
    When a key is missing (like an unused placeholder in the template),
    it returns the key wrapped in braces instead of raising KeyError.
    This prevents template formatting errors when not all placeholders are used.
    """
    def __missing__(self, key):
        return "{%s}" % key

def _build_context(
    prompt: str,
    metrics: List[str],
    time_window: str,
    data_summary: str,
    chat_history: List[Dict[str, str]],
) -> str:
    """
    Build the complete context prompt for the LLM.
    
    Args:
        prompt: Current user input
        metrics: Available metrics list
        time_window: Time range for data
        data_summary: Summary of database data
        chat_history: Previous conversation messages
        
    Returns:
        Complete formatted prompt string ready for LLM
        
    This function:
    1. Formats recent chat history (last 12 messages, up to 300 chars each)
    2. Excludes graph data dumps from history to save tokens
    3. Fills the main template with all context variables
    4. Uses SafeDict to handle any unused template placeholders
    """
    # Format recent chat history for context
    # Take last 12 messages, truncate content to 300 chars, exclude graph data
    hist = "\n".join(
        f"{m['role']}: {m['content'][:300]}"
        for m in chat_history[-12:]
        if not m["content"].startswith("[[GRAPH_DATA]]")
    )

    # Prepare template variables
    placeholders = {
        "prompt":       prompt,
        "metrics":      ", ".join(metrics) if metrics else "none",
        "time_window":  time_window,
        "data_summary": data_summary or "no external data",
        "chat_history": hist or "none",
    }
    
    # Fill template with SafeDict to handle missing placeholders gracefully
    return MAIN_TEMPLATE.format_map(_SafeDict(placeholders))
