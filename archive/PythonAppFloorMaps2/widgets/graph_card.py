# widgets/graph_card.py

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QScrollArea,
    QGridLayout, QMessageBox, QMainWindow
)
from PySide6.QtGui import QWheelEvent
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates


class ClickableCanvas(FigureCanvas):
    """Wheel-events scroll parent QScrollArea; clicks open popup."""
    def __init__(self, fig, onclick=None, parent=None):
        super().__init__(fig)
        self._cb = onclick
        self.setParent(parent)

    def mousePressEvent(self, ev):
        if callable(self._cb):
            self._cb()

    def wheelEvent(self, ev: QWheelEvent):
        p = self.parent()
        while p and not isinstance(p, QScrollArea):
            p = p.parent()
        if isinstance(p, QScrollArea):
            sb = p.verticalScrollBar()
            sb.setValue(sb.value() - ev.angleDelta().y())
        else:
            super().wheelEvent(ev)


class GraphCard(QWidget):
    """
    Card in the Graphs page:
      • categorical or date x-axis supported
      • fixed minimum height so cards never vanish
      • favouriting only turns star/text yellow (no bg change)
      • black border with small rounding
    """
    def __init__(
        self, title, parent_grid, home_layout, main_window,
        x_data, y_data, x_labels=None, is_date=False, parent=None
    ):
        super().__init__(parent)
        self.parent_grid = parent_grid
        self.home_layout = home_layout
        self.main_window = main_window
        self.title = title
        self.is_fav = False
        self.x, self.y, self.x_labels, self.is_date = x_data, y_data, x_labels, is_date
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        self.setMinimumHeight(220)                           # ensure cards don’t vanish
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self.setObjectName("graphCard")
        self.setStyleSheet(
            """
            QWidget#graphCard {
                background: rgba(240,240,255,0.97);
                border: 1px solid black;    /* black border */
                border-radius: 4px;         /* small rounded corner */
            }
            """
        )

        # Thumbnail plot
        fig = Figure(figsize=(3, 4.4), tight_layout=True)
        ax = fig.add_subplot(111)

        if self.is_date and self.x_labels is not None:
            ax.plot(self.x, self.y, marker="o", ms=3)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            fig.autofmt_xdate(rotation=45)
        else:
            ax.plot(self.x, self.y, marker="o", ms=3)
            if self.x_labels is not None:
                ax.set_xticks(self.x)
                ax.set_xticklabels(self.x_labels, rotation=45, fontsize=6, ha="right")
            else:
                ax.set_xticks([])

        ax.set_yticks([])
        ax.set_title(self.title, fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.3)

        canvas = ClickableCanvas(fig, onclick=self.open_full, parent=self)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(canvas)

        # Buttons row
        row = QHBoxLayout()
        self.fav_btn = QPushButton("☆ Favorite")
        self.fav_btn.setCheckable(True)
        self.fav_btn.setStyleSheet("QPushButton{background:transparent;}")  # no bg change
        self.fav_btn.clicked.connect(self.toggle_fav)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setStyleSheet("QPushButton{background:transparent;}")       # no bg change
        del_btn.clicked.connect(self.confirm_delete)

        row.addStretch(1)
        row.addWidget(self.fav_btn)
        row.addWidget(del_btn)
        row.addStretch(1)
        layout.addLayout(row)

    # --------------------------------------------------------------- toggle fav
    def toggle_fav(self):
        from widgets.home_graph import HomeGraph

        if self.is_fav:  # currently fav -> unfav
            self.is_fav = False
            self.fav_btn.setText("☆ Favorite")
            self.fav_btn.setStyleSheet("QPushButton{background:transparent;}")
            if hasattr(self, "home_widget"):
                self.home_layout.removeWidget(self.home_widget)
                self.home_widget.deleteLater()
        else:           # unfav -> fav
            self.is_fav = True
            self.fav_btn.setText("★ Favorited")
            self.fav_btn.setStyleSheet("QPushButton{background:transparent; color:yellow;}")
            self.home_widget = HomeGraph(
                [{"x": self.x, "y": self.y, "label": self.title, "x_labels": self.x_labels, "is_date": self.is_date}],
                self,
                parent=self.main_window.home_page
            )
            self.home_layout.addWidget(self.home_widget)

        self.main_window.save_graphs()  # persist

    # --------------------------------------------------------------- delete
    def confirm_delete(self):
        if QMessageBox.question(
            self, "Confirm Deletion", f"Delete '{self.title}'?", QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes:
            self._delete()

    def _delete(self):
        if self.is_fav and hasattr(self, "home_widget"):
            self.home_layout.removeWidget(self.home_widget)
            self.home_widget.deleteLater()
        for i in range(self.parent_grid.count()):
            if self.parent_grid.itemAt(i).widget() is self:
                self.parent_grid.takeAt(i)
                break
        self.main_window.graph_cards.remove(self)
        self.main_window.save_graphs()
        self.deleteLater()

    # --------------------------------------------------------------- popup full
    def open_full(self):
        win = QMainWindow(self.main_window)
        win.setWindowTitle(self.title)
        win.setGeometry(250, 150, 800, 600)
        central = QWidget()
        win.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(10, 10, 10, 10)

        fig = Figure(figsize=(8, 6), tight_layout=True)
        ax = fig.add_subplot(111)

        if self.is_date and self.x_labels is not None:
            ax.plot(self.x, self.y, marker="o", color="blue")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            fig.autofmt_xdate(rotation=45)
        else:
            ax.plot(self.x, self.y, marker="o", color="blue")
            if self.x_labels is not None:
                ax.set_xticks(self.x)
                ax.set_xticklabels(self.x_labels, rotation=45, ha="right")

        ax.set_title(self.title)
        ax.grid(True, linestyle="--", alpha=0.3)

        lay.addWidget(FigureCanvas(fig))
        win.show()

# END OF widgets/graph_card.py
