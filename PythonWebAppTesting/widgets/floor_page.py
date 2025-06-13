# widgets/floor_page.py
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt

class FloorImageWidget(QWidget):
    def __init__(self, image_path: str, title: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.original_pixmap = QPixmap(image_path)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        # Fixed title
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)

        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.image_label)

    def showEvent(self, event):
        super().showEvent(event)
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self):
        if not self.original_pixmap.isNull():
            m = self.layout.contentsMargins()
            max_w = self.width() - (m.left() + m.right())
            if max_w > 0:
                scaled = self.original_pixmap.scaledToWidth(max_w, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)


class FloorPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(20)

        titles = ["ADIC IAQ", "ADIC Temp. F", "ADIC Humidity"]
        for i, title in enumerate(titles, start=1):
            img_widget = FloorImageWidget(f"floor{i}.png", title)
            self.layout.addWidget(img_widget)

        self.layout.addStretch()
