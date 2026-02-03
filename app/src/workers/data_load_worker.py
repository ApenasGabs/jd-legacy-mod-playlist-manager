import json
import logging

from PySide6.QtCore import QObject, Signal

from .. import config
from ..core.enums import LoadMode
from ..ui.shared import texts
from ..utils import localisation as localisation
from ..services.data_service import DataService


class DataLoadWorker(QObject):
    """Background worker to load data/extract files without blocking UI."""

    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)
    cancelled = Signal()

    def __init__(self, data_service: DataService, use_songs_json: bool, load_mode: LoadMode, clear_extracted: bool):
        super().__init__()
        self.data_service = data_service
        self.use_songs_json = use_songs_json
        self.load_mode = load_mode
        self.clear_extracted = clear_extracted
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    def _check_cancel(self) -> bool:
        return self._cancel_requested

    def run(self):
        try:
            def _emit(percent, message):
                self.progress.emit(int(percent), message)

            def _emit_detail(start_percent, end_percent, idx, total, message):
                span = max(end_percent - start_percent, 0)
                if total:
                    pct = start_percent + int((idx / total) * span)
                else:
                    pct = start_percent
                if pct > end_percent:
                    pct = end_percent
                _emit(pct, message)

            def _get_stages():
                if self.load_mode == LoadMode.JSON:
                    return {
                        "extract_patch": (0, 20),
                        "clear_temp": (20, 25),
                        "localisation": (25, 30),
                        "covers": (30, 60),
                        "locales": (60, 70),
                        "songs_json": (70, 80),
                        "playlists": (80, 90),
                    }
                if self.load_mode == LoadMode.EXTRACTED:
                    return {
                        "verify_patch": (0, 10),
                        "clear_temp": (10, 15),
                        "localisation": (15, 20),
                        "covers": (20, 50),
                        "locales": (50, 60),
                        "songs_maps": (60, 75),
                        "save_songs": (75, 80),
                        "playlists": (80, 90),
                    }
                return {
                    "clear_extracted": (0, 20),
                    "extract_ipk": (20, 60),
                    "clear_temp": (65, 70),
                    "localisation": (70, 75),
                    "covers": (75, 80),
                    "locales": (80, 85),
                    "songs_maps": (85, 90),
                    "save_songs": (90, 91),
                    "playlists": (91, 98),
                }

            stages = _get_stages()

            def _emit_stage(stage_key, message):
                start, _ = stages.get(stage_key, (0, 0))
                _emit(start, message)

            def _emit_stage_detail(stage_key, idx, total, message):
                start, end = stages.get(stage_key, (0, 0))
                _emit_detail(start, end, idx, total, message)

            generated_at = None
            if self.use_songs_json:
                try:
                    input_path = config.DATA_DIR / "songs.json"
                    if input_path.exists():
                        payload_meta = json.loads(input_path.read_text(encoding="utf-8"))
                        generated_at = payload_meta.get("generatedAt")
                except Exception as e:
                    logging.exception(f"Failed to read songs.json metadata: {e}")

            if self.load_mode == LoadMode.EXTRACTED:
                _emit_stage("verify_patch", texts.LOAD_PROGRESS_EXTRACT_PATCH)
                def _patch_progress(idx, total, name):
                    _emit_stage_detail("verify_patch", idx, total, f"{texts.LOAD_PROGRESS_EXTRACT_PATCH} ({idx}/{total}): {name}")
                self.data_service.ensure_patch_nx_extracted_worker(progress_callback=_patch_progress)

            if self.load_mode == LoadMode.IPK and self.clear_extracted:
                _emit_stage("clear_extracted", texts.LOAD_PROGRESS_CLEAR_EXTRACTED)
                def _clear_extracted_progress(idx, total, name):
                    _emit_stage_detail("clear_extracted", idx, total, f"{texts.LOAD_PROGRESS_CLEAR_EXTRACTED} ({idx}/{total}): {name}")
                self.data_service.clear_directory_contents_worker(
                    config.EXTRACTED_DIR,
                    "data/extracted",
                    progress_callback=_clear_extracted_progress,
                )

            if self._check_cancel():
                self.cancelled.emit()
                return

            if self.load_mode == LoadMode.IPK:
                _emit_stage("extract_ipk", texts.LOAD_PROGRESS_EXTRACT_ALL)
                def _ipk_progress(idx, total, name):
                    _emit_stage_detail("extract_ipk", idx, total, f"{texts.LOAD_PROGRESS_EXTRACT_ALL} ({idx}/{total}): {name}")
                self.data_service.extract_mod_files_worker(
                    progress_callback=_ipk_progress,
                    cancel_check=self._check_cancel,
                )
            elif self.load_mode == LoadMode.JSON:
                _emit_stage("extract_patch", texts.LOAD_PROGRESS_EXTRACT_PATCH)
                def _patch_progress(idx, total, name):
                    _emit_stage_detail("extract_patch", idx, total, f"{texts.LOAD_PROGRESS_EXTRACT_PATCH} ({idx}/{total}): {name}")
                self.data_service.ensure_patch_nx_extracted_worker(progress_callback=_patch_progress)

            if self._check_cancel():
                self.cancelled.emit()
                return

            _emit_stage("clear_temp", texts.LOAD_PROGRESS_CLEAR_TEMP)
            def _clear_temp_progress(idx, total, name):
                _emit_stage_detail("clear_temp", idx, total, f"{texts.LOAD_PROGRESS_CLEAR_TEMP} ({idx}/{total}): {name}")
            self.data_service.clear_directory_contents_worker(
                config.TEMP_DIR,
                "data/temp",
                progress_callback=_clear_temp_progress,
            )
            config.setup_directories(config.ALL_TEMP_DIRS)

            _emit_stage("localisation", texts.LOAD_PROGRESS_LOCALISATION)
            def _loc_progress(idx, total, _id=None):
                _emit_stage_detail(
                    "localisation",
                    idx,
                    total,
                    f"{texts.LOAD_PROGRESS_LOCALISATION} ({idx}/{total})"
                )
            localisation.decompress(
                config.INPUT_LOCALISATION_FILE,
                config.TEMP_LOCALISATION_JSON,
                legacy=config.LOCALISATION_LEGACY_ESCAPE,
                progress_callback=_loc_progress,
            )

            if self._check_cancel():
                self.cancelled.emit()
                return

            cover_errors = []
            _emit_stage("covers", texts.LOAD_PROGRESS_COVERS)
            def _cover_progress(idx, total, name):
                _emit_stage_detail("covers", idx, total, f"{texts.LOAD_PROGRESS_COVERS} ({idx}/{total}): {name}")
            cover_errors = self.data_service.extract_playlist_covers_worker(
                progress_callback=_cover_progress,
                cancel_check=self._check_cancel,
            )
            cover_png_paths = [str(p) for p in config.TEMP_PLAYLISTS_COVERS.glob("*.png")]

            if self._check_cancel():
                self.cancelled.emit()
                return

            _emit_stage("locales", texts.LOAD_PROGRESS_LOCALES)
            locales_dict, locales_items = self.data_service.load_locales_data()

            if self.load_mode == LoadMode.JSON:
                _emit_stage("songs_json", texts.LOAD_PROGRESS_SONGS)
                songs_list = self.data_service.load_songs_from_json()
            else:
                _emit_stage("songs_maps", texts.LOAD_PROGRESS_SONGS)
                def _songs_progress(idx, total, name):
                    _emit_stage_detail("songs_maps", idx, total, f"{texts.LOAD_PROGRESS_SONGS} ({idx}/{total}): {name}")
                songs_list = self.data_service.load_songs_from_extracted_maps_folders(progress_callback=_songs_progress)
            songs_list_sorted = sorted(songs_list, key=lambda x: x["CodeName"])

            if not self.use_songs_json:
                _emit_stage("save_songs", texts.LOAD_PROGRESS_SAVE_SONGS)
                self.data_service.save_songs_json(songs_list_sorted)
            _emit_stage("playlists", texts.LOAD_PROGRESS_PLAYLISTS)
            songs_dict = {song["CodeName"]: song for song in songs_list_sorted}
            def _playlists_progress(idx, total, name):
                _emit_stage_detail("playlists", idx, total, f"{texts.LOAD_PROGRESS_PLAYLISTS} ({idx}/{total}): {name}")
            playlists_payload = self.data_service.build_playlists_data(
                locales_dict,
                songs_dict,
                progress_callback=_playlists_progress,
            )

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
