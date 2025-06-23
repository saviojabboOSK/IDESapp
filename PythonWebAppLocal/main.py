import sys
import os
import json
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QScrollArea, QLineEdit, QFrame, QStackedWidget,
    QProgressBar
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, QTimer, QObject

from fastapi.staticfiles import StaticFiles

from qt_material import apply_stylesheet

from workers import ChatWorker, analyze_prompt, call_openai, analyze_prompt_with_timeout
from widgets.chat_entry import ChatEntry
from widgets.graph_card import GraphCard
from widgets.home_graph import HomeGraph
from widgets.multi_series_chat_entry import MultiSeriesChatEntry
from widgets.multi_series_graph_card import MultiSeriesGraphCard
from widgets.floor_page import FloorPage

# --- Imports: standard, PySide6, FastAPI, project modules ---
# Imports required libraries for GUI, API, and utilities.

# ─── FastAPI INTEGRATION ──────────────────────────────────────────────────────
import threading
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, ValidationError
from typing import List, Dict, Any

from fastapi.responses import JSONResponse


from influx_service import fetch_timeseries

import asyncio
from workers import call_openai, analyze_prompt_with_timeout


api = FastAPI()
# Export the FastAPI application as 'app' for Uvicorn
app = api

# serve static assets under /static
api.mount("/static", StaticFiles(directory="static"), name="static")
# 2) serve index.html at the root URL
@api.get("/", response_class=FileResponse)
async def root():
    return FileResponse(os.path.join("static", "index.html"))

@api.get("/graphs.json")
async def get_graphs():
    """Return the current graph list."""
    try:
        return JSONResponse(json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8")))
    except FileNotFoundError:
        return JSONResponse([], status_code=200)
    
class FavPayload(BaseModel):
    index: int
    is_fav: bool

@api.post("/api/favorite")
async def favorite(p: FavPayload):
    data = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8"))
    if 0 <= p.index < len(data):
        data[p.index]["is_fav"] = p.is_fav
        json.dump(data, open(GRAPH_STORE_PATH, "w", encoding="utf-8"), indent=2)
        return {"ok": True}
    raise HTTPException(400, "index out of range")

# ─── FastAPI: persist favourites & deletions ──────────────────────────────────

class FavBody(BaseModel):
    index: int | None = None        # either index ...
    title: str | None = None        # ... or unique title
    is_fav: bool

class DeleteBody(BaseModel):
    index: int | None = None
    title: str | None = None

@api.get("/graphs.json")
async def graph_list():
    """Return the latest saved graphs.json for the web UI."""
    try:
        return JSONResponse(json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8")))
    except FileNotFoundError:
        return JSONResponse([], status_code=200)

@api.post("/api/favorite")
async def favorite(body: FavBody):
    data = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8"))
    # locate entry
    if body.index is not None and 0 <= body.index < len(data):
        target = data[body.index]
    else:
        target = next((g for g in data if g["title"] == body.title), None)
    if target is None:
        raise HTTPException(404, "graph not found")
    target["is_fav"] = body.is_fav
    json.dump(data, open(GRAPH_STORE_PATH, "w", encoding="utf-8"), indent=2)
    return {"ok": True}

@api.post("/api/delete")
async def delete(body: DeleteBody):
    data = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8"))
    if body.index is not None and 0 <= body.index < len(data):
        data.pop(body.index)
    else:
        # drop first match on title
        data = [g for g in data if g["title"] != body.title]
    json.dump(data, open(GRAPH_STORE_PATH, "w", encoding="utf-8"), indent=2)
    return {"ok": True}

class DeletePayload(BaseModel):
    index: int

@api.post("/api/delete")
async def delete(p: DeletePayload):
    data = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8"))
    if 0 <= p.index < len(data):
        data.pop(p.index)
        json.dump(data, open(GRAPH_STORE_PATH, "w", encoding="utf-8"), indent=2)
        return {"ok": True}
    raise HTTPException(400, "index out of range")


api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def _start_api():
    import uvicorn
    uvicorn.run(api, host="0.0.0.0", port=8000, log_level="warning")

class AnalyzeRequest(BaseModel):
    chat_history: List[Dict[str, str]]

def is_valid_graph(graph):
    if not isinstance(graph, dict):
        return False
    if not {"title", "series", "is_fav"}.issubset(graph):
        return False
    if not isinstance(graph["series"], list) or not graph["series"]:
        return False
    for s in graph["series"]:
        if not isinstance(s, dict):
            return False
        if not {"label", "x", "y"}.issubset(s):
            return False
        if not isinstance(s["x"], list) or not isinstance(s["y"], list):
            return False
        if len(s["x"]) != len(s["y"]) or len(s["x"]) == 0:
            return False
    return True

# --- API Endpoints: Home, Graphs, Favorite, Delete ---
# Defines endpoints for serving the main page, graphs data, favoriting, and deleting graphs.

@api.post("/api/analyze")
async def analyze(req: Request):
    try:
        data = await req.json()
        print("/api/analyze received body:", data)  # Debug print

        # Unified handling of prompt & chat history
        chat_history = data.get("chat_history", [])
        if not isinstance(chat_history, list):
            chat_history = []

        # Include one-off prompt if provided
        prompt = data.get("prompt", "").strip()
        if prompt:
            chat_history.append({ "role": "user", "content": prompt })

        if not chat_history:
            raise HTTPException(400, "Missing prompt")

        # Call the AI service with full chat history
        raw_result = await analyze_prompt(chat_history)
        print(f"OpenAI raw call result: {raw_result}")
        # Extract response fields with fallbacks
        description = raw_result.get("description", f"Analysis of data related to {prompt}")
        title = raw_result.get("title", f"Data for {prompt}")
        series = raw_result.get("series", [])
        is_fav = raw_result.get("is_fav", False)
        response_type = raw_result.get("responseType", "General")
        # Normalize series data
        def normalize_series(series):
            normalized = []
            if not isinstance(series, list):
                return normalized
            for i, s in enumerate(series):
                if not isinstance(s, dict):
                    continue
                label = s.get("label") or f"Series {i+1}"
                x = s.get("x", [])
                y = s.get("y", [])
                if not isinstance(x, list):
                    x = list(x) if hasattr(x, "__iter__") else []
                if not isinstance(y, list):
                    y = list(y) if hasattr(y, "__iter__") else []
                min_len = min(len(x), len(y))
                x = x[:min_len]
                y = y[:min_len]
                if min_len > 0:
                    normalized.append({"label": label, "x": x, "y": y})
            return normalized
        normalized_series = normalize_series(series)
        result = {
            "description": description,
            "title": title,
            "series": normalized_series,
            "is_fav": is_fav,
            "responseType": response_type
        }
        return result
    except Exception as e:
        print(f"Error in analyze endpoint: {e}")
        return {
            "description": f"Sorry, I encountered an error processing your request: {str(e)}",
            "title": "Error",
            "series": [{
                "label": "Error",
                "x": [1, 2, 3],
                "y": [0, 0, 0]
            }],
            "is_fav": False,
            "responseType": "Analysis"
        }


GRAPH_STORE_PATH = os.path.join(os.path.dirname(__file__), "graphs.json")


class GraphBody(BaseModel):
    title: str
    series: List[Dict[str, Any]]            # exactly what the LLM returns
    is_fav: bool = False

from fastapi import Request

from pydantic import ValidationError

def is_valid_graph(graph):
    if not isinstance(graph, dict):
        return False
    if not {"title", "series", "is_fav"}.issubset(graph):
        return False
    if not isinstance(graph["series"], list) or not graph["series"]:
        return False
    for s in graph["series"]:
        if not isinstance(s, dict):
            return False
        if not {"label", "x", "y"}.issubset(s):
            return False
        if not isinstance(s["x"], list) or not isinstance(s["y"], list):
            return False
    return True

# --- /api/add_graph endpoint ---
# Validates and saves a new graph to disk, or returns a fallback if invalid.

@api.post("/api/add_graph")
async def add_graph(request: Request):
    try:
        raw_body = await request.json()
        print(f"Raw /api/add_graph request body: {raw_body}")
        # Validate using is_valid_graph
        if not is_valid_graph(raw_body):
            print("Rejected invalid graph payload.")
            # Check if graphs.json is empty, and if so, add a fallback graph
            data = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8")) if os.path.exists(GRAPH_STORE_PATH) else []
            if not data:
                fallback = {
                    "title": "Sample Graph",
                    "series": [{
                        "label": "Example Series",
                        "x": [1,2,3,4,5],
                        "y": [10,20,15,30,25]
                    }],
                    "is_fav": False
                }
                data.append(fallback)
                json.dump(data, open(GRAPH_STORE_PATH, "w", encoding="utf-8"), indent=2)
            raise HTTPException(status_code=422, detail="Invalid graph format. A sample graph is present.")
        payload = GraphBody(**raw_body)
        print(f"Validated /api/add_graph payload: {payload}")
        data = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8")) if os.path.exists(GRAPH_STORE_PATH) else []
        data.append(payload.model_dump())
        json.dump(data, open(GRAPH_STORE_PATH, "w", encoding="utf-8"), indent=2)
        return {"ok": True, "index": len(data) - 1}
    except ValidationError as ve:
        print(f"Pydantic validation error in /api/add_graph: {ve}")
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        print(f"Unexpected error in /api/add_graph: {e}")
        raise HTTPException(status_code=422, detail=str(e))


class ScrollPropagator(QObject):
    def __init__(self, scroll_area):
        super().__init__()
        self.scroll_area = scroll_area

    def eventFilter(self, obj, event):
        from PySide6.QtGui import QWheelEvent
        if isinstance(event, QWheelEvent):
            sb = self.scroll_area.verticalScrollBar()
            sb.setValue(sb.value() - event.angleDelta().y())
            return True
        return False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Dashboard")
        self.setGeometry(100, 100, 1200, 800)

        # === State ===
        self.chat_history = [{
            "role": "system",
            "content": (
                "You are a Python plotting assistant…\n"
                "Return ONE JSON with fields: description, title, series[]."
            )
        }]
        self.graph_cards = []

        # === UI Setup ===
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        self._build_top_bar(root)
        self._build_loading_bar(root)
        self._build_pages(root)
        self._build_chat_input(root)

        # start on Home
        self._highlight_nav(self.home_btn)
        self.pages.setCurrentWidget(self.home_scroll)

        # enable scroll wheel anywhere
        for area in (self.home_scroll, self.floor_scroll,
                     self.chat_scroll, self.graphs_scroll):
            self._install_scroll_propagation(area)

        # load saved graphs
        self.load_graphs()

    def _build_top_bar(self, parent_layout):
        bar = QHBoxLayout(); bar.setContentsMargins(10,10,10,10); bar.setSpacing(20)
        # logos
        for img, size in [("logo1.png",80),("logo2.png",220),("logo3.png",350)]:
            lbl = QLabel()
            lbl.setPixmap(QPixmap(img).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            bar.addWidget(lbl)
            if img == "logo2.png": bar.addStretch()
        bar.addStretch()
        # nav buttons
        self.home_btn     = QPushButton("Home")
        self.floor_btn    = QPushButton("Floor")
        self.generate_btn = QPushButton("Generate")
        self.graphs_btn   = QPushButton("Graphs")
        for b in (self.home_btn, self.floor_btn, self.generate_btn, self.graphs_btn):
            b.setFixedSize(120,40); b.setFont(QFont("Arial",11))
        self.home_btn.clicked.connect(self.show_home)
        self.floor_btn.clicked.connect(self.show_floor)
        self.generate_btn.clicked.connect(self.show_generate)
        self.graphs_btn.clicked.connect(self.show_graphs)
        for b in (self.home_btn, self.floor_btn, self.generate_btn, self.graphs_btn):
            bar.addWidget(b)
        parent_layout.addLayout(bar)

    def _build_loading_bar(self, parent_layout):
        self.loading_bar = QProgressBar(); self.loading_bar.setRange(0,0)
        self.loading_bar.setFixedHeight(10); self.loading_bar.hide()
        parent_layout.addWidget(self.loading_bar)

    def _build_pages(self, parent_layout):
        self.pages = QStackedWidget(); parent_layout.addWidget(self.pages)
        # Home
        home_container = QWidget(); self.home_page = home_container
        self.home_scroll = QScrollArea(); self.home_scroll.setWidgetResizable(True)
        self.home_layout = QVBoxLayout(home_container); self.home_layout.setContentsMargins(5,5,5,5)
        self.home_scroll.setWidget(home_container); self.pages.addWidget(self.home_scroll)
        # Floor
        self.floor_scroll = QScrollArea(); self.floor_scroll.setWidgetResizable(True)
        self.floor_scroll.setWidget(FloorPage()); self.pages.addWidget(self.floor_scroll)
        # Generate
        gen_container = QWidget()
        self.chat_scroll = QScrollArea(); self.chat_scroll.setWidgetResizable(True)
        self.chat_layout = QVBoxLayout(gen_container); self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(gen_container); self.pages.addWidget(self.chat_scroll)
        # Graphs
        graphs_container = QWidget()
        self.graphs_scroll = QScrollArea(); self.graphs_scroll.setWidgetResizable(True)
        self.graphs_grid = QGridLayout(graphs_container); self.graphs_grid.setContentsMargins(24,18,24,18)
        self.graphs_scroll.setWidget(graphs_container); self.pages.addWidget(self.graphs_scroll)

    def _build_chat_input(self, parent_layout):
        overlay = QWidget(); overlay.setAttribute(Qt.WA_TranslucentBackground)
        parent_layout.addWidget(overlay)
        ol = QHBoxLayout(overlay); ol.setContentsMargins(350,0,350,25)
        bg = QFrame(); bg.setStyleSheet("QFrame{background:rgba(30,30,30,120);border-radius:14px}")
        bl = QHBoxLayout(bg); bl.setContentsMargins(18,10,18,10)
        self.chat_input = QLineEdit(); self.chat_input.setPlaceholderText("Type here…")
        self.chat_input.returnPressed.connect(self.forward_to_generate)
        send_btn = QPushButton("Send"); send_btn.clicked.connect(self.forward_to_generate)
        bl.addWidget(self.chat_input); bl.addWidget(send_btn); ol.addWidget(bg)

    def _highlight_nav(self, active):
        for b in (self.home_btn, self.floor_btn, self.generate_btn, self.graphs_btn):
            b.setStyleSheet("")
        active.setStyleSheet("background:#005f5f;color:white;font-weight:bold;")

    def show_home(self):
        self.pages.setCurrentWidget(self.home_scroll); self._highlight_nav(self.home_btn)

    def show_floor(self):
        self.pages.setCurrentWidget(self.floor_scroll); self._highlight_nav(self.floor_btn)

    def show_generate(self):
        self.pages.setCurrentWidget(self.chat_scroll); self._highlight_nav(self.generate_btn)
        # Reset chat history every time the user enters the Generate page
        self.chat_history = [{
            "role": "system",
            "content": (
                "You are a Python plotting assistant…\n"
                "Return ONE JSON with fields: description, title, series[]."
            )
        }]
        QTimer.singleShot(50, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()))

    def show_graphs(self):
        # clear grid
        while self.graphs_grid.count():
            self.graphs_grid.takeAt(0)
        favs = [c for c in self.graph_cards if c.is_fav]
        rest = [c for c in self.graph_cards if not c.is_fav]
        row = col = 0
        def add(c):
            nonlocal row, col
            self.graphs_grid.addWidget(c, row, col)
            col+=1
            if col==2: col, row = 0, row+1
        for c in (favs+rest): add(c)
        self.pages.setCurrentWidget(self.graphs_scroll); self._highlight_nav(self.graphs_btn)

    def _install_scroll_propagation(self, scroll_area):
        sp = ScrollPropagator(scroll_area)
        scroll_area.viewport().installEventFilter(sp)
        if scroll_area.widget():
            scroll_area.widget().installEventFilter(sp)

    def forward_to_generate(self):
        prompt = self.chat_input.text().strip()
        if not prompt: return
        self.chat_history.append({"role":"user","content":prompt})
        self.loading_bar.show(); self.chat_input.setEnabled(False)
        self.worker = ChatWorker(self.chat_history[:])
        self.worker.result_ready.connect(self.handle_result)
        self.worker.start()

    def handle_result(self, description: str, title: str, series_list: list):
        # 4) hide loading bar, re-enable input
        self.loading_bar.hide()
        self.chat_input.clear()
        self.chat_input.setEnabled(True)

        # 5) append assistant reply
        self.chat_history.append({"role": "assistant", "content": description})

        last_user = self.chat_history[-2]["content"]

        # 6) Build a chat bubble
        if isinstance(series_list, list) and len(series_list) > 1:
            # Multi‐series: truncate each series’ x/y to matching lengths if needed
            fixed = []
            for s in series_list:
                x_raw = s.get("x", [])
                y_raw = s.get("y", [])
                n = min(len(x_raw), len(y_raw))
                x_slice = x_raw[:n]
                y_slice = y_raw[:n]
                fixed.append({**s, "x": x_slice, "y": y_slice})
            entry = MultiSeriesChatEntry(
                user_prompt=last_user,
                ai_response=description,
                series=fixed,
                title=title,
                parent=self.chat_scroll.widget()
            )

        elif isinstance(series_list, list) and len(series_list) == 1:
            s = series_list[0]
            x_raw = s.get("x", [])
            y_raw = s.get("y", [])
            n = min(len(x_raw), len(y_raw))
            x_raw = x_raw[:n]
            y_raw = y_raw[:n]

            # Attempt numeric conversion; if fails, treat as dates or categories
            try:
                x_arr = np.array(x_raw, dtype=float)
                x_labels = None
                is_date = False
            except ValueError:
                try:
                    # Try parsing both ISO format and MM/DD/YYYY format
                    x_dates = []
                    for d in x_raw:
                        try:
                            if "/" in d:  # MM/DD/YYYY format
                                x_dates.append(datetime.strptime(d, "%m/%d/%Y %H:%M"))
                            else:  # ISO format
                                x_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
                        except ValueError:
                            # If parsing fails, just use the string as is
                            x_dates.append(d)
                    
                    import matplotlib.dates as mdates
                    x_arr = mdates.date2num(x_dates)
                    x_labels = x_dates
                    is_date = True
                except Exception as e:
                    print(f"Error parsing dates: {str(e)}")
                    x_labels = x_raw
                    x_arr = np.arange(len(x_labels), dtype=float)
                    is_date = False

            y_arr = np.array(y_raw, dtype=float)

            entry = ChatEntry(
                user_prompt=last_user,
                ai_response=description,
                x_data=x_arr,
                y_data=y_arr,
                title=title,
                x_labels=x_labels,
                is_date=is_date,
                parent=self.chat_scroll.widget()
            )
        else:
            entry = ChatEntry(
                user_prompt=last_user,
                ai_response=description,
                no_random_plot=True,
                parent=self.chat_scroll.widget()
            )

        self.chat_layout.addWidget(entry)
        self.show_generate()

        # 7) Now, if series_list is non-empty, add a GraphCard or MultiSeriesGraphCard
        if isinstance(series_list, list) and len(series_list) > 0:
            if len(series_list) == 1:
                s = series_list[0]
                x_raw = s.get("x", [])
                y_raw = s.get("y", [])
                n = min(len(x_raw), len(y_raw))
                x_raw = x_raw[:n]
                y_raw = y_raw[:n]

                try:
                    x_arr = np.array(x_raw, dtype=float)
                    x_labels = None
                    is_date = False
                except ValueError:
                    try:
                        # Try parsing both ISO format and MM/DD/YYYY format
                        x_dates = []
                        for d in x_raw:
                            try:
                                if "/" in d:  # MM/DD/YYYY format
                                    x_dates.append(datetime.strptime(d, "%m/%d/%Y %H:%M"))
                                else:  # ISO format
                                    x_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
                            except ValueError:
                                # If parsing fails, just use the string as is
                                x_dates.append(d)
                        
                        import matplotlib.dates as mdates
                        x_arr = mdates.date2num(x_dates)
                        x_labels = x_dates
                        is_date = True
                    except Exception as e:
                        print(f"Error parsing dates: {str(e)}")
                        x_labels = x_raw
                        x_arr = np.arange(len(x_labels), dtype=float)
                        is_date = False

                y_arr = np.array(y_raw, dtype=float)

                card = GraphCard(
                    title=title,
                    parent_grid=self.graphs_grid,
                    home_layout=self.home_layout,
                    main_window=self,
                    x_data=x_arr,
                    y_data=y_arr,
                    x_labels=x_labels,
                    is_date=is_date
                )
            else:
                converted = []
                for s in series_list:
                    first_x = s["x"][0] if s["x"] else None
                    if isinstance(first_x, str):
                        try:
                            # Try parsing both ISO format and MM/DD/YYYY format
                            x_dates = []
                            for d in s["x"]:
                                try:
                                    if "/" in d:  # MM/DD/YYYY format
                                        x_dates.append(datetime.strptime(d, "%m/%d/%Y %H:%M"))
                                    else:  # ISO format
                                        x_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
                                except ValueError:
                                    # If parsing fails, just use the string as is
                                    x_dates.append(d)
                            
                            import matplotlib.dates as mdates
                            x_arr = mdates.date2num(x_dates)
                            x_labels = x_dates
                            is_date = True
                        except Exception:
                            x_labels = s["x"]
                            x_arr = np.arange(len(x_labels), dtype=float)
                            is_date = False
                    else:
                        x_labels = None
                        x_arr = np.array(s["x"], dtype=float)
                        is_date = False

                    y_arr = np.array(s["y"], dtype=float)
                    converted.append({
                        "label": s["label"],
                        "x": x_arr,
                        "y": y_arr,
                        "x_labels": x_labels,
                        "is_date": is_date
                    })

                card = MultiSeriesGraphCard(
                    title=title,
                    parent_grid=self.graphs_grid,
                    home_layout=self.home_layout,
                    main_window=self,
                    series=converted
                )

            is_fav = False
            if is_fav:
                card.toggle_fav()

            self.graph_cards.append(card)
            self.graphs_grid.addWidget(card, *self._next_pos())

    def _next_pos(self):
        count = self.graphs_grid.count()
        return divmod(count, 2)

                # ---------- Persistence: save/load graphs.json ----------
    
    def is_valid_graph(graph):
        if not isinstance(graph, dict):
            return False
        if not {"title", "series", "is_fav"}.issubset(graph):
            return False
        if not isinstance(graph["series"], list) or not graph["series"]:
            return False
        for s in graph["series"]:
            if not isinstance(s, dict):
                return False
            if not {"label", "x", "y"}.issubset(s):
                return False
            if not isinstance(s["x"], list) or not isinstance(s["y"], list):
                return False
        return True

    def save_graphs(self):
        data = []
        for card in self.graph_cards:
            if isinstance(card, MultiSeriesGraphCard):
                series_list = []
                for s in card.series:
                    entry = {"label": s["label"]}
                    if s["is_date"] and s.get("x_labels"):
                        entry["x"] = [d.strftime("%Y-%m-%d") for d in s["x_labels"]]
                    elif s.get("x_labels"):
                        entry["x"] = s["x_labels"]
                    else:
                        entry["x"] = s["x"].tolist()
                    entry["y"] = s["y"].tolist()
                    series_list.append(entry)

                graph_obj = {
                    "title": card.title,
                    "series": series_list,
                    "is_fav": card.is_fav
                }
                if is_valid_graph(graph_obj):
                    data.append(graph_obj)
                else:
                    print(f"Warning: Invalid graph not saved: {graph_obj}")

            else:
                if card.is_date and card.x_labels:
                    x_field = [d.strftime("%Y-%m-%d") for d in card.x_labels]
                elif card.x_labels:
                    x_field = card.x_labels
                else:
                    x_field = card.x.tolist()

                graph_obj = {
                    "title": card.title,
                    "series": [{
                        "label": card.title,
                        "x": x_field,
                        "y": card.y.tolist()
                    }],
                    "is_fav": card.is_fav
                }
                if is_valid_graph(graph_obj):
                    data.append(graph_obj)
                else:
                    print(f"Warning: Invalid graph not saved: {graph_obj}")

        try:
            with open(GRAPH_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Error saving graphs.json:", e)

    def load_graphs(self):
        if not os.path.exists(GRAPH_STORE_PATH):
            return
        try:
            saved = json.load(open(GRAPH_STORE_PATH, "r", encoding="utf-8"))
        except Exception:
            return

        for item in saved:
            title = item.get("title", "")
            series_list = item.get("series", [])
            is_fav = item.get("is_fav", False)

            if not isinstance(series_list, list) or len(series_list) == 0:
                continue

            if len(series_list) == 1:
                s = series_list[0]
                first_x = s["x"][0] if s["x"] else None
                if isinstance(first_x, str):
                    try:
                        # Try parsing both ISO format and MM/DD/YYYY format
                        x_dates = []
                        for d in s["x"]:
                            try:
                                if "/" in d:  # MM/DD/YYYY format
                                    x_dates.append(datetime.strptime(d, "%m/%d/%Y %H:%M"))
                                else:  # ISO format
                                    x_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
                            except ValueError:
                                # If parsing fails, just use the string as is
                                x_dates.append(d)
                        
                        import matplotlib.dates as mdates
                        x_arr = mdates.date2num(x_dates)
                        x_labels = x_dates
                        is_date = True
                    except Exception:
                        x_labels = s["x"]
                        x_arr = np.arange(len(x_labels), dtype=float)
                        is_date = False
                else:
                    x_labels = None
                    x_arr = np.array(s["x"], dtype=float)
                    is_date = False

                y_arr = np.array(s["y"], dtype=float)

                card = GraphCard(
                    title=title,
                    parent_grid=self.graphs_grid,
                    home_layout=self.home_layout,
                    main_window=self,
                    x_data=x_arr,
                    y_data=y_arr,
                    x_labels=x_labels,
                    is_date=is_date
                )
            else:
                converted = []
                for s in series_list:
                    first_x = s["x"][0] if s["x"] else None
                    if isinstance(first_x, str):
                        try:
                            # Try parsing both ISO format and MM/DD/YYYY format
                            x_dates = []
                            for d in s["x"]:
                                try:
                                    if "/" in d:  # MM/DD/YYYY format
                                        x_dates.append(datetime.strptime(d, "%m/%d/%Y %H:%M"))
                                    else:  # ISO format
                                        x_dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
                                except ValueError:
                                    # If parsing fails, just use the string as is
                                    x_dates.append(d)
                        
                            import matplotlib.dates as mdates
                            x_arr = mdates.date2num(x_dates)
                            x_labels = x_dates
                            is_date = True
                        except Exception:
                            x_labels = s["x"]
                            x_arr = np.arange(len(x_labels), dtype=float)
                            is_date = False
                    else:
                        x_labels = None
                        x_arr = np.array(s["x"], dtype=float)
                        is_date = False

                    y_arr = np.array(s["y"], dtype=float)
                    converted.append({
                        "label": s["label"],
                        "x": x_arr,
                        "y": y_arr,
                        "x_labels": x_labels,
                        "is_date": is_date
                    })

                card = MultiSeriesGraphCard(
                    title=title,
                    parent_grid=self.graphs_grid,
                    home_layout=self.home_layout,
                    main_window=self,
                    series=converted
                )

            if is_fav:
                card.toggle_fav()

            self.graph_cards.append(card)
            self.graphs_grid.addWidget(card, *self._next_pos())


# -----------------------------------------------------------------------------


if __name__ == "__main__":
    # 1) start FastAPI in background
    t = threading.Thread(target=_start_api, daemon=True)
    t.start()

    # 2) launch Qt app
    app = QApplication(sys.argv)
    apply_stylesheet(app, "dark_teal.xml")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

@api.middleware("http")
async def handle_client_cancellation(request: Request, call_next):
    """
    Middleware to handle client disconnections and cancellations.
    This helps manage the stop button functionality.
    """
    try:
        # Track if the request has been cancelled before processing
        request.state.cancelled = False
        return await call_next(request)
    except Exception as e:
        if isinstance(e, asyncio.CancelledError):
            print("Request was cancelled due to client disconnection")
            return JSONResponse(
                status_code=499,
                content={"detail": "Client disconnected"}
            )
        raise
