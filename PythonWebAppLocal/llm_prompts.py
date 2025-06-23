# LLM Prompt Templates for IDES Application
# This file contains structured prompts to ensure consistent and accurate LLM responses

import json

QUERY_ANALYSIS_PROMPT = """
You are a query analysis assistant for a sensor data visualization system. 

Analyze the user's request and return ONLY a valid JSON response with these exact fields:

{
  "response_type": "<one of: Graph, Analysis, Forecast, Floorplan, General>",
  "metrics": ["<array of sensor metrics like temperature, humidity, rainfall>"],
  "location": "<location name or null>",
  "time_window": "<time period like 1h, 24h, 7d, 30d>",
  "confidence": <0.0-1.0 confidence score>
}

Response Type Guidelines:
- Graph: User wants visual charts/plots (keywords: graph, plot, chart, visualize, show)
- Analysis: User wants text analysis of data (keywords: analyze, explain, describe, what)
- Forecast: User wants predictions (keywords: forecast, predict, future, projection)
- Floorplan: User wants location/floor visualization (keywords: floor, map, layout, where)
- General: Other queries or general conversation

Metric Detection:
- Look for: temperature/temp, humidity, rainfall/rain, pressure, etc.
- Return actual sensor names, not query words

Location Detection:
- Look for any mentioned cities or regions: Chicago, San Diego, New York, etc.
- If multiple locations mentioned, include all of them
- Return as string for single location, array for multiple locations

Time Window Detection:
- Look for specific numbers: "30 days" → "30d", "7 days" → "7d", "2 weeks" → "14d"
- Look for patterns: "past week" → "7d", "last month" → "30d", "past year" → "365d"
- hour/hourly → 1h
- day/daily → 24h  
- week/weekly → 7d
- month/monthly → 30d
- Pay special attention to numbers followed by time units (e.g., "3 days", "12 hours")
- Default to 24h ONLY if no time period is mentioned

User query: "{prompt}"

Respond with valid JSON only:
"""

GRAPH_GENERATION_PROMPT = """
You are a data visualization expert. Create metadata for a graph based on user requirements and available data.

Return ONLY valid JSON with these exact fields:

{
  "title": "<descriptive title for the graph>",
  "description": "<brief explanation of what the graph shows>",
  "chart_type": "<one of: line, bar, scatter, area>"
}

Guidelines:
- Title should be descriptive and include metrics, location, time period
- Description should explain what users will see in the graph
- Chart type should match the data:
  - line: time series, trends over time
  - bar: comparisons, categorical data
  - scatter: correlations, relationships
  - area: cumulative data, filled regions

User request: "{prompt}"
Metrics: {metrics}
Location: {location}
Time period: {time_window}

Respond with valid JSON only:
"""

ANALYSIS_PROMPT = """
You are a data analyst for sensor monitoring systems. Provide clear insights based on the data.

Data Summary: {data_summary}
User Request: "{prompt}"
Location: {location}
Time Period: {time_window}

Instructions:
- Focus on trends, patterns, and anomalies
- Use plain text, no markdown formatting
- Be specific about values and time periods
- Highlight important insights for the user's question
- Keep response under 300 words
- Use technical accuracy but accessible language

Provide your analysis:
"""

FORECAST_PROMPT = """
You are a forecasting expert for sensor data systems. Provide predictions based on data trends.

Trend Analysis: {trend_summary}
User Request: "{prompt}"
Location: {location}

Instructions:
- Explain expected future values based on current trends
- Mention confidence levels and factors affecting predictions
- Use plain text, no markdown formatting
- Be specific about timeframes and expected ranges
- Keep response under 250 words
- Focus on practical implications

Provide your forecast:
"""

GRAPH_VALIDATION_PROMPT = """
You are a data validation expert. Check if the provided graph data follows the required schema.

Required Schema:
- title: string (1-100 chars)
- description: string (1-500 chars)  
- responseType: one of [Graph, Analysis, Forecast, Floorplan, General]
- series: array of objects with:
  - label: string (1-50 chars)
  - x: array of strings/numbers (1-1000 items)
  - y: array of numbers (1-1000 items, same length as x)

Return validation result as JSON:
{
  "valid": true/false,
  "errors": ["list of specific errors if any"],
  "corrected_data": {<corrected data if fixable>}
}

Data to validate: {graph_data}

Respond with validation JSON only:
"""

ERROR_RECOVERY_PROMPT = """
You are an error recovery assistant. The system encountered an error processing the user's request.

Error: {error_message}
User Request: "{user_prompt}"

Provide a helpful response that:
- Acknowledges the issue
- Suggests what the user can try instead
- Offers alternative ways to get the information they need
- Maintains a professional, helpful tone
- Keep under 100 words

Your response:
"""

# Prompt template functions
def get_query_analysis_prompt(prompt: str, chat_history: list = None) -> str:
    """Get formatted query analysis prompt with optional chat history context."""
    
    # Build context from chat history if available
    context_text = ""
    if chat_history and len(chat_history) > 1:
        # Get recent conversation context (last 3-4 exchanges)
        recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history[:-1]  # Exclude current message
        context_items = []
        for msg in recent_history:
            role = msg.get("role", "")
            content = msg.get("content", "").strip()
            if content and role in ["user", "assistant"]:
                context_items.append(f"{role}: {content[:100]}...")  # Truncate long messages
        
        if context_items:
            context_text = f"\nPrevious conversation context:\n{chr(10).join(context_items)}\n"
    
    # Update the prompt template to include context
    enhanced_prompt = QUERY_ANALYSIS_PROMPT.replace(
        'User query: "{prompt}"',
        f'{context_text}Current user query: "{prompt}"'
    )
    
    return enhanced_prompt.format(prompt=prompt)

def get_graph_generation_prompt(prompt: str, metrics: list, location: str, time_window: str) -> str:
    """Get formatted graph generation prompt."""
    return GRAPH_GENERATION_PROMPT.format(
        prompt=prompt,
        metrics=metrics,
        location=location or "Not specified",
        time_window=time_window
    )

def get_analysis_prompt(prompt: str, data_summary: str, location: str, time_window: str) -> str:
    """Get formatted analysis prompt."""
    return ANALYSIS_PROMPT.format(
        prompt=prompt,
        data_summary=data_summary,
        location=location or "Not specified", 
        time_window=time_window
    )

def get_forecast_prompt(prompt: str, trend_summary: str, location: str) -> str:
    """Get formatted forecast prompt."""
    return FORECAST_PROMPT.format(
        prompt=prompt,
        trend_summary=trend_summary,
        location=location or "Not specified"
    )

def get_validation_prompt(graph_data: dict) -> str:
    """Get formatted validation prompt."""
    return GRAPH_VALIDATION_PROMPT.format(graph_data=json.dumps(graph_data, indent=2))

def get_error_recovery_prompt(error_message: str, user_prompt: str) -> str:
    """Get formatted error recovery prompt."""
    return ERROR_RECOVERY_PROMPT.format(
        error_message=error_message,
        user_prompt=user_prompt
    )
