import json
import logging
from collections import OrderedDict
from pathlib import Path

from ..ui.shared import constants, texts
from .. import config
from ..utils import playlist_covers as playlist_covers
from ..utils import localisation as localisation
from ..utils import ipk_manager as ipk_manager
from ..utils import utils as utils

from PySide6.QtCore import Qt

from ..ui.shared.constants import PLAYLIST_COVER_PNG_PATH_ROLE

class SaveCancelled(Exception):
    pass


class SaveService:
    """Encapsulates save pipeline steps."""

    def __init__(
        self,
        playlists_tree_controller,
        data_service=None,
        use_songs_json=False,
    ):
        self._playlists_tree_controller = playlists_tree_controller
        self._data_service = data_service
        steps = []

        steps.append((texts.SAVE_STEP_DELETE_COVERS, self._delete_pending_cover_assets))

        steps.append((texts.SAVE_STEP_GENERATE_COVERS, self._generate_all_cover_assets))

        steps.extend([
            (texts.SAVE_STEP_SAVE_LOCALISATION, self._save_localisation_loc8),
            (texts.SAVE_STEP_SAVE_PLAYLISTS, self._save_playlists_json),
            (texts.SAVE_STEP_REPACK, self._repack_patch_nx),
        ])

        self._steps = steps
        self._progress_callback = None
        self._cancel_check = None
        self._current_step_idx = 0
        self._current_step_total = len(self._steps)
        self._current_step_base = 0
        self._current_step_span = 0
        self._step_weights = {
            texts.SAVE_STEP_DELETE_COVERS: (0, 5),
            texts.SAVE_STEP_GENERATE_COVERS: (5, 20),
            texts.SAVE_STEP_SAVE_LOCALISATION: (20, 30),
            texts.SAVE_STEP_SAVE_PLAYLISTS: (30, 70),
            texts.SAVE_STEP_REPACK: (70, 100),
        }

    def run(self, progress_callback=None, cancel_check=None):
        """Run all save steps in order."""
        self._progress_callback = progress_callback
        self._cancel_check = cancel_check
        total = len(self._steps)
        self._current_step_total = total
        for idx, (message, func) in enumerate(self._steps, start=1):
            self._current_step_idx = idx
            start, end = self._step_weights.get(message, (0, 0))
            self._current_step_base = start
            self._current_step_span = max(end - start, 0)
            self._emit_progress(message, percent=start)
            self._raise_if_cancelled()
            func()
            self._raise_if_cancelled()
            if end:
                end_percent = end
                if end_percent > 99:
                    end_percent = 99
                self._emit_progress(message, percent=end_percent)

    def _emit_progress(self, message, percent=None):
        if self._progress_callback:
            if percent is not None:
                self._progress_callback(int(percent), 100, message)
            else:
                self._progress_callback(self._current_step_idx, self._current_step_total, message)

    def _emit_substep_progress(self, idx, total, message):
        base = self._current_step_base
        span = self._current_step_span
        if not span:
            self._emit_progress(message)
            return
        if total:
            pct = base + int((idx / total) * span)
        else:
            pct = base
        max_pct = base + span
        if pct > max_pct:
            pct = max_pct
        if pct > 99:
            pct = 99
        self._emit_progress(message, percent=pct)

    def _raise_if_cancelled(self):
        if self._cancel_check and self._cancel_check():
            raise SaveCancelled()

    def _delete_pending_cover_assets(self):
        if self._playlists_tree_controller:
            self._playlists_tree_controller.delete_pending_cover_assets()

    def _generate_all_cover_assets(self):
        """Generate playlist cover assets from temp PNGs."""
        logging.info("Generating all playlist cover assets...")
        cover_paths = self._collect_playlist_cover_png_paths()
        if not cover_paths:
            logging.info("No playlist cover PNGs found in treePlaylists.")
            return

        seen = set()
        total = len(cover_paths)
        for idx, cover_path in enumerate(cover_paths, start=1):
            self._raise_if_cancelled()
            try:
                png_file = Path(cover_path)
                if not png_file.exists():
                    logging.warning("Cover PNG not found: %s", cover_path)
                    continue
                resolved = str(png_file.resolve()).lower()
                if resolved in seen:
                    continue
                seen.add(resolved)

                self._emit_substep_progress(
                    idx,
                    total,
                    f"{texts.SAVE_STEP_GENERATE_COVERS} ({idx}/{total}): {png_file.name}"
                )

                output_folder = config.INPUT_COVERS_FOLDER
                logging.debug("Processing PNG: %s", png_file)
                playlist_covers.process_playlist_assets(png_file, output_folder)
            except Exception as e:
                logging.exception("Failed to process playlist cover [%s]: %s", cover_path, e)

        logging.info("Finished generating all playlist cover assets.")

    def _collect_playlist_cover_png_paths(self):
        """Collect cover PNG paths for all playlists currently in the tree."""
        covers = []
        if not self._playlists_tree_controller:
            return covers

        try:
            for section_item in self._playlists_tree_controller.get_section_items():
                for playlist_item in self._playlists_tree_controller.get_playlist_items(section_item):
                    cover_path = playlist_item.data(0, PLAYLIST_COVER_PNG_PATH_ROLE) or ""
                    if not cover_path:
                        data = playlist_item.data(0, Qt.UserRole) or {}
                        cover_path = data.get("coverPngPath", "")
                    if not cover_path:
                        data = playlist_item.data(0, Qt.UserRole) or {}
                        cover_path = utils.resolve_cover_png_path(data.get("coverPath", ""))
                    if cover_path:
                        covers.append(str(cover_path))
        except Exception as e:
            logging.exception("Failed to collect playlist cover PNG paths: %s", e)

        return covers


    def _save_localisation_loc8(self):
        """Save localisation loc8 files from temp JSON."""
        logging.info("Saving localisation loc8 files...")
        loc8_files = list(config.INPUT_LOCALISATION_FOLDER.glob("*.loc8"))
        total = len(loc8_files)
        for idx, loc8_file in enumerate(loc8_files, start=1):
            self._raise_if_cancelled()
            self._emit_substep_progress(
                idx,
                total,
                f"{texts.SAVE_STEP_SAVE_LOCALISATION} ({idx}/{total}): {loc8_file.name}"
            )
            try:
                logging.debug(f"Processing localisation file: {loc8_file}")
                def _loc_progress(item_idx, item_total, _id=None):
                    self._emit_substep_progress(
                        item_idx,
                        item_total,
                        f"{texts.SAVE_STEP_SAVE_LOCALISATION} ({idx}/{total}): {loc8_file.name}"
                    )
                localisation.compress(
                    config.TEMP_LOCALISATION_JSON,
                    loc8_file,
                    legacy=config.LOCALISATION_LEGACY_ESCAPE,
                    progress_callback=_loc_progress,
                )
            except Exception as e:
                logging.exception(f"Failed to save localisation loc8 [{loc8_file}]: {e}")
        logging.info("Finished saving localisation loc8 files.")

    def _save_playlists_json(self):
        """Save playlists JSON/CKD files."""

        def _coerce_int(value):
            try:
                if isinstance(value, int):
                    return value
                if isinstance(value, str):
                    stripped = value.strip()
                    if stripped and stripped.isdigit():
                        return int(stripped)
                if isinstance(value, float) and value.is_integer():
                    return int(value)
            except Exception:
                pass
            return value

        logging.info("Saving playlists JSON/CKD files...")
        #Ensure section requests are rebuilt from current tree state
        # if self._playlists_tree_controller:
        #     for section_item in self._playlists_tree_controller.get_section_items():
        #         self._playlists_tree_controller.update_section_requests(section_item)
        # self._emit_progress(f"{texts.SAVE_STEP_SAVE_PLAYLISTS}: gc_carousel_rules.json.ckd")

        logging.info("Mouting gc_carousel_rules.json.ckd...")
        # Open gc_carousel_rules.json.ckd from input
        json_gc_carousel_rules = json.loads(config.INPUT_SECTIONS_FILE.read_bytes().decode('utf-8'))

        # Clear categories
        json_gc_carousel_rules["rules"]["/jd2022-playlists"]["categories"] = []

        # Iterate over treePlaylists and save each section to gc_carousel_rules
        for section_item in self._playlists_tree_controller.get_section_items():
            logging.debug(f"Processing section: {section_item.text(0)}")
            section_data = dict(section_item.data(0, Qt.UserRole) or {})
            if "titleId" in section_data:
                section_data["titleId"] = _coerce_int(section_data.get("titleId"))
            if "requests" in section_data and isinstance(section_data["requests"], list):
                ordered_requests = []
                for req in section_data["requests"]:
                    if isinstance(req, dict):
                        ordered_req = OrderedDict()
                        ordered_req["__class"] = req.get("__class", "JD_CarouselPlaylistsRequestDesc")
                        ordered_req["act"] = req.get("act", "ui_carousel")
                        ordered_req["isc"] = req.get("isc", "grp_row")
                        ordered_req["playlistID"] = req.get("playlistID")
                        ordered_req["type"] = req.get("type", "edito-pinned")
                        for key, value in req.items():
                            if key not in ordered_req:
                                ordered_req[key] = value
                        ordered_requests.append(ordered_req)
                    else:
                        ordered_requests.append(req)
                section_data["requests"] = ordered_requests

            ordered_section = OrderedDict()
            ordered_section["__class"] = section_data.get("__class", "CategoryRule")
            ordered_section["act"] = section_data.get("act", "ui_carousel")
            ordered_section["isc"] = section_data.get("isc", "grp_row")
            ordered_section["title"] = section_data.get("title")
            ordered_section["titleId"] = section_data.get("titleId")
            ordered_section["requests"] = section_data.get("requests", [])

            for key, value in section_data.items():
                if key not in ordered_section:
                    ordered_section[key] = value

            json_gc_carousel_rules["rules"]["/jd2022-playlists"]["categories"].append(ordered_section)

        logging.info("Writing updated gc_carousel_rules.json.ckd...")
        # Write updated gc_carousel_rules.json.ckd as bytes
        config.INPUT_SECTIONS_FILE.write_bytes(
            json.dumps(
                json_gc_carousel_rules,
                ensure_ascii=False
            ).encode('utf-8')
        )

        self._emit_substep_progress(1, 2, f"{texts.SAVE_STEP_SAVE_PLAYLISTS}: gc_carousel_rules.json.ckd")
        logging.info("Mounting playlists.json.ckd...")
        # Open playlists.json.ckd from input
        json_playlists = json.loads(config.INPUT_PLAYLISTS_FILE.read_bytes().decode('utf-8'))

        # Clear playlists
        json_playlists["playlists"] = {}

        # Iterate over treePlaylists and save each playlist to playlists.json
        for section_item in self._playlists_tree_controller.get_section_items():
            for playlist_item in self._playlists_tree_controller.get_playlist_items(section_item):
                logging.debug(f"Processing playlist: {playlist_item.text(0)}")
                playlist_data = dict(playlist_item.data(0, Qt.UserRole) or {})
                if "titleId" in playlist_data:
                    playlist_data["titleId"] = _coerce_int(playlist_data.get("titleId"))
                if "descriptionId" in playlist_data:
                    playlist_data["descriptionId"] = _coerce_int(playlist_data.get("descriptionId"))

                ordered_playlist = OrderedDict()
                ordered_playlist["__class"] = playlist_data.get("__class", "OfflinePlaylist")
                ordered_playlist["titleId"] = playlist_data.get("titleId")
                ordered_playlist["descriptionId"] = playlist_data.get("descriptionId")
                ordered_playlist["coverPath"] = playlist_data.get("coverPath")
                ordered_playlist["maps"] = list(playlist_data.get("maps", []))

                for key, value in playlist_data.items():
                    if key not in ordered_playlist:
                        ordered_playlist[key] = value

                playlist_id = playlist_item.data(0, constants.PLAYLIST_ID_ROLE)
                if not playlist_id:
                    continue
                json_playlists["playlists"][playlist_id] = ordered_playlist
        
        logging.info("Writing updated playlists.json.ckd...")
        # Write updated playlists.json.ckd as bytes
        config.INPUT_PLAYLISTS_FILE.write_bytes(
            json.dumps(
                json_playlists,
                ensure_ascii=False
            ).encode('utf-8')
        )
        
        self._emit_substep_progress(2, 2, f"{texts.SAVE_STEP_SAVE_PLAYLISTS}: playlists.json.ckd")
        logging.info("Finished saving playlists JSON/CKD files.")


    def _repack_patch_nx(self):
        """Repack patch_nx to output."""
        self._emit_progress(f"{texts.SAVE_STEP_REPACK}: patch_nx.ipk", percent=self._current_step_base)
        logging.info("Repacking patch_nx.ipk...")
        def _pack_progress(idx, total, name):
            self._emit_substep_progress(
                idx,
                total,
                f"{texts.SAVE_STEP_REPACK} ({idx}/{total}): {name}"
            )
        ipk_manager.pack(
            config.INPUT_PATCH_NX_FOLDER,
            config.OUTPUT_PATCH_NX_FILE,
            progress_callback=_pack_progress,
        )
        self._emit_progress(f"{texts.SAVE_STEP_REPACK}: patch_nx.ipk", percent=min(self._current_step_base + self._current_step_span - 1, 99))
        logging.info("Finished repacking patch_nx.ipk.")
