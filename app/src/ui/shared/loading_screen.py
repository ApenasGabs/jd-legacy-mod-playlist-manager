from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QPlainTextEdit, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from . import texts


class LoadingScreen(QDialog):
    """Loading screen displayed during long operations"""

    def __init__(self, parent=None, title_text=None, footer_text=None, cancel_callback=None, cancel_text=None):
        super().__init__(parent)
        self.setWindowTitle("Processing Files")
        self.setModal(True)
        self.setStyleSheet("background-color: #f0f0f0;")

        self._cancel_callback = cancel_callback
        self._force_close = False

        # Allow close button (Cancel)
        self.setWindowFlags(self.windowFlags() | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(40, 40, 40, 40)

        # Title label
        self.title_label = QLabel(title_text or texts.LOADING_TITLE_LABEL)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.title_label)

        # Status log box
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.log_box.setPlainText(texts.LOADING_STATUS_DEFAULT)
        self.log_box.setStyleSheet(
            "QPlainTextEdit { background-color: #ffffff; border: 1px solid #000000; }"
            "QScrollBar:vertical { background: #e0e0e0; width: 12px; margin: 0px; }"
            "QScrollBar::handle:vertical { background: #8a8a8a; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        )
        self.log_box.setFixedHeight(240)
        layout.addWidget(self.log_box)

        # Status label (percent only)
        self.status_label = QLabel("0%")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.status_label)

        # Progress bar (below percent)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # Cancel button
        self.cancel_button = QPushButton(cancel_text or texts.BUTTON_CANCEL)
        self.cancel_button.setFixedWidth(100)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        cancel_row = QHBoxLayout()
        cancel_row.addStretch(1)
        cancel_row.addWidget(self.cancel_button)
        layout.addLayout(cancel_row)

        self.setLayout(layout)
        self.setFixedSize(600, 520)
        self._last_log_line = None
        self._last_log_key = None

    def _get_log_key(self, message):
        try:
            msg = str(message)
            if " (" in msg:
                return msg.split(" (", 1)[0].strip()
            if ":" in msg:
                return msg.split(":", 1)[0].strip()
            return msg.strip()
        except Exception:
            return None

    def _replace_last_log_line(self, line):
        try:
            doc = self.log_box.document()
            if doc.blockCount() == 0:
                self.log_box.appendPlainText(line)
                return
            cursor = QTextCursor(doc)
            cursor.movePosition(QTextCursor.End)
            cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            cursor.removeSelectedText()
            cursor.insertText(line)
        except Exception:
            self.log_box.appendPlainText(line)

    def set_title_text(self, text):
        if hasattr(self, "title_label"):
            self.title_label.setText(text)

    def set_progress(self, percent, message):
        if hasattr(self, "progress_bar"):
            self.progress_bar.setValue(int(percent))
        if hasattr(self, "status_label"):
            self.status_label.setText(f"{int(percent)}%")
        self.append_log_line(int(percent), message)

    def append_log_line(self, percent, message):
        try:
            if not hasattr(self, "log_box"):
                return
            line = texts.PROGRESS_STATUS_FORMAT.format(percent=int(percent), message=message)
            if line == self._last_log_line:
                return
            key = self._get_log_key(message)
            if key and key == self._last_log_key:
                self._replace_last_log_line(line)
            else:
                self.log_box.appendPlainText(line)
            self._last_log_line = line
            self._last_log_key = key
            self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())
        except Exception:
            pass

    def set_cancel_enabled(self, enabled: bool):
        if hasattr(self, "cancel_button"):
            self.cancel_button.setEnabled(bool(enabled))

    def allow_close(self):
        self._force_close = True

    def _on_cancel_clicked(self):
        if self._cancel_callback:
            should_close = self._cancel_callback()
            if should_close:
                self.allow_close()
                self.close()

    def closeEvent(self, event):
        """Stop animation before closing"""
        if not self._force_close and self._cancel_callback:
            should_close = self._cancel_callback()
            if not should_close:
                event.ignore()
                return
        super().closeEvent(event)
