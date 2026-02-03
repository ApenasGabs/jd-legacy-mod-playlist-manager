import os
import logging
import re

from PySide6.QtCore import QThread, QTimer, QObject, Signal
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
        self._cancel_dialog = None
        self._cancel_in_progress = False
        self._cleanup_thread = None
        self._cleanup_worker = None
        self._last_save_percent = -1
        self._last_save_message = None

    def on_btnSave_clicked(self):
        """Handle Save button on main window."""
        try:
            if self._save_thread and self._save_thread.isRunning():
                return
            msg = QMessageBox(self.main)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle(texts.SAVE_CONFIRM_TITLE)
            msg.setText(texts.SAVE_CONFIRM_TEXT)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            if msg.exec() != QMessageBox.Yes:
                return
            self._start_save_thread()
        except Exception as e:
            logging.exception(f"Error handling Save: {e}")
            show_error(self.main, texts.TITLE_ERROR, texts.SAVE_ERROR_TEXT.format(message=e))

    def _start_save_thread(self):
        """Start save operations in a background thread."""
        self._last_save_percent = -1
        self._last_save_message = None
        self.save_loading_screen = LoadingScreen(
            self.main,
            title_text=texts.SAVE_TITLE_LABEL,
            footer_text=texts.SAVE_FOOTER_TEXT,
            cancel_callback=self._on_cancel_save_requested,
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
        self._save_worker.cancelled.connect(self._on_save_cancelled)

        self._save_worker.finished.connect(self._save_thread.quit)
        self._save_worker.error.connect(self._save_thread.quit)
        self._save_worker.cancelled.connect(self._save_thread.quit)
        self._save_thread.finished.connect(self._save_worker.deleteLater)
        self._save_thread.finished.connect(self._save_thread.deleteLater)

        if hasattr(self.main.ui, "btnSave"):
            self.main.ui.btnSave.setEnabled(False)

        self._save_thread.start()

    def _on_save_progress(self, index, total, message):
        """Update save loading screen progress text."""
        QTimer.singleShot(0, self.main, lambda: self._on_save_progress_ui(index, total, message))

    def _on_save_progress_ui(self, index, total, message):
        try:
            if self.save_loading_screen:
                percent = self._calculate_save_percent(index, total, message)
                percent = self._smooth_save_percent(percent, message, index, total)
                self.save_loading_screen.set_progress(percent, message)
        except Exception:
            pass

    def _calculate_save_percent(self, index, total, message):
        if total == 100 and isinstance(index, (int, float)):
            try:
                direct = int(index)
                if 0 <= direct <= 100:
                    return direct
            except Exception:
                pass
        if not total:
            return 0
        step_span = 100 / total
        base = (index - 1) * step_span
        match = re.search(r"\((\d+)\/(\d+)\)", str(message))
        if match:
            try:
                sub_idx = int(match.group(1))
                sub_total = int(match.group(2))
                if sub_total > 0:
                    percent = base + (sub_idx / sub_total) * step_span
                else:
                    percent = base
            except Exception:
                percent = base
        else:
            percent = base
        percent = int(percent)
        if percent < 0:
            percent = 0
        if percent > 99:
            percent = 99
        return percent

    def _smooth_save_percent(self, percent, message, index, total):
        if percent < 0:
            percent = 0
        if percent > 99:
            percent = 99
        if percent < self._last_save_percent:
            percent = self._last_save_percent
        self._last_save_percent = percent
        self._last_save_message = message
        return percent

    def _on_save_finished(self):
        """Handle save completion on UI thread."""
        QTimer.singleShot(0, self.main, self._on_save_finished_ui)

    def _on_save_finished_ui(self):
        try:
            if self._cancel_dialog and self._cancel_dialog.isVisible():
                self._cancel_dialog.close()
            if self.save_loading_screen:
                try:
                    self.save_loading_screen.set_progress(100, texts.SAVE_PROGRESS_DONE)
                except Exception:
                    pass
                try:
                    self.save_loading_screen.allow_close()
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
        QTimer.singleShot(0, self.main, lambda: self._on_save_error_ui(message))

    def _on_save_error_ui(self, message):
        try:
            if self._cancel_dialog and self._cancel_dialog.isVisible():
                self._cancel_dialog.close()
            if self.save_loading_screen:
                try:
                    self.save_loading_screen.allow_close()
                except Exception:
                    pass
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

    def _on_save_cancelled(self):
        QTimer.singleShot(0, self.main, self._on_save_cancelled_ui)

    def _on_save_cancelled_ui(self):
        try:
            if self._cancel_dialog and self._cancel_dialog.isVisible():
                self._cancel_dialog.close()
        except Exception:
            pass
        self._start_cancel_cleanup(
            target_dir=config.OUTPUT_PATCH_NX_FOLDER,
            log_label="data/output",
            done_callback=None,
        )

    def _on_cancel_save_requested(self):
        try:
            if self._cancel_dialog and self._cancel_dialog.isVisible():
                return False
            if self._cancel_in_progress:
                return False
            if not self._save_worker:
                return False
            msg = QMessageBox(self.main)
            self._cancel_dialog = msg
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(texts.SAVE_CANCEL_CONFIRM_TITLE)
            msg.setText(texts.SAVE_CANCEL_CONFIRM_TEXT)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            result = msg.exec()
            if result != QMessageBox.Yes:
                return False

            if self.save_loading_screen:
                self.save_loading_screen.set_cancel_enabled(False)
                self.save_loading_screen.set_progress(
                    self.save_loading_screen.progress_bar.value(),
                    texts.SAVE_CANCELING_TEXT,
                )
            self._cancel_in_progress = True
            self._save_worker.request_cancel()
            return False
        except Exception:
            return False

    def _start_cancel_cleanup(self, target_dir, log_label, done_callback):
        try:
            if self.save_loading_screen:
                self.save_loading_screen.set_cancel_enabled(False)
                self.save_loading_screen.append_log_line(
                    self.save_loading_screen.progress_bar.value(),
                    texts.SAVE_CANCELING_TEXT,
                )
            self._cleanup_thread = QThread(self.main)

            class _CleanupWorker(QObject):
                finished = Signal()

                def __init__(self, svc, directory, label):
                    super().__init__()
                    self._svc = svc
                    self._dir = directory
                    self._label = label

                def run(self):
                    try:
                        self._svc.clear_directory_contents_worker(self._dir, self._label)
                    finally:
                        self.finished.emit()

            self._cleanup_worker = _CleanupWorker(self.main.data_service, target_dir, log_label)
            self._cleanup_worker.moveToThread(self._cleanup_thread)
            self._cleanup_thread.started.connect(self._cleanup_worker.run)

            def _finish():
                try:
                    if self.save_loading_screen:
                        self.save_loading_screen.allow_close()
                        self.save_loading_screen.close()
                except Exception:
                    pass
                self._cancel_in_progress = False
                if hasattr(self.main.ui, "btnSave"):
                    self.main.ui.btnSave.setEnabled(True)
                if done_callback:
                    done_callback()

            self._cleanup_worker.finished.connect(_finish)
            self._cleanup_worker.finished.connect(self._cleanup_thread.quit)
            self._cleanup_thread.finished.connect(self._cleanup_worker.deleteLater)
            self._cleanup_thread.finished.connect(self._cleanup_thread.deleteLater)
            self._cleanup_thread.start()
        except Exception:
            try:
                if self.save_loading_screen:
                    self.save_loading_screen.allow_close()
                    self.save_loading_screen.close()
            except Exception:
                pass
            self._cancel_in_progress = False
