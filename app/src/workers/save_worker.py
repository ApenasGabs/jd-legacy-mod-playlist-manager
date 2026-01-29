import logging

from PySide6.QtCore import QObject, Signal, QThread


class SaveWorker(QObject):
    """Background worker to save changes without blocking UI."""

    progress = Signal(int, int, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, save_service):
        super().__init__()
        self.save_service = save_service

    def run(self):
        try:
            try:
                logging.info("Save worker started thread=%s", QThread.currentThread())
            except Exception:
                pass
            self.save_service.run(self.progress.emit)
            try:
                logging.info("Save worker finished thread=%s", QThread.currentThread())
            except Exception:
                pass
            self.finished.emit()
        except Exception as e:
            logging.exception(f"Save worker failed: {e}")
            self.error.emit(str(e))
