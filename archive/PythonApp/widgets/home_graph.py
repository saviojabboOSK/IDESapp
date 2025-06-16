# widgets/home_graph.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QScrollArea
)
from PySide6.QtGui import QWheelEvent
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from widgets.graph_card import ClickableCanvas


class HomeGraph(QWidget):
    """
    Full-width favourite graph on the Home page.
    Supports categorical x_labels or date x_labels.
    Wheel scroll works on hover, and date axes auto-format to avoid clutter.
    """
    def __init__(self, x_data, y_data, parent_graph_item, x_labels=None, is_date=False, parent=None):
        super().__init__(parent)
        self.x, self.y, self.x_labels, self.is_date = x_data, y_data, x_labels, is_date
        self.parent_graph_item = parent_graph_item
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 5, 10, 5)
        lay.setSpacing(0)

        self.setMinimumHeight(300)

        # Make a figure that will expand to fill the layout
        fig = Figure(figsize=(8, 4.5), tight_layout=True)
        ax = fig.add_subplot(111)

        # Plot data
        if self.is_date and self.x_labels is not None:
            ax.plot(self.x, self.y, marker="o")
            # Auto-locate dates so ticks don't overlap
            locator = mdates.AutoDateLocator()
            formatter = mdates.AutoDateFormatter(locator)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
        else:
            ax.plot(self.x, self.y, marker="o")
            if self.x_labels is not None:
                ax.set_xticks(self.x)
                ax.set_xticklabels(self.x_labels, rotation=45, ha="right")

        # Set y-axis limits with margin
        y_min = min(self.y) if len(self.y) > 0 else 0
        y_max = max(self.y) if len(self.y) > 0 else 1
        y_range = y_max - y_min
        margin = y_range * 0.05 if y_range > 0 else 1
        ax.set_ylim(y_min - margin, y_max + margin)

        ax.set_title(self.parent_graph_item.title)
        ax.grid(True, linestyle="--", alpha=0.3)

        # Wrap in ClickableCanvas so wheel events scroll the Home page
        canvas = ClickableCanvas(fig, onclick=None, parent=self)
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        lay.addWidget(canvas)

        # Star button to remove favorite
        star_row = QHBoxLayout()
        star_row.addStretch()
        star = QPushButton("★")
        star.setFixedSize(30, 30)
        star.setStyleSheet(
            "background:transparent; color:yellow; font-size:20px; border:none;"
        )
        star.clicked.connect(self.confirm_unfav)
        star_row.addWidget(star)
        lay.addLayout(star_row)

    def confirm_unfav(self):
        self.parent_graph_item.toggle_fav()

# END OF widgets/home_graph.py
