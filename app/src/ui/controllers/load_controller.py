import datetime
import logging
import shutil

from PySide6.QtCore import QThread, Qt, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import config
from core.enums import LoadMode
from ui.shared import texts
from ui.utils.utils import prewarm_cover_cache
from ui.shared.dialogs import show_error, show_info, show_warning
from ui.shared.loading_screen import LoadingScreen
import utils.ipk_manager as ipk_manager
from workers.data_load_worker import DataLoadWorker


class LoadController:
    def __init__(self, main_window):
        self.main = main_window
        self._data_thread = None
        self._data_worker = None
        self.loading_screen = None

    def begin(self):
        """Entry point for load flow."""
        load_mode = None
        clear_extracted = False

        mod_path_file = config.DATA_DIR / "mod_path.txt"
        start_dir = None
        if mod_path_file.exists():
            try:
                saved_path = mod_path_file.read_text(encoding="utf-8").strip()
                if saved_path:
                    start_dir = saved_path
            except Exception as e:
                logging.exception(f"Failed to read mod_path.txt: {e}")

        info_box = QMessageBox(self.main)
        info_box.setIcon(QMessageBox.Information)
        info_box.setWindowTitle(texts.TITLE_SELECT_MOD_FOLDER)
        info_box.setText(texts.MOD_FOLDER_PROMPT)
        info_box.setStandardButtons(QMessageBox.Ok)
        info_box.exec()

        folder = QFileDialog.getExistingDirectory(
            self.main,
            texts.SELECT_MOD_FOLDER_DIALOG,
            start_dir or ""
        )
        if not folder:
            logging.error("No MOD folder selected. Closing application.")
            show_error(self.main, texts.TITLE_ERROR, texts.MOD_FOLDER_MISSING)
            raise SystemExit(1)

        config.set_mod_root(folder)

        ipk_check = list(config.INPUT_MOD_ROOT_DIR.glob("*.ipk"))
        if not ipk_check:
            show_warning(self.main, texts.TITLE_NO_IPK_FILES, texts.NO_IPK_FILES_FOUND)
            raise SystemExit(1)
        try:
            mod_path_file.write_text(folder, encoding="utf-8")
        except Exception as e:
            logging.exception(f"Failed to write mod_path.txt: {e}")

        drive_letter = config.BASE_DIR.drive or "Unknown"
        patch_nx_folder = config.EXTRACTED_DIR / "patch_nx"
        has_patch_nx = patch_nx_folder.exists()
        extracted_dirs = [d for d in config.EXTRACTED_DIR.iterdir() if d.is_dir()]
        has_other_extracted = any(d.name != "patch_nx" for d in extracted_dirs)

        while True:
            choice = self.choose_load_mode(drive_letter, has_patch_nx, has_other_extracted)
            if choice is None:
                raise SystemExit(0)

            self.backup_ipk_patcher()

            if choice == LoadMode.JSON:
                if not (config.DATA_DIR / "songs.json").exists():
                    show_warning(self.main, texts.MISSING_FILE_TITLE, texts.MISSING_SONGS_JSON)
                    continue

                if not has_patch_nx:
                    confirm = QMessageBox(self.main)
                    confirm.setIcon(QMessageBox.Question)
                    confirm.setWindowTitle(texts.PATCH_NX_EXTRACT_CONFIRM_TITLE)
                    confirm.setText(texts.PATCH_NX_EXTRACT_CONFIRM_TEXT)
                    confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    confirm.setDefaultButton(QMessageBox.Yes)
                    if confirm.exec() != QMessageBox.Yes:
                        continue

                self.main.use_songs_json = True
                self.main.media_enabled = True
                if hasattr(self.main, "_disable_media_playback_ui"):
                    self.main._disable_media_playback_ui()
                if hasattr(self.main, "volume_controller"):
                    self.main.volume_controller.set_enabled(False)
                load_mode = LoadMode.JSON
                break

            if choice == LoadMode.EXTRACTED:
                if not has_other_extracted:
                    show_warning(self.main, texts.EXTRACTED_DATA_NOT_FOUND_TITLE, texts.EXTRACTED_DATA_NOT_FOUND_TEXT)
                    continue

                self.main.use_songs_json = False
                self.main.media_enabled = True
                if hasattr(self.main, "volume_controller"):
                    self.main.volume_controller.set_enabled(True)
                load_mode = LoadMode.EXTRACTED
                break

            if choice == LoadMode.IPK:
                if extracted_dirs:
                    confirm = QMessageBox(self.main)
                    confirm.setIcon(QMessageBox.Warning)
                    confirm.setWindowTitle(texts.REEXTRACT_CONFIRM_TITLE)
                    confirm.setText(texts.REEXTRACT_CONFIRM_TEXT)
                    confirm.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    confirm.setDefaultButton(QMessageBox.No)
                    if confirm.exec() != QMessageBox.Yes:
                        continue

                    clear_extracted = True

                self.main.use_songs_json = False
                self.main.media_enabled = True
                if hasattr(self.main, "volume_controller"):
                    self.main.volume_controller.set_enabled(True)
                load_mode = LoadMode.IPK
                break

        if not load_mode:
            raise SystemExit(1)

        self.main._load_mode = load_mode
        self.start_data_load_thread(load_mode, clear_extracted)

    def choose_load_mode(self, drive_letter, has_patch_nx, has_other_extracted):
        patch_note = texts.LOAD_MODE_PATCH_NOTE_HAS if has_patch_nx else texts.LOAD_MODE_PATCH_NOTE_MISSING
        extracted_note = (
            texts.LOAD_MODE_EXTRACTED_NOTE_OK
            if has_patch_nx and has_other_extracted
            else texts.LOAD_MODE_EXTRACTED_NOTE_MISSING
        )
        info_lines = [
            texts.LOAD_MODE_INTRO,
            "",
            texts.LOAD_MODE_OPTION_JSON_INFO,
            texts.LOAD_MODE_INFO_JSON.format(patch_note=patch_note),
            texts.LOAD_MODE_INFO_JSON_1,
            texts.LOAD_MODE_INFO_JSON_2,
            "",
            texts.LOAD_MODE_OPTION_EXTRACTED_INFO,
            texts.LOAD_MODE_INFO_EXTRACTED.format(extracted_note=extracted_note),
            texts.LOAD_MODE_INFO_EXTRACTED_1,
            texts.LOAD_MODE_INFO_EXTRACTED_2,
            "",
            texts.LOAD_MODE_OPTION_IPK_INFO,
            texts.LOAD_MODE_INFO_IPK.format(drive=drive_letter),
            "",
            texts.LOAD_MODE_BACKUP_NOTICE,
            texts.LOAD_MODE_HELP,
            ""
        ]

        msg = QMessageBox(self.main)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(texts.TITLE_LOAD_SONGS_DB)
        msg.setText(texts.LOAD_MODE_TOP_WARNING)
        msg.setInformativeText("\n".join(info_lines))

        btn_json = msg.addButton(texts.LOAD_MODE_OPTION_JSON, QMessageBox.AcceptRole)
        btn_extracted = msg.addButton(texts.LOAD_MODE_OPTION_EXTRACTED, QMessageBox.AcceptRole)
        btn_ipk = msg.addButton(texts.LOAD_MODE_OPTION_IPK, QMessageBox.AcceptRole)
        btn_cancel = msg.addButton(texts.LOAD_MODE_CANCEL, QMessageBox.RejectRole)
        msg.setDefaultButton(btn_extracted)

        msg.exec()
        clicked = msg.clickedButton()
        if clicked == btn_json:
            return LoadMode.JSON
        if clicked == btn_extracted:
            return LoadMode.EXTRACTED
        if clicked == btn_ipk:
            return LoadMode.IPK
        if clicked == btn_cancel:
            return None
        return None

    def start_data_load_thread(self, load_mode, clear_extracted):
        """Start background worker for extraction/data loading."""
        self.loading_screen = LoadingScreen(
            self.main,
            title_text=texts.LOADING_TITLE_LABEL,
            footer_text=texts.LOADING_FOOTER_TEXT,
        )
        self.loading_screen.show()
        QApplication.processEvents()

        self._data_thread = QThread(self.main)
        self._data_worker = DataLoadWorker(self.main.data_service, self.main.use_songs_json, load_mode, clear_extracted)
        self._data_worker.moveToThread(self._data_thread)

        self._data_thread.started.connect(self._data_worker.run)
        self._data_worker.progress.connect(self.on_data_load_progress)
        self._data_worker.finished.connect(self.on_data_loaded)
        self._data_worker.error.connect(self.on_data_load_error)

        self._data_worker.finished.connect(self._data_thread.quit)
        self._data_worker.error.connect(self._data_thread.quit)
        self._data_thread.finished.connect(self._data_worker.deleteLater)
        self._data_thread.finished.connect(self._data_thread.deleteLater)

        self._data_thread.start()

    def on_data_loaded(self, payload):
        """Handle background worker success (dispatch to UI thread)."""
        try:
            logging.info("on_data_loaded thread=%s main_thread=%s", QThread.currentThread(), self.main.thread())
        except Exception:
            pass
        QTimer.singleShot(0, self.main, lambda: self._on_data_loaded_ui(payload))

    def on_data_load_progress(self, percent, message):
        """Update loading screen progress on UI thread."""
        QTimer.singleShot(0, self.main, lambda: self._on_data_load_progress_ui(percent, message))

    def _on_data_load_progress_ui(self, percent, message):
        try:
            if self.loading_screen:
                self.loading_screen.set_progress(percent, message)
        except Exception:
            pass

    def _on_data_loaded_ui(self, payload):
        """Handle background worker success on the UI thread."""
        self.prewarm_cover_pixmaps(payload)
        self.load_components(payload)
        cover_errors = payload.get("cover_errors") or []
        if cover_errors:
            logging.error(
                "Errors occurred while extracting playlist covers: %s",
                ", ".join(cover_errors)
            )
            show_error(
                self.main,
                texts.TITLE_ERROR,
                texts.EXTRACT_COVER_ERRORS.format(errors="\n".join(cover_errors)),
            )
        if self.loading_screen:
            try:
                self.loading_screen.set_progress(100, texts.LOAD_PROGRESS_DONE)
            except Exception:
                pass
            self.loading_screen.close()
        self.maybe_show_songs_json_info(payload)

    def prewarm_cover_pixmaps(self, payload):
        """Preload cover images into cache to avoid lag on first selection."""
        try:
            cover_paths = payload.get("cover_png_paths") or []
            if not cover_paths:
                return
            if not self.loading_screen:
                return
            try:
                self.loading_screen.set_progress(95, texts.LOAD_PROGRESS_PRELOAD_COVERS)
            except Exception:
                pass
            label = getattr(self.main.ui, "lblImg", None)
            if label:
                target_w = label.width() or label.geometry().width()
                target_h = label.height() or label.geometry().height()
            else:
                target_w = 0
                target_h = 0
            if not target_w:
                target_w = 441
            if not target_h:
                target_h = 151

            def _progress(idx, total):
                if self.loading_screen:
                    pct = 95
                    if total:
                        pct = 95 + int((idx / total) * 4)
                        if pct > 99:
                            pct = 99
                    self.loading_screen.set_progress(pct, texts.LOAD_PROGRESS_PRELOAD_COVERS)
                QApplication.processEvents()

            prewarm_cover_cache(cover_paths, target_w, target_h, progress_callback=_progress)
        except Exception:
            pass

    def maybe_show_songs_json_info(self, payload):
        if self.main._load_mode != LoadMode.JSON:
            return

        generated_at = payload.get("songs_generated_at")
        formatted = self.format_us_datetime(generated_at) if generated_at else texts.UNKNOWN_TEXT
        logging.info(f"The songs database was loaded from a file generated on: {formatted}")
        show_info(self.main, texts.TITLE_SONGS_DATABASE, texts.SONGS_DB_LOADED_TEXT, formatted)

    def format_us_datetime(self, value):
        if not value:
            return None
        try:
            raw = str(value).strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            parsed = datetime.datetime.fromisoformat(raw)
            return parsed.strftime("%B %d, %Y %I:%M %p")
        except Exception:
            return str(value)

    def on_data_load_error(self, message):
        """Handle background worker errors (dispatch to UI thread)."""
        try:
            logging.info("on_data_load_error thread=%s main_thread=%s", QThread.currentThread(), self.main.thread())
        except Exception:
            pass
        QTimer.singleShot(0, self.main, lambda: self._on_data_load_error_ui(message))

    def _on_data_load_error_ui(self, message):
        """Handle background worker errors on the UI thread."""
        if self.loading_screen:
            self.loading_screen.close()
        show_error(self.main, texts.TITLE_ERROR, texts.LOAD_DATA_ERROR.format(error=message))
        raise SystemExit(1)

    def load_components(self, payload):
        """Load data in screen components (Songs/Playlists/Locales)."""
        logging.info("Loading components...")
        self._log_thread_context("load_components")
        try:
            logging.info("Populating localization data...")
            self._log_widget_thread("tblLocales", self.main.ui.tblLocales)
            self._log_widget_thread("txtSearchLocales", getattr(self.main.ui, "txtSearchLocales", None))
            self.main.locales_controller.populate_locales(payload["locales_items"])
            logging.info("Populating songs...")
            self._log_widget_thread("tblSongs", self.main.ui.tblSongs)
            self._log_widget_thread("txtSearchSongs", getattr(self.main.ui, "txtSearchSongs", None))
            self.main.songs_table_controller.populate_songs(payload["songs_list"])
            logging.info("Populating playlists...")
            self._log_widget_thread("treePlaylists", self.main.ui.treePlaylists)
            self.main.playlists_tree_controller.populate_playlists(payload["playlists"])
            self.main.update_action_buttons()
            logging.info("Components loaded successfully.")
        except Exception as e:
            logging.exception(f"Error loading components: {e}")
            show_error(self.main, texts.TITLE_ERROR, texts.LOAD_COMPONENTS_ERROR.format(error=e))
            raise SystemExit(1)

    def _log_thread_context(self, label):
        """Log current and main thread for debugging."""
        try:
            current = QThread.currentThread()
            main_thread = self.main.thread()
            logging.info(
                "%s thread: current=%s main=%s same=%s",
                label,
                current,
                main_thread,
                current == main_thread,
            )
        except Exception as e:
            logging.debug("Failed to log thread context: %s", e)

    def _log_widget_thread(self, name, widget):
        """Log widget thread for debugging."""
        try:
            if widget is None:
                logging.info("Widget %s is None", name)
                return
            logging.info("Widget %s thread=%s", name, widget.thread())
        except Exception as e:
            logging.debug("Failed to log widget thread for %s: %s", name, e)

    def backup_ipk_patcher(self):
        ipk_original = config.get_patch_nx_path()

        if not ipk_original or not ipk_original.exists():
            logging.error(f"patch_nx.ipk not found in {config.INPUT_MOD_ROOT_DIR}. Closing application.")
            show_error(self.main, texts.TITLE_ERROR, texts.PATCH_NX_MISSING_CLOSE)
            raise SystemExit(1)

        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        nome_backup = f"patch_nx_{timestamp}.ipk"
        destino_backup = config.BKP_DIR / nome_backup

        try:
            logging.info(f"Creating backup: {nome_backup}")
            shutil.copy2(ipk_original, destino_backup)
            logging.info("Backup completed successfully.")
        except Exception as e:
            logging.exception(f"Failed to create backup: {e}")
            show_error(self.main, texts.BACKUP_ERROR_TITLE, texts.BACKUP_ERROR_TEXT.format(error=e))

    def extract_mod_files(self):
        ipk_files = list(config.INPUT_MOD_ROOT_DIR.glob("*.ipk"))

        if not ipk_files:
            show_warning(self.main, texts.TITLE_WARNING, texts.NO_IPK_FILES_FOUND_SIMPLE)
            logging.error("No .ipk files found in the selected MOD folder.")
            raise SystemExit(1)

        logging.info(f"Found {len(ipk_files)} .ipk files to extract.")
        error_files = []
        for ipk in ipk_files:
            output_folder = config.EXTRACTED_DIR / ipk.stem
            output_folder.mkdir(exist_ok=True)
            logging.info(f"Extracting file [{ipk.name}] to folder [{output_folder}]")
            try:
                ipk_manager.extract(ipk, output_dir=output_folder)
            except Exception as e:
                error_files.append(ipk.name)
                logging.exception(f"Error extracting:\n{ipk.name}\nError: {e}")
            else:
                logging.info(f"Successfully extracted [{ipk.name}].")
            QApplication.processEvents()

        if error_files:
            logging.error(
                "Errors occurred while extracting IPKs: %s",
                ", ".join(error_files)
            )
            show_error(self.main, texts.TITLE_ERROR, texts.EXTRACT_IPK_ERRORS.format(errors="\n".join(error_files)))
            raise SystemExit(1)

        logging.info("IPK extraction completed successfully.")

    def messagebox_load_or_extract(self):
        msg = QMessageBox(self.main)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle(texts.TITLE_EXISTING_FILES)
        msg.setText(texts.EXTRACTED_FOUND_TEXT)
        logging.info("Extracted folders detected in 'extracted' directory.")
        msg.setInformativeText(texts.EXTRACTED_FOUND_INFO)

        btn_reextract = msg.addButton(texts.BUTTON_REEXTRACT_ALL, QMessageBox.DestructiveRole)
        btn_load = msg.addButton(texts.BUTTON_LOAD_EXISTING, QMessageBox.AcceptRole)
        msg.setDefaultButton(btn_load)

        msg.exec()

        return msg.clickedButton() == btn_reextract

    def ensure_patch_nx_extracted(self):
        """Extract patch_nx.ipk only if patch_nx folder is missing."""
        try:
            patch_folder = config.EXTRACTED_DIR / "patch_nx"
            if patch_folder.exists():
                return True

            patch_ipk = config.get_patch_nx_path()
            if not patch_ipk or not patch_ipk.exists():
                show_error(self.main, texts.TITLE_ERROR, texts.PATCH_NX_NOT_FOUND)
                return False

            logging.info("Extracting patch_nx.ipk only...")
            patch_folder.mkdir(parents=True, exist_ok=True)
            ipk_manager.extract(patch_ipk, output_dir=patch_folder)
            return True
        except Exception as e:
            logging.exception(f"Failed to extract patch_nx.ipk: {e}")
            show_error(self.main, texts.TITLE_ERROR, texts.PATCH_NX_EXTRACT_FAILED.format(error=e))
            return False
