# widgets/chat_entry.py

import random
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QLabel, QSizePolicy, QScrollArea, QMainWindow
)
from PySide6.QtGui import QFont, QWheelEvent
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates


class ClickableCanvas(FigureCanvas):
    """
    Forwards mouse clicks to a callback and wheel events to the nearest QScrollArea,
    so that hovering over the plot scrolls the parent widget.
    """
    def __init__(self, figure, onclick_callback=None, parent=None):
        super().__init__(figure)
        self._cb = onclick_callback
        self.setParent(parent)

    def mousePressEvent(self, event):
        if callable(self._cb):
            self._cb()

    def wheelEvent(self, event: QWheelEvent):
        # Find the closest QScrollArea ancestor
        parent = self.parent()
        while parent and not isinstance(parent, QScrollArea):
            parent = parent.parent()
        if isinstance(parent, QScrollArea):
            sb = parent.verticalScrollBar()
            sb.setValue(sb.value() - event.angleDelta().y())
        else:
            super().wheelEvent(event)


class ChatEntry(QWidget):
    """
    A single chat bubble in the Generate page. Displays:
      - user prompt (right-aligned, blue)
      - AI response (left-aligned, dark)
      - an embedded plot if x_data/y_data provided
      - no plot if no_random_plot=True
    """
    def __init__(
        self,
        user_prompt: str,
        ai_response: str,
        x_data=None,
        y_data=None,
        title: str = None,
        x_labels=None,
        is_date: bool = False,
        no_random_plot: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build_ui(user_prompt, ai_response, x_data, y_data, title, x_labels, is_date, no_random_plot)

    def _build_ui(self, prompt, response, x_data, y_data, title, x_labels, is_date, no_random_plot):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Container frame
        container = QFrame()
        container.setObjectName("chatBubbleFrame")
        container.setStyleSheet("""
            QFrame#chatBubbleFrame {
                background-color: rgba(255,255,255,220);
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 10, 15, 10)
        container_layout.setSpacing(5)

        # 1) User prompt
        user_lbl = QLabel(prompt)
        user_lbl.setAlignment(Qt.AlignRight)
        user_lbl.setFont(QFont("Arial", 12, QFont.Bold))
        user_lbl.setStyleSheet("color: #1965A7")
        user_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        user_lbl.setWordWrap(True)
        container_layout.addWidget(user_lbl)

        # 2) AI response
        resp_lbl = QLabel(response)
        resp_lbl.setAlignment(Qt.AlignLeft)
        resp_lbl.setFont(QFont("Arial", 12))
        resp_lbl.setStyleSheet("color: #222")
        resp_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        resp_lbl.setWordWrap(True)
        container_layout.addWidget(resp_lbl)

        # 3) Plot (if provided)
        if (not no_random_plot) and (x_data is not None) and (y_data is not None) and (len(x_data) == len(y_data) > 0):
            fig = Figure(figsize=(4, 5), tight_layout=True)  # doubled height
            ax = fig.add_subplot(111)

            if is_date and x_labels is not None:
                # x_data already converted to matplotlib date numbers; x_labels are Python datetimes
                ax.plot(x_data, y_data, marker="o")
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
                fig.autofmt_xdate(rotation=45)
            else:
                ax.plot(x_data, y_data, marker="o")
                if x_labels is not None:
                    ax.set_xticks(x_data)
                    ax.set_xticklabels(x_labels, rotation=45, ha="right")

            ax.set_title(title or "")
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.grid(True, linestyle="--", alpha=0.3)

            canvas = ClickableCanvas(fig, onclick_callback=self.open_new_window, parent=self)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            container_layout.addWidget(canvas)

        outer_layout.addWidget(container)
        outer_layout.setAlignment(container, Qt.AlignTop)

    def open_new_window(self):
        """
        Open a new window with the same figure at larger size.
        """
        for child in self.findChildren(ClickableCanvas):
            fig = child.figure

            win = QMainWindow(self)
            win.setWindowTitle(self.windowTitle() or "Detail View")
            win.setGeometry(150, 150, 800, 600)
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

# END OF widgets/chat_entry.py
