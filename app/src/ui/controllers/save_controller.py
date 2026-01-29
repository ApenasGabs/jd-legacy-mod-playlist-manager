import os
import logging

from PySide6.QtCore import QThread, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from ... import config
from ...services.save_service import SaveService
from ..shared import texts
from ..shared.dialogs import show_error
from ..shared.loading_screen import LoadingScreen
from ...workers.save_worker import SaveWorker


class SaveController:
    def __init__(self, main_window):
        self.main = main_window
        self._save_thread = None
        self._save_worker = None
        self.save_loading_screen = None

    def on_btnSave_clicked(self):
        """Handle Save button on main window."""
        try:
            if self._save_thread and self._save_thread.isRunning():
                return
            self._start_save_thread()
        except Exception as e:
            logging.exception(f"Error handling Save: {e}")
            show_error(self.main, texts.TITLE_ERROR, texts.SAVE_ERROR_TEXT.format(message=e))

    def _start_save_thread(self):
        """Start save operations in a background thread."""
        self.save_loading_screen = LoadingScreen(
            self.main,
            title_text=texts.SAVE_TITLE_LABEL,
            footer_text=texts.SAVE_FOOTER_TEXT,
        )
        try:
            self.save_loading_screen.setWindowTitle(texts.SAVE_LOADING_TITLE)
            self.save_loading_screen.set_progress(0, texts.SAVE_STEP_DELETE_COVERS)
        except Exception:
            pass
        self.save_loading_screen.show()
        QApplication.processEvents()

        try:
            logging.info("Save thread setup main_thread=%s", QThread.currentThread())
        except Exception:
            pass

        self._save_thread = QThread(self.main)
        save_service = SaveService(
            self.main.playlists_tree_controller,
            data_service=getattr(self.main, "data_service", None),
            use_songs_json=getattr(self.main, "use_songs_json", False),
        )
        self._save_worker = SaveWorker(save_service)
        self._save_worker.moveToThread(self._save_thread)

        self._save_thread.started.connect(self._save_worker.run)
        self._save_worker.progress.connect(self._on_save_progress)
        self._save_worker.finished.connect(self._on_save_finished)
        self._save_worker.error.connect(self._on_save_error)

        self._save_worker.finished.connect(self._save_thread.quit)
        self._save_worker.error.connect(self._save_thread.quit)
        self._save_thread.finished.connect(self._save_worker.deleteLater)
        self._save_thread.finished.connect(self._save_thread.deleteLater)

        if hasattr(self.main.ui, "btnSave"):
            self.main.ui.btnSave.setEnabled(False)

        self._save_thread.start()

    def _on_save_progress(self, index, total, message):
        """Update save loading screen progress text."""
        try:
            logging.info("Save progress thread=%s", QThread.currentThread())
        except Exception:
            pass
        QTimer.singleShot(0, self.main, lambda: self._on_save_progress_ui(index, total, message))

    def _on_save_progress_ui(self, index, total, message):
        try:
            if self.save_loading_screen:
                percent = 0
                if total:
                    percent = int(((index - 1) / total) * 100)
                    if percent < 0:
                        percent = 0
                    if percent > 99:
                        percent = 99
                self.save_loading_screen.set_progress(percent, message)
        except Exception:
            pass

    def _on_save_finished(self):
        """Handle save completion on UI thread."""
        try:
            logging.info("Save finished signal thread=%s", QThread.currentThread())
        except Exception:
            pass
        QTimer.singleShot(0, self.main, self._on_save_finished_ui)

    def _on_save_finished_ui(self):
        try:
            if self.save_loading_screen:
                try:
                    self.save_loading_screen.set_progress(100, texts.SAVE_PROGRESS_DONE)
                except Exception:
                    pass
                self.save_loading_screen.close()
            if hasattr(self.main.ui, "btnSave"):
                self.main.ui.btnSave.setEnabled(True)

            msg = QMessageBox(self.main)
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle(texts.TITLE_SAVE_COMPLETED)
            msg.setText(texts.SAVE_COMPLETED_TEXT)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            if msg.exec() == QMessageBox.Yes:
                output_dir = config.OUTPUT_PATCH_NX_FOLDER.resolve()
                if output_dir.exists():
                    if os.name == "nt":
                        os.startfile(str(output_dir))
                    elif os.name == "posix":
                        import subprocess
                        subprocess.Popen(["xdg-open", str(output_dir)])
        except Exception as e:
            logging.exception(f"Error finalizing save: {e}")

    def _on_save_error(self, message):
        """Handle save worker errors on UI thread."""
        try:
            logging.info("Save error signal thread=%s", QThread.currentThread())
        except Exception:
            pass
        QTimer.singleShot(0, self.main, lambda: self._on_save_error_ui(message))

    def _on_save_error_ui(self, message):
        try:
            if self.save_loading_screen:
                self.save_loading_screen.close()
            if hasattr(self.main.ui, "btnSave"):
                self.main.ui.btnSave.setEnabled(True)
            msg = QMessageBox(self.main)
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(texts.SAVE_ERROR_DIALOG_TITLE)
            msg.setText(texts.SAVE_ERROR_DIALOG_TEXT)
            msg.setDetailedText(str(message))
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
        except Exception as e:
            logging.exception(f"Error handling save error: {e}")
