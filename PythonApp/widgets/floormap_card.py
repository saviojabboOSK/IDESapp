# widgets/floormap_card.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QScrollArea, QMainWindow, QLabel
)
from PySide6.QtGui import QPixmap, QPainter, QColor, QBrush
from PySide6.QtCore import Qt
import os

class FloormapCard(QWidget):
    """
    Card to display a floormap image with an overlay gradient or values.
    Similar UI and behavior to GraphCard.
    """
    def __init__(self, title, parent_grid, home_layout, main_window, image_path, overlay_data=None, parent=None):
        super().__init__(parent)
        self.parent_grid = parent_grid
        self.home_layout = home_layout
        self.main_window = main_window
        self.title = title
        self.is_fav = False
        self.image_path = image_path
        self.overlay_data = overlay_data  # Could be a 2D array or None
        self._build_ui()

    def _build_ui(self):
        self.setMinimumHeight(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(5)
        self.setObjectName("floormapCard")
        self.setStyleSheet(
            """
            QWidget#floormapCard {
                background: rgba(240,240,255,0.97);
                border: 1px solid black;
                border-radius: 4px;
            }
            """
        )

        # Load original image
        self.base_pixmap = QPixmap(self.image_path)
        if self.base_pixmap.isNull():
            self.base_pixmap = QPixmap(300, 200)
            self.base_pixmap.fill(Qt.gray)

        # Create overlay pixmap
        self.overlay_pixmap = self._create_overlay_pixmap()

        # Combine base and overlay pixmap for display
        self.display_label = QLabel(self)
        self.display_label.setPixmap(self.overlay_pixmap.scaled(300, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.display_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.display_label)

        # Buttons row
        row = QHBoxLayout()
        self.fav_btn = QPushButton("☆ Favorite")
        self.fav_btn.setCheckable(True)
        self.fav_btn.setStyleSheet("QPushButton{background:transparent;}")
        self.fav_btn.clicked.connect(self.toggle_fav)

        del_btn = QPushButton("🗑 Delete")
        del_btn.setStyleSheet("QPushButton{background:transparent;}")
        del_btn.clicked.connect(self.confirm_delete)

        row.addStretch(1)
        row.addWidget(self.fav_btn)
        row.addWidget(del_btn)
        row.addStretch(1)
        layout.addLayout(row)

    def _create_overlay_pixmap(self):
        # Create a pixmap with the base image and overlay gradient or values
        pixmap = QPixmap(self.base_pixmap)
        if self.overlay_data is None:
            # No overlay, return base image
            return pixmap

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Example: overlay a semi-transparent red gradient over the image
        # The overlay_data could be a 2D numpy array normalized between 0 and 1
        # For simplicity, we will overlay a red transparent rectangle with opacity based on overlay_data average

        # Calculate average overlay intensity (if overlay_data is 2D array)
        try:
            import numpy as np
            overlay_array = np.array(self.overlay_data)
            avg_intensity = float(overlay_array.mean())
        except Exception:
            avg_intensity = 0.3  # default opacity

        opacity = max(0.1, min(avg_intensity, 0.7))
        color = QColor(255, 0, 0, int(opacity * 255))
        painter.fillRect(pixmap.rect(), QBrush(color))

        painter.end()
        return pixmap

    def toggle_fav(self):
        from widgets.home_graph import HomeGraph

        if self.is_fav:
            self.is_fav = False
            self.fav_btn.setText("☆ Favorite")
            self.fav_btn.setStyleSheet("QPushButton{background:transparent;}")
            if hasattr(self, "home_widget"):
                self.home_layout.removeWidget(self.home_widget)
                self.home_widget.deleteLater()
        else:
            self.is_fav = True
            self.fav_btn.setText("★ Favorited")
            self.fav_btn.setStyleSheet("QPushButton{background:transparent; color:yellow;}")
            # For home widget, just show the base image without overlay for simplicity
            self.home_widget = HomeGraph(
                None, None, self,
                image_path=self.image_path,
                parent=self.main_window.home_page
            )
            self.home_layout.addWidget(self.home_widget)

        self.main_window.save_graphs()  # persist

    def confirm_delete(self):
        from PySide6.QtWidgets import QMessageBox
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

    def open_full(self):
        win = QMainWindow(self.main_window)
        win.setWindowTitle(self.title)
        win.setGeometry(250, 150, 800, 600)
        central = QWidget()
        win.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(10, 10, 10, 10)

        label = QLabel()
        label.setAlignment(Qt.AlignCenter)
        # Show the overlay pixmap scaled to fit
        label.setPixmap(self.overlay_pixmap.scaled(780, 580, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        lay.addWidget(label)

        win.show()

# END OF widgets/floormap_card.py