# backend/main.py
#
# This is the main FastAPI application server that provides the REST API endpoints
# for the sensor data visualization dashboard. It handles:
# - Serving the frontend static files (HTML, CSS, JS)
# - Managing graph data persistence (JSON file storage)
# - Processing chat/analysis requests via LLM integration
# - CRUD operations for saved graphs (create, read, update, delete)
# - Cross-origin resource sharing (CORS) for frontend communication

# ─── Core Imports ──────────────────────────────────────────────────────────
from dotenv import load_dotenv, find_dotenv
import os, json, logging
from pathlib import Path
from typing import List, Dict, Any

# ─── FastAPI Framework Imports ─────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Environment Setup ─────────────────────────────────────────────────────
# Load environment variables from .env file
# find_dotenv() searches up the directory tree for .env files
load_dotenv(find_dotenv(raise_error_if_not_found=False))

# ─── Logging Configuration ─────────────────────────────────────────────────
# Set up logging for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logging.getLogger("uvicorn").handlers.clear()  # Prevent uvicorn log duplication
logger = logging.getLogger("backend")

# Log important startup information
logger.info(f"🔑 OPENAI_API_KEY = {os.getenv('OPENAI_API_KEY')!r}")
logger.info(f"📦 Running from CWD = {os.getcwd()!r}")

# ─── Import Application Modules ────────────────────────────────────────────
# Import after env loading so modules can access environment variables
from workers import analyze_prompt

# ─── File Path Configuration ───────────────────────────────────────────────
# Set up paths for data storage and static file serving
ROOT = Path(__file__).parent           # /backend directory
GRAPH_STORE = ROOT / "graphs.json"     # JSON file for persistent graph storage
STATIC_FOLDER = ROOT.parent / "static" # Frontend files (HTML, CSS, JS)

# ─── FastAPI Application Setup ─────────────────────────────────────────────
# Create main FastAPI application instance
app = FastAPI(title="Sensor Dashboard API")

# Mount static files for frontend (serves HTML, CSS, JS, images)
app.mount("/static", StaticFiles(directory=STATIC_FOLDER), name="static")

# Enable CORS for frontend communication
# Allows all origins, methods, and headers for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Allow requests from any domain
    allow_methods=["*"],    # Allow all HTTP methods
    allow_headers=["*"],    # Allow all headers
)

# ─── Request/Response Models ───────────────────────────────────────────────
# Pydantic models define the structure of API request/response data
# These models provide automatic validation and documentation

class Graph(BaseModel):
    """
    Model for graph data structure.
    Used when saving new graphs to persistent storage.
    """
    title: str                      # Display title for the graph
    series: List[Dict[str, Any]]   # Array of data series (x/y coordinates, labels)
    is_fav: bool = False           # Whether graph is marked as favorite

class FavBody(BaseModel):
    """
    Model for favorite/unfavorite requests.
    Used to toggle the favorite status of existing graphs.
    """
    index: int      # Index of graph in the graphs array
    is_fav: bool    # New favorite status

class DeleteBody(BaseModel):
    """
    Model for graph deletion requests.
    Used to delete graphs from persistent storage.
    """
    index: int      # Index of graph to delete

class AnalyzeBody(BaseModel):
    """
    Model for chat/analysis requests.
    Contains the conversation history for LLM processing.
    """
    chat_history: List[Dict[str, str]]  # Array of {role: "user"/"assistant", content: "..."}

# ─── Data Persistence Helper Functions ─────────────────────────────────────

def _load_graphs() -> list:
    """
    Load saved graphs from JSON file.
    
    Returns:
        List of graph dictionaries, or empty list if file doesn't exist
        
    This function handles file I/O for reading persistent graph data.
    If the graphs.json file doesn't exist (first run), returns empty list.
    """
    if GRAPH_STORE.exists():
        return json.loads(GRAPH_STORE.read_text())
    else:
        return []

def _save_graphs(data: list) -> None:
    """
    Save graphs list to JSON file.
    
    Args:
        data: List of graph dictionaries to save
        
    This function handles file I/O for writing persistent graph data.
    Uses pretty-printing (indent=2) for human-readable JSON.
    """
    GRAPH_STORE.write_text(json.dumps(data, indent=2))

# ─── API Route Definitions ─────────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(body: AnalyzeBody):
    """
    Main chat/analysis endpoint.
    
    Processes user messages through the LLM pipeline to generate:
    - Graph visualizations with data
    - Text analysis and explanations  
    - General conversation responses
    
    Args:
        body: AnalyzeBody containing chat_history array
        
    Returns:
        Structured response with title, description, series data, and type
        
    Error Handling:
        - Catches all exceptions and returns them as structured error responses
        - Logs full tracebacks for debugging
        - Returns HTTP 200 with error content (not HTTP 500) for frontend handling
    """
    try:
        # Process the chat history through the LLM pipeline
        return await analyze_prompt(body.chat_history)
    except Exception as e:
        # Log detailed error information for debugging
        import traceback
        logging.error("Analyze failed:\n%s", traceback.format_exc())

        # Return structured error response (HTTP 200 for frontend compatibility)
        return {
            "title":        "Error", 
            "description":  f"{type(e).__name__}: {e}",
            "series":       [],
            "responseType": "Error",
            "is_fav":       False,
        }

@app.get("/", response_class=FileResponse)
def root():
    """
    Serve the main frontend application.
    
    Returns:
        The index.html file from the static folder
        
    This endpoint serves the main web application when users visit the root URL.
    """
    return STATIC_FOLDER / "index.html"

@app.get("/graphs.json")
def graphs():
    """
    Get all saved graphs.
    
    Returns:
        JSON array of all saved graph objects
        
    This endpoint provides the current list of saved graphs for the frontend
    to display in the home and graphs pages.
    """
    return _load_graphs()

@app.post("/api/add_graph")
def add_graph(g: Graph):
    """
    Save a new graph to persistent storage.
    
    Args:
        g: Graph object with title, series data, and favorite status
        
    Returns:
        Success confirmation with the new graph's index
        
    This endpoint is called when:
    - User generates a new graph via chat
    - Graph needs to be saved to the persistent collection
    """
    data = _load_graphs()
    data.append(g.model_dump())  # Convert Pydantic model to dict
    _save_graphs(data)
    return {"ok": True, "index": len(data) - 1}

@app.post("/api/favorite")
def favorite(b: FavBody):
    """
    Toggle favorite status of an existing graph.
    
    Args:
        b: FavBody with graph index and new favorite status
        
    Returns:
        Success confirmation or 404 error
        
    This endpoint handles the favorite/unfavorite functionality:
    - Updates the is_fav field of the specified graph
    - Saves the updated data to persistent storage
    """
    data = _load_graphs()
    if 0 <= b.index < len(data):
        data[b.index]["is_fav"] = b.is_fav
        _save_graphs(data)
        return {"ok": True}
    else:
        raise HTTPException(404, "index out of range")

@app.post("/api/delete")
def delete(b: DeleteBody):
    """
    Delete a graph from persistent storage.
    
    Args:
        b: DeleteBody with the index of graph to delete
        
    Returns:
        Success confirmation or 404 error
        
    This endpoint handles graph deletion:
    - Removes the graph at the specified index
    - Saves the updated data to persistent storage
    - Note: This shifts all subsequent indices down by 1
    """
    data = _load_graphs()
    if 0 <= b.index < len(data):
        data.pop(b.index)
        _save_graphs(data)
        return {"ok": True}
    else:
        raise HTTPException(404, "index out of range")
