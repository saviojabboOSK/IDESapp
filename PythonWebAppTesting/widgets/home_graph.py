# widgets/home_graph.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from widgets.graph_card import ClickableCanvas

class HomeGraph(QWidget):
    """
    Full-width favourite graph on the Home page.
    Supports multi-series (comparison) graphs and minimum height.
    """
    def __init__(self, series_list, parent_graph_item, parent=None):
        super().__init__(parent)
        self.series = series_list
        self.parent_graph_item = parent_graph_item
        self.setMinimumHeight(450)   # ← change this number for your desired min height
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 10, 20, 10)
        lay.setSpacing(0)

        fig = Figure(tight_layout=True)
        ax = fig.add_subplot(111)

        # Plot all lines/series
        for s in self.series:
            x = s.get("x", [])
            y = s.get("y", [])
            label = s.get("label", "")
            x_labels = s.get("x_labels", None)
            is_date = s.get("is_date", False)

            # If this line is a date series, autoformat the x axis
            if is_date and x_labels is not None:
                ax.plot(x, y, marker="o", label=label)
                locator = mdates.AutoDateLocator()
                formatter = mdates.AutoDateFormatter(locator)
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(formatter)
            else:
                ax.plot(x, y, marker="o", label=label)
                if x_labels is not None:
                    ax.set_xticks(x)
                    ax.set_xticklabels(x_labels, rotation=45, ha="right")

        ax.set_title(self.parent_graph_item.title)
        ax.grid(True, linestyle="--", alpha=0.3)

        # Show legend only if multiple lines
        if len(self.series) > 1:
            ax.legend()

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

#END OF home_graph.py