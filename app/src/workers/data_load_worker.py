import json
import logging

from PySide6.QtCore import QObject, Signal

import config
from core.enums import LoadMode
from ui.shared import texts
import utils.localisation as localisation
from services.data_service import DataService


class DataLoadWorker(QObject):
    """Background worker to load data/extract files without blocking UI."""

    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, data_service: DataService, use_songs_json: bool, load_mode: LoadMode, clear_extracted: bool):
        super().__init__()
        self.data_service = data_service
        self.use_songs_json = use_songs_json
        self.load_mode = load_mode
        self.clear_extracted = clear_extracted

    def run(self):
        try:
            def _emit(percent, message):
                self.progress.emit(int(percent), message)

            _emit(0, texts.LOAD_PROGRESS_START)

            generated_at = None
            if self.use_songs_json:
                try:
                    input_path = config.DATA_DIR / "songs.json"
                    if input_path.exists():
                        payload_meta = json.loads(input_path.read_text(encoding="utf-8"))
                        generated_at = payload_meta.get("generatedAt")
                except Exception as e:
                    logging.exception(f"Failed to read songs.json metadata: {e}")

            if self.clear_extracted:
                _emit(5, texts.LOAD_PROGRESS_CLEAR_EXTRACTED)
                self.data_service.clear_directory_contents_worker(
                    config.EXTRACTED_DIR,
                    "data/extracted"
                )

            if self.load_mode == LoadMode.IPK:
                _emit(20, texts.LOAD_PROGRESS_EXTRACT_ALL)
                self.data_service.extract_mod_files_worker()
            else:
                _emit(20, texts.LOAD_PROGRESS_EXTRACT_PATCH)
                self.data_service.ensure_patch_nx_extracted_worker()

            _emit(35, texts.LOAD_PROGRESS_CLEAR_TEMP)
            self.data_service.clear_directory_contents_worker(config.TEMP_DIR, "data/temp")
            config.setup_directories(config.ALL_TEMP_DIRS)

            _emit(45, texts.LOAD_PROGRESS_LOCALISATION)
            localisation.decompress(
                config.INPUT_LOCALISATION_FILE,
                config.TEMP_LOCALISATION_JSON,
                legacy=config.LOCALISATION_LEGACY_ESCAPE,
            )

            cover_errors = []
            _emit(60, texts.LOAD_PROGRESS_COVERS)
            cover_errors = self.data_service.extract_playlist_covers_worker()
            cover_png_paths = [str(p) for p in config.TEMP_PLAYLISTS_COVERS.glob("*.png")]

            _emit(70, texts.LOAD_PROGRESS_LOCALES)
            locales_dict, locales_items = self.data_service.load_locales_data()

            _emit(80, texts.LOAD_PROGRESS_SONGS)
            songs_list = self.data_service.load_songs_data(self.use_songs_json)
            songs_list_sorted = sorted(songs_list, key=lambda x: x["CodeName"])

            if not self.use_songs_json:
                _emit(90, texts.LOAD_PROGRESS_SAVE_SONGS)
                self.data_service.save_songs_json(songs_list_sorted)

            _emit(95, texts.LOAD_PROGRESS_PLAYLISTS)
            songs_dict = {song["CodeName"]: song for song in songs_list_sorted}
            playlists_payload = self.data_service.build_playlists_data(locales_dict, songs_dict)

            payload = {
                "locales_items": locales_items,
                "songs_list": songs_list_sorted,
                "playlists": playlists_payload,
                "cover_errors": cover_errors,
                "songs_generated_at": generated_at,
                "cover_png_paths": cover_png_paths,
            }

            self.finished.emit(payload)
        except Exception as e:
            logging.exception(f"Background load failed: {e}")
            self.error.emit(str(e))
