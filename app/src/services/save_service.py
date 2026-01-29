import json
import logging
from pathlib import Path

from ui.shared import constants, texts
import config
import utils.playlist_covers as playlist_covers
import utils.localisation as localisation
import utils.ipk_manager as ipk_manager

from PySide6.QtCore import Qt

from ui.shared.constants import PLAYLIST_COVER_PNG_PATH_ROLE

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

    def run(self, progress_callback=None):
        """Run all save steps in order."""
        total = len(self._steps)
        for idx, (message, func) in enumerate(self._steps, start=1):
            if progress_callback:
                progress_callback(idx, total, message)
            func()

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
        for cover_path in cover_paths:
            try:
                png_file = Path(cover_path)
                if not png_file.exists():
                    logging.warning("Cover PNG not found: %s", cover_path)
                    continue
                resolved = str(png_file.resolve()).lower()
                if resolved in seen:
                    continue
                seen.add(resolved)

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
                    if cover_path:
                        covers.append(str(cover_path))
        except Exception as e:
            logging.exception("Failed to collect playlist cover PNG paths: %s", e)

        return covers

    def _save_localisation_loc8(self):
        """Save localisation loc8 files from temp JSON."""
        logging.info("Saving localisation loc8 files...")
        for loc8_file in config.INPUT_LOCALISATION_FOLDER.glob("*.loc8"):
            try:
                logging.debug(f"Processing localisation file: {loc8_file}")
                localisation.compress(
                    config.TEMP_LOCALISATION_JSON,
                    loc8_file,
                    legacy=config.LOCALISATION_LEGACY_ESCAPE,
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
                section_data["requests"] = list(section_data["requests"])
            json_gc_carousel_rules["rules"]["/jd2022-playlists"]["categories"].append(section_data)

        logging.info("Writing updated gc_carousel_rules.json.ckd...")
        # Write updated gc_carousel_rules.json.ckd as bytes
        config.INPUT_SECTIONS_FILE.write_bytes(
            json.dumps(
                json_gc_carousel_rules,
                ensure_ascii=False
            ).encode('utf-8')
        )

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
                playlist_id = playlist_item.data(0, constants.PLAYLIST_ID_ROLE)
                if not playlist_id:
                    continue
                json_playlists["playlists"][playlist_id] = playlist_data
        
        logging.info("Writing updated playlists.json.ckd...")
        # Write updated playlists.json.ckd as bytes
        config.INPUT_PLAYLISTS_FILE.write_bytes(
            json.dumps(
                json_playlists,
                ensure_ascii=False
            ).encode('utf-8')
        )
        
        logging.info("Finished saving playlists JSON/CKD files.")


    def _repack_patch_nx(self):
        """Repack patch_nx to output."""

        logging.info("Repacking patch_nx.ipk...")
        ipk_manager.pack(config.INPUT_PATCH_NX_FOLDER, config.OUTPUT_PATCH_NX_FILE)
        logging.info("Finished repacking patch_nx.ipk.")
