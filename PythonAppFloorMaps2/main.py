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

from qt_material import apply_stylesheet

from workers import ChatWorker
from widgets.chat_entry import ChatEntry
from widgets.graph_card import GraphCard
from widgets.home_graph import HomeGraph
from widgets.multi_series_chat_entry import MultiSeriesChatEntry
from widgets.multi_series_graph_card import MultiSeriesGraphCard
from widgets.floor_page import FloorPage    # <-- new

GRAPH_STORE_PATH = os.path.join(os.path.dirname(__file__), "graphs.json")

# -----------------------------------------------------------------------------


class ScrollPropagator(QObject):
    """
    Event filter that forwards wheel events to a QScrollArea so that scrolling works
    when hovering over any child widget.
    """
    def __init__(self, scroll_area):
        super().__init__()
        self.scroll_area = scroll_area

    def eventFilter(self, obj, event):
        from PySide6.QtGui import QWheelEvent
        if isinstance(event, QWheelEvent):
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().value() - event.angleDelta().y()
            )
            return True
        return False


# -----------------------------------------------------------------------------


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sensor Dashboard")
        self.setGeometry(100, 100, 1200, 800)

        # === Data/state ===
        self.chat_history = [
            {
                "role": "system",
                "content": (
                    "You are a Python plotting assistant. I will ask for data. Use what you know and hypothetical data for every prompt. For every user prompt, return ONE JSON object with fields:\n"
                    "  1. \"description\": a plain-English explanation of the plot and axes.\n"
                    "  2. \"title\": a concise title.\n"
                    "  3. \"series\": a JSON array of objects, each {\"label\":string, \"x\":[...], \"y\":[...] }.\n"
                    "     Use full arrays—no ellipses. If only one line is needed, return exactly one object. If no plot, return \"series\": []."
                )
            }
        ]
        self.graph_cards = []  # will store GraphCard / MultiSeriesGraphCard

        # === Build UI ===
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_top_bar(root)
        self._build_loading_bar(root)
        self._build_pages(root)
        self._build_chat_input(root)

        # Start on Home
        self._highlight_nav(self.home_btn)
        self.pages.setCurrentWidget(self.home_scroll)

        # Install scroll-propagation
        for area in (self.home_scroll, self.floor_scroll, self.chat_scroll, self.graphs_scroll):
            self._install_scroll_propagation(area)

        # Load any saved graphs
        self.load_graphs()

    # ---------- Top bar ----------
    def _build_top_bar(self, parent_layout):
        bar = QHBoxLayout()
        bar.setContentsMargins(10, 10, 10, 10)
        bar.setSpacing(20)

        logo1 = QLabel()
        logo1.setPixmap(QPixmap("logo1.png").scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo2 = QLabel()
        logo2.setPixmap(QPixmap("logo2.png").scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo3 = QLabel()
        logo3.setPixmap(QPixmap("logo3.png").scaled(350, 350, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        bar.addWidget(logo1)
        bar.addWidget(logo2)
        bar.addStretch()
        bar.addWidget(logo3)
        bar.addStretch()

        self.home_btn     = QPushButton("Home")
        self.floor_btn    = QPushButton("Floor")      # new
        self.generate_btn = QPushButton("Generate")
        self.graphs_btn   = QPushButton("Graphs")
        for b in (self.home_btn, self.floor_btn, self.generate_btn, self.graphs_btn):
            b.setFixedSize(120, 40)
            b.setFont(QFont("Arial", 11))

        self.home_btn.clicked.connect(self.show_home)
        self.floor_btn.clicked.connect(self.show_floor)    # new
        self.generate_btn.clicked.connect(self.show_generate)
        self.graphs_btn.clicked.connect(self.show_graphs)

        bar.addWidget(self.home_btn)
        bar.addWidget(self.floor_btn)                      # new, between Home & Generate
        bar.addWidget(self.generate_btn)
        bar.addWidget(self.graphs_btn)

        parent_layout.addLayout(bar)

    # ---------- Loading bar ----------
    def _build_loading_bar(self, parent_layout):
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)  # indeterminate
        self.loading_bar.setFixedHeight(10)
        self.loading_bar.hide()
        parent_layout.addWidget(self.loading_bar)

    # ---------- Pages: Home / Floor / Generate / Graphs ----------
    def _build_pages(self, parent_layout):
        self.pages = QStackedWidget()
        parent_layout.addWidget(self.pages)

        # Home
        home_container = QWidget()
        self.home_page = home_container  # so HomeGraph has a valid parent
        self.home_scroll = QScrollArea()
        self.home_scroll.setWidgetResizable(True)
        self.home_layout = QVBoxLayout(home_container)
        self.home_layout.setContentsMargins(5, 5, 5, 5)
        self.home_scroll.setWidget(home_container)
        self.pages.addWidget(self.home_scroll)

        # Floor (new)
        self.floor_scroll = QScrollArea()
        self.floor_scroll.setWidgetResizable(True)
        self.floor_scroll.setWidget(FloorPage())      # <--- new
        self.pages.addWidget(self.floor_scroll)

        # Generate
        gen_container = QWidget()
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_layout = QVBoxLayout(gen_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll.setWidget(gen_container)
        self.pages.addWidget(self.chat_scroll)

        # Graphs
        graphs_container = QWidget()
        self.graphs_scroll = QScrollArea()
        self.graphs_scroll.setWidgetResizable(True)
        self.graphs_grid = QGridLayout(graphs_container)
        self.graphs_grid.setContentsMargins(24, 18, 24, 18)
        self.graphs_scroll.setWidget(graphs_container)
        self.pages.addWidget(self.graphs_scroll)

    # ---------- Chat input overlay ----------
    def _build_chat_input(self, parent_layout):
        overlay = QWidget()
        overlay.setAttribute(Qt.WA_TranslucentBackground)
        parent_layout.addWidget(overlay)

        ol = QHBoxLayout(overlay)
        ol.setContentsMargins(350, 0, 350, 25)

        bg = QFrame()
        bg.setStyleSheet("QFrame { background: rgba(30,30,30,120); border-radius:14px; }")
        bl = QHBoxLayout(bg)
        bl.setContentsMargins(18, 10, 18, 10)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here…")
        self.chat_input.returnPressed.connect(self.forward_to_generate)

        send_btn = QPushButton("Send")
        send_btn.clicked.connect(self.forward_to_generate)

        bl.addWidget(self.chat_input)
        bl.addWidget(send_btn)
        ol.addWidget(bg)

    # ---------- Nav highlighting ----------
    def _highlight_nav(self, active):
        for b in (self.home_btn, self.floor_btn, self.generate_btn, self.graphs_btn):
            b.setStyleSheet("")
        active.setStyleSheet("background: #005f5f; color: white; font-weight: bold;")

    def show_home(self):
        self.pages.setCurrentWidget(self.home_scroll)
        self._highlight_nav(self.home_btn)

    def show_floor(self):
        self.pages.setCurrentWidget(self.floor_scroll)
        self._highlight_nav(self.floor_btn)

    def show_generate(self):
        self.pages.setCurrentWidget(self.chat_scroll)
        self._highlight_nav(self.generate_btn)
        QTimer.singleShot(
            50,
            lambda: self.chat_scroll.verticalScrollBar().setValue(
                self.chat_scroll.verticalScrollBar().maximum()
            ),
        )

    def show_graphs(self):
        # Clear all existing items (does not delete widgets themselves)
        while self.graphs_grid.count():
            self.graphs_grid.takeAt(0)

        favs = [c for c in self.graph_cards if c.is_fav]
        rest = [c for c in self.graph_cards if not c.is_fav]
        row = col = 0

        def add(card):
            nonlocal row, col
            self.graphs_grid.addWidget(card, row, col)
            col += 1
            if col == 2:
                col, row = 0, row + 1

        for card in (favs + rest):
            add(card)

        self.pages.setCurrentWidget(self.graphs_scroll)
        self._highlight_nav(self.graphs_btn)

    # ---------- Scroll-propagation helper ----------
    def _install_scroll_propagation(self, scroll_area):
        sp = ScrollPropagator(scroll_area)
        scroll_area.viewport().installEventFilter(sp)
        if scroll_area.widget():
            scroll_area.widget().installEventFilter(sp)

    # ---------- Chat flow: prompt → ChatGPT → bubble/card ----------
    def forward_to_generate(self):
        prompt = self.chat_input.text().strip()
        if not prompt:
            return

        # 1) append user message
        self.chat_history.append({"role": "user", "content": prompt})

        # 2) show loading bar, disable input
        self.loading_bar.show()
        self.chat_input.setEnabled(False)

        # 3) launch ChatWorker
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
                    x_dates = [datetime.fromisoformat(d) for d in x_raw]
                    import matplotlib.dates as mdates
                    x_arr = mdates.date2num(x_dates)
                    x_labels = x_dates
                    is_date = True
                except Exception:
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
                        x_dates = [datetime.fromisoformat(d) for d in x_raw]
                        import matplotlib.dates as mdates
                        x_arr = mdates.date2num(x_dates)
                        x_labels = x_dates
                        is_date = True
                    except Exception:
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
                            x_dates = [datetime.fromisoformat(d) for d in x_raw]
                            import matplotlib.dates as mdates
                            x_arr = mdates.date2num(x_dates)
                            x_labels = x_dates
                            is_date = True
                        except Exception:
                            x_labels = x_raw
                            x_arr = np.arange(len(x_labels), dtype=float)
                            is_date = False

                    y_arr = np.array(y_raw, dtype=float)
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

            self.graph_cards.append(card)
            self.graphs_grid.addWidget(card, *self._next_pos())
            self.save_graphs()

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
                        x_dates = [datetime.fromisoformat(d) for d in s["x"]]
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
                            x_dates = [datetime.fromisoformat(d) for d in s["x"]]
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
    app = QApplication(sys.argv)
    apply_stylesheet(app, "dark_teal.xml")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

