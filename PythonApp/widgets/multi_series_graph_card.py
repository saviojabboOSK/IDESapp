# widgets/multi_series_graph_card.py

import numpy as np
from datetime import datetime
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
        self._onclick = onclick
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


class MultiSeriesGraphCard(QWidget):
    """
    Card on the Graphs page that supports multiple series, 
    each of which might be numeric, categorical, or date-based.
    """
    def __init__(
        self, title, parent_grid, home_layout, main_window,
        series: list, parent=None
    ):
        super().__init__(parent)
        self.parent_grid = parent_grid
        self.home_layout = home_layout
        self.main_window = main_window
        self.title = title
        self.series = series  # list of dicts: {label, x, y, x_labels?, is_date?}
        self.is_fav = False
        self._build()

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.setMinimumHeight(220)  # ensure cards don’t vanish
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self.setObjectName("graphCard")
        self.setStyleSheet(
            """
            QWidget#graphCard {
                background: rgba(240,240,255,0.97);
                border: 1px solid black;    /* black border */
                border-radius: 4px;         /* small rounding */
            }
            """
        )

        # Thumbnail plot
        fig = Figure(tight_layout=True)
        ax = fig.add_subplot(111)

        any_date = any(s.get("is_date", False) for s in self.series)

        for s in self.series:
            x = s["x"]
            y = s["y"]
            x_labels = s.get("x_labels", None)
            is_date = s.get("is_date", False)

            if is_date and x_labels is not None:
                ax.plot(x, y, label=s["label"], marker="o", ms=3)
            else:
                ax.plot(x, y, label=s["label"], marker="o", ms=3)

        if any_date:
            # Use auto date locator/formatter so ticks don’t overlap
            locator = mdates.AutoDateLocator()
            formatter = mdates.AutoDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
        else:
            first = self.series[0]
            if first.get("x_labels") is not None:
                ax.set_xticks(first["x"])
                ax.set_xticklabels(first["x_labels"], rotation=45, fontsize=6, ha="right")
            else:
                ax.set_xticks([])

        # ax.set_yticks([])  # Show Y axis ticks on every page
        ax.set_title(self.title, fontsize=9)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(fontsize=6)

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
        else:  # unfav -> fav
            self.is_fav = True
            self.fav_btn.setText("★ Favorited")
            self.fav_btn.setStyleSheet("QPushButton{background:transparent; color:yellow;}")
            # Show an overlay of the first series on Home; use AutoDateLocator for dates
            self.home_widget = HomeGraph(
                self.series[0]["x"],
                self.series[0]["y"],
                self,
                x_labels=self.series[0].get("x_labels"),
                is_date=self.series[0].get("is_date", False),
                parent=self.main_window.home_page
            )
            self.home_layout.addWidget(self.home_widget)

        self.main_window.save_graphs()

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

        fig = Figure(tight_layout=True)
        ax = fig.add_subplot(111)

        any_date = any(s.get("is_date", False) for s in self.series)

        for s in self.series:
            x = s["x"]
            y = s["y"]
            x_labels = s.get("x_labels", None)
            is_date = s.get("is_date", False)

            if is_date and x_labels is not None:
                ax.plot(x, y, label=s["label"], marker="o")
            else:
                ax.plot(x, y, label=s["label"], marker="o")

        if any_date:
            locator = mdates.AutoDateLocator()
            formatter = mdates.AutoDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
        else:
            first = self.series[0]
            if first.get("x_labels") is not None:
                ax.set_xticks(first["x"])
                ax.set_xticklabels(first["x_labels"], rotation=45, ha="right")

        ax.set_title(self.title)
        ax.grid(True, linestyle="--", alpha=0.3)
        ax.legend(fontsize=8)

        lay.addWidget(FigureCanvas(fig))
        win.show()

# END OF widgets/multi_series_graph_card.py
