import logging

from PySide6.QtCore import QObject, Signal, QThread
from ..services.save_service import SaveCancelled


class SaveWorker(QObject):
    """Background worker to save changes without blocking UI."""

    progress = Signal(int, int, str)
    finished = Signal()
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, save_service):
        super().__init__()
        self.save_service = save_service
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def _check_cancel(self):
        return self._cancel_requested

    def run(self):
        try:
            try:
                logging.info("Save worker started thread=%s", QThread.currentThread())
            except Exception:
                pass
            self.save_service.run(self.progress.emit, cancel_check=self._check_cancel)
            try:
                logging.info("Save worker finished thread=%s", QThread.currentThread())
            except Exception:
                pass
            self.finished.emit()
        except SaveCancelled:
            logging.info("Save worker cancelled by user.")
            self.cancelled.emit()
        except Exception as e:
            logging.exception(f"Save worker failed: {e}")
            self.error.emit(str(e))
