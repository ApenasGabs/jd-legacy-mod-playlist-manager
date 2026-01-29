from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QMovie

from ... import config
from . import texts


class LoadingScreen(QDialog):
    """Loading screen displayed during long operations"""

    def __init__(self, parent=None, title_text=None, footer_text=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Files")
        self.setModal(True)
        self.setStyleSheet("background-color: #f0f0f0;")

        # Remove window buttons
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        # GIF Label
        self.gif_label = QLabel()
        self.gif_label.setAlignment(Qt.AlignCenter)

        # Load and animate GIF
        gif_path = str(config.GUI_DIR / "loading.gif")
        self.movie = QMovie(gif_path)

        # Resize proportionally (630x637 -> 100x101)
        self.movie.setScaledSize(QSize(100, 101))

        self.gif_label.setMovie(self.movie)
        self.movie.start()

        layout.addWidget(self.gif_label)

        # Title label (below GIF)
        self.title_label = QLabel(title_text or texts.LOADING_TITLE_LABEL)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.title_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label (percent + message)
        self.status_label = QLabel(texts.LOADING_STATUS_DEFAULT)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)

        # Footer text
        self.text_label = QLabel(footer_text or texts.LOADING_FOOTER_TEXT)
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setFont(QFont("Arial", 11))
        layout.addWidget(self.text_label)

        self.setLayout(layout)
        self.setFixedSize(420, 380)

    def set_title_text(self, text):
        if hasattr(self, "title_label"):
            self.title_label.setText(text)

    def set_progress(self, percent, message):
        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(int(percent))
        if hasattr(self, "status_label"):
            self.status_label.setText(texts.PROGRESS_STATUS_FORMAT.format(percent=int(percent), message=message))

    def closeEvent(self, event):
        """Stop animation before closing"""
        if self.movie:
            self.movie.stop()
        super().closeEvent(event)
