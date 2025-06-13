# widgets/multi_series_chat_entry.py

import numpy as np
from datetime import datetime
import matplotlib.dates as mdates
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QSizePolicy, QScrollArea, QMainWindow
)
from PySide6.QtGui import QFont, QWheelEvent
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from widgets.graph_card import ClickableCanvas


class MultiSeriesChatEntry(QWidget):
    """
    A chat bubble for multi-series plots in the Generate page.
    Each series can be numeric, categorical, or date-based.
    Uses AutoDateLocator/Formatter and an expanding canvas so overlays never get clipped.
    """
    def __init__(self, user_prompt: str, ai_response: str, series: list, title: str, parent=None):
        super().__init__(parent)
        self.series = series  # list of dicts: {label, x, y, x_labels?, is_date?}
        self.title = title
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui(user_prompt, ai_response)

    def _build_ui(self, prompt, response):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Container frame
        container = QFrame()
        container.setObjectName("chatBubbleFrame")
        container.setStyleSheet("""
            QFrame#chatBubbleFrame {
                background-color: rgba(255,255,255,220);
                border-radius: 12px;
            }
        """)
        cl = QVBoxLayout(container)
        cl.setContentsMargins(15, 10, 15, 10)
        cl.setSpacing(5)

        # 1) User prompt
        user_lbl = QLabel(prompt)
        user_lbl.setAlignment(Qt.AlignRight)
        user_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        user_lbl.setStyleSheet("color: #1965A7")
        user_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        user_lbl.setWordWrap(True)
        cl.addWidget(user_lbl)

        # 2) AI response
        resp_lbl = QLabel(response)
        resp_lbl.setAlignment(Qt.AlignLeft)
        resp_lbl.setFont(QFont("Arial", 12))
        resp_lbl.setStyleSheet("color: #222")
        resp_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        resp_lbl.setWordWrap(True)
        cl.addWidget(resp_lbl)

        # 3) Build figure with increased width so overlays fit
        fig = Figure(figsize=(6, 4), tight_layout=True)
        ax = fig.add_subplot(111)

        any_date = any(s.get("is_date", False) for s in self.series)

        for s in self.series:
            x = s["x"]
            y = s["y"]
            x_labels = s.get("x_labels", None)
            is_date = s.get("is_date", False)

            if is_date and x_labels is not None:
                ax.plot(x, y, label=s["label"], marker="o", ms=4)
            else:
                ax.plot(x, y, label=s["label"], marker="o", ms=4)

        if any_date:
            # Auto-locate dates so ticks don’t overlap
            locator = mdates.AutoDateLocator()
            formatter = mdates.AutoDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
        else:
            first = self.series[0]
            if first.get("x_labels") is not None:
                ax.set_xticks(first["x"])
                ax.set_xticklabels(first["x_labels"], rotation=45, ha="right")
            else:
                ax.set_xticks([])

        ax.set_title(self.title)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(fontsize=8, loc="best")

        # Wrap in ClickableCanvas so wheel events scroll the chat area
        canvas = ClickableCanvas(fig, onclick=self.open_full, parent=container)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        cl.addWidget(canvas)

        outer.addWidget(container)
        outer.setAlignment(container, Qt.AlignTop)

    def open_full(self):
        """
        Open a new window with the same figure at larger size.
        """
        for child in self.findChildren(ClickableCanvas):
            fig = child.figure

            win = QMainWindow(self)
            win.setWindowTitle(self.title)
            win.setGeometry(150, 150, 900, 600)
            central = QWidget()
            win.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            new_canvas = ClickableCanvas(fig, onclick_callback=None, parent=central)
            new_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(new_canvas)

            win.show()
            break

# END OF widgets/multi_series_chat_entry.py
