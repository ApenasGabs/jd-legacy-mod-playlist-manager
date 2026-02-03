import datetime
import json
import logging
import re
from pathlib import Path

from .. import config
from ..utils import playlist_covers as playlist_covers
from ..utils import ipk_manager as ipk_manager
from ..utils import utils as utils
from ..ui.shared import texts


class DataService:
    def _build_song_payload(self, song_code, song_data):
        """Build song payload for playlists tree UI."""
        title = song_data.get("Title") if song_data else ""
        artist = song_data.get("Artist") if song_data else ""
        parts = [p for p in (title, artist) if p]
        song_string = " - ".join(parts) if parts else str(song_code)

        missing_message = None
        missing_code = None
        if not song_data:
            missing_code = song_code
            missing_message = texts.SONG_NOT_FOUND_MESSAGE.format(code=song_code)
            song_string = texts.SONG_NOT_FOUND_SHORT

        return {
            "code": song_code,
            "song_data": song_data,
            "song_string": song_string,
            "missing_message": missing_message,
            "missing_code": missing_code,
        }


    def _parse_songdesc_file(self, songdesc_ckd_path: Path):
        """Parse songdesc.tpl.ckd and return song JSON or (None, error message)."""
        decode_error = None
        try:
            try:
                file_content = songdesc_ckd_path.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                decode_error = e
                file_content = songdesc_ckd_path.read_text(encoding="utf-8", errors="ignore")

            decoder = json.JSONDecoder()
            song_data, _ = decoder.raw_decode(file_content)
        except json.JSONDecodeError as json_err:
            try:
                fixed_content = re.sub(r"(\d)\"\s*[\,\}]", r"\1,", file_content)
                decoder = json.JSONDecoder()
                song_data, _ = decoder.raw_decode(fixed_content)
            except (json.JSONDecodeError, Exception) as e:
                decode_note = f" | UTF-8 decode error: {decode_error}" if decode_error else ""
                error_msg = f"Error processing [{songdesc_ckd_path}]: {json_err} | {e}{decode_note}"
                return None, error_msg

        if not song_data:
            return None, texts.DATA_EMPTY_SONG_DATA.format(path=songdesc_ckd_path)

        return song_data["COMPONENTS"][0], None

    def _build_song_entry(self, song_json: dict, maps_dir: Path, songdesc_ckd_path: Path) -> dict:
        """Build normalized song entry for tblSongs."""
        map_name = song_json["MapName"]
        map_lower = map_name.lower()
        return {
            "CodeName": map_name,
            "Title": song_json["Title"],
            "Artist": song_json["Artist"],
            "JDVersion": str(song_json["JDVersion"]) if "JDVersion" in song_json else "",
            "OriginalJDVersion": str(song_json["OriginalJDVersion"]) if "OriginalJDVersion" in song_json else "",
            "SourceFilePath": str(songdesc_ckd_path),
            "AudioFilePaths": [
                str(maps_dir / "world" / "maps" / map_lower / "audio" / f"{map_lower}.ogg"),
                str(maps_dir / "world" / "maps" / map_lower / "audio" / f"{map_name}.ogg"),
                str(maps_dir / "world" / "maps" / map_lower / "autodance" / f"{map_lower}.ogg"),
            ],
            "VideoFilePath": str(maps_dir / "world" / "maps" / map_lower / "videoscoach" / f"{map_lower}.vp9.720.webm"),
            "FullData": song_json,
        }

    def clear_directory_contents_worker(self, directory_path, log_label=None, progress_callback=None):
        """Delete all files and subfolders inside a directory (worker-safe)."""
        label = log_label or str(directory_path)
        logging.info(f"Clearing directory contents: {label}")
        if not directory_path.exists():
            return {"deleted": 0, "failed": 0, "remaining": 0}
        items = list(directory_path.iterdir())
        total = len(items)
        deleted = 0
        failed = 0
        for idx, item in enumerate(items, start=1):
            try:
                if item.is_dir():
                    import os
                    import shutil
                    def _onerror(func, path, exc_info):
                        try:
                            os.chmod(path, 0o700)
                            func(path)
                        except Exception:
                            pass
                    shutil.rmtree(item, onerror=_onerror)
                else:
                    item.unlink()
                deleted += 1
            except Exception as e:
                failed += 1
                logging.warning(f"Failed to delete item [{item}]: {e}")
            if progress_callback:
                try:
                    progress_callback(idx, total, item.name)
                except Exception:
                    pass
        try:
            remaining = len(list(directory_path.iterdir()))
        except Exception:
            remaining = 0
        logging.info(
            "Clearing directory contents done: deleted=%s failed=%s remaining=%s",
            deleted,
            failed,
            remaining,
        )
        return {"deleted": deleted, "failed": failed, "remaining": remaining}

    def ensure_patch_nx_extracted_worker(self, progress_callback=None):
        """Extract patch_nx.ipk only if patch_nx folder is missing (worker-safe)."""
        patch_folder = config.EXTRACTED_DIR / "patch_nx"
        if patch_folder.exists():
            return

        patch_ipk = config.get_patch_nx_path()
        if not patch_ipk or not patch_ipk.exists():
            raise RuntimeError(texts.DATA_PATCH_NX_NOT_FOUND)

        logging.info("Extracting patch_nx.ipk only...")
        patch_folder.mkdir(parents=True, exist_ok=True)
        ipk_manager.extract(patch_ipk, output_dir=patch_folder, progress_callback=progress_callback)

    def extract_mod_files_worker(self, progress_callback=None, cancel_check=None):
        """Extract all .ipk files without UI interactions (worker-safe)."""
        ipk_files = list(config.INPUT_MOD_ROOT_DIR.glob("*.ipk"))
        if not ipk_files:
            raise RuntimeError(texts.DATA_NO_IPK_FILES_FOUND)

        logging.info(f"Found {len(ipk_files)} .ipk files to extract.")
        error_files = []
        total = len(ipk_files)
        for idx, ipk in enumerate(ipk_files, start=1):
            if cancel_check and cancel_check():
                logging.info("IPK extraction cancelled by user.")
                return
            if progress_callback:
                progress_callback(idx, total, ipk.name)
            output_folder = config.EXTRACTED_DIR / ipk.stem
            output_folder.mkdir(exist_ok=True)
            logging.info(f"Extracting file [{ipk.name}] to folder [{output_folder}]")
            try:
                ipk_manager.extract(ipk, output_dir=output_folder, cancel_check=cancel_check)
            except Exception as e:
                if cancel_check and cancel_check():
                    logging.info("IPK extraction cancelled by user.")
                    return
                error_files.append(ipk.name)
                logging.exception(f"Error extracting:\n{ipk.name}\nError: {e}")
            else:
                logging.info(f"Successfully extracted [{ipk.name}].")

        if error_files:
            raise RuntimeError(texts.DATA_EXTRACT_IPK_ERRORS.format(errors="\n".join(error_files)))

        logging.info("IPK extraction completed successfully.")

    def extract_playlist_covers_worker(self, progress_callback=None, cancel_check=None):
        """Extract playlist covers without UI interactions (worker-safe)."""
        logging.info("Decompressing playlist cover textures.")
        error_covers = []
        cover_files = list(config.INPUT_COVERS_FOLDER.glob("*.tga.ckd"))
        total = len(cover_files)
        for idx, tga_ckd in enumerate(cover_files, start=1):
            if cancel_check and cancel_check():
                logging.info("Cover extraction cancelled by user.")
                return error_covers
            if progress_callback:
                progress_callback(idx, total, tga_ckd.stem)
            try:
                logging.debug(f"Extracting cover from [{tga_ckd}]")
                output_stem = tga_ckd.stem
                if output_stem.endswith(".tga"):
                    output_stem = output_stem[:-4]
                output_png = config.TEMP_PLAYLISTS_COVERS / f"{output_stem}.png"
                playlist_covers.tga_ckd_to_png(tga_ckd, output_png, progress_callback=None)
                logging.debug(f"Extracted and converted cover [{tga_ckd.name}] to PNG [{output_png}]")
            except Exception as e:
                error_covers.append(tga_ckd.name)
                logging.exception(f"Error extracting cover from:\n{tga_ckd.name}\nError: {e}")
        if not error_covers:
            logging.info("Playlist cover texture decompression completed.")
        return error_covers

    def load_locales_data(self):
        """Load localization JSON and return (dict, reversed items list)."""
        logging.info("Loading localization JSON file...")
        with open(config.TEMP_LOCALISATION_JSON, "r", encoding="utf-8") as f:
            locales_dict = json.load(f)
        logging.info(f"Localization JSON loaded: {len(locales_dict)} items")

        locales_items = list(locales_dict.items())
        locales_items.reverse()
        return locales_dict, locales_items

    def load_songs_data(self, use_songs_json: bool):
        """Load songs list from JSON or extracted folders (data-only)."""
        if use_songs_json:
            logging.info("Loading songs from songs.json...")
            return self.load_songs_from_json()
        logging.info("Populating songs from extracted maps folders...")
        return self.load_songs_from_extracted_maps_folders()

    def build_playlists_data(self, locales_dict, songs_dict, progress_callback=None):
        """Build playlists payload for UI rendering (data-only)."""
        sections_list = json.loads(config.INPUT_SECTIONS_FILE.read_text(encoding="utf-8"))["rules"]["/jd2022-playlists"]["categories"]
        playlists_list = json.loads(config.INPUT_PLAYLISTS_FILE.read_text(encoding="utf-8"))["playlists"]

        payload = []
        total_sections = len(sections_list)
        for idx, section in enumerate(sections_list, start=1):
            if progress_callback:
                try:
                    section_name = section.get("title", "") if isinstance(section, dict) else ""
                    progress_callback(idx, total_sections, section_name)
                except Exception:
                    pass
            section_name = section["title"] if "title" in section else locales_dict.get(section["titleId"], "")
            section_payload = {
                "title": section_name,
                "titleId": section.get("titleId", ""),
                "playlists": []
            }

            for playlist in section.get("requests", []):
                playlist_title_id = str(playlists_list[playlist["playlistID"]]["titleId"])
                playlist_description_id = str(playlists_list[playlist["playlistID"]]["descriptionId"])
                title_text = locales_dict.get(playlist_title_id, "")
                description_text = locales_dict.get(playlist_description_id, "")
                cover_png_path = utils.resolve_cover_png_path(playlists_list[playlist["playlistID"]]["coverPath"])

                playlist_data = {
                    "playlistID": playlist["playlistID"],
                    "titleId": playlist_title_id,
                    "titleText": title_text,
                    "descriptionId": playlist_description_id,
                    "descriptionText": description_text,
                    "coverPath": playlists_list[playlist["playlistID"]]["coverPath"],
                    "coverPngPath": cover_png_path,
                    "songs": playlists_list[playlist["playlistID"]]["maps"]
                }

                songs_payload = []
                for song in playlist_data["songs"]:
                    song_data = songs_dict.get(song, {})
                    songs_payload.append(self._build_song_payload(song, song_data))

                section_payload["playlists"].append({
                    "playlist_data": playlist_data,
                    "songs": songs_payload
                })

            payload.append(section_payload)

        return payload

    def save_songs_json(self, songs_list):
        """Persist songs data to data/songs.json for future fast loading."""
        output_path = config.DATA_DIR / "songs.json"

        def _rel_path(path_value):
            if not path_value:
                return path_value
            try:
                p = Path(path_value).resolve()
                rel = p.relative_to(config.BASE_DIR)
                return rel.as_posix()
            except Exception:
                return path_value

        export_songs = []
        for song in songs_list:
            song_copy = dict(song)
            song_copy["SourceFilePath"] = _rel_path(song_copy.get("SourceFilePath"))
            song_copy["VideoFilePath"] = _rel_path(song_copy.get("VideoFilePath"))
            audio_paths = song_copy.get("AudioFilePaths") or []
            song_copy["AudioFilePaths"] = [_rel_path(p) for p in audio_paths]
            export_songs.append(song_copy)

        payload = {
            "generatedAt": datetime.datetime.now().isoformat(),
            "pathBase": ".",
            "count": len(songs_list),
            "songs": export_songs,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.info(f"songs.json saved: {output_path}")

    def load_songs_from_extracted_maps_folders(self, progress_callback=None):
        """Load tblSongs by scanning extracted maps folders."""
        songs_list = []
        extracted_maps_dirs = [d for d in config.EXTRACTED_DIR.iterdir() if d.is_dir() and d.name.startswith("maps_")]

        total_folders_analyzed = 0
        error_folders = []

        songdesc_paths = []
        for maps_dir in extracted_maps_dirs:
            cache_itf_path = maps_dir / "cache" / "itf_cooked" / "nx" / "world" / "maps"
            if not cache_itf_path.exists():
                continue

            for song_dir in cache_itf_path.iterdir():
                if not song_dir.is_dir():
                    continue

                songdesc_ckd_path = song_dir / "songdesc.tpl.ckd"
                if not songdesc_ckd_path.exists():
                    continue

                songdesc_paths.append((maps_dir, songdesc_ckd_path))

        total_candidates = len(songdesc_paths)
        for idx, (maps_dir, songdesc_ckd_path) in enumerate(songdesc_paths, start=1):
            total_folders_analyzed += 1
            if progress_callback:
                try:
                    progress_callback(idx, total_candidates, songdesc_ckd_path.name)
                except Exception:
                    pass

            try:
                song_json, error_msg = self._parse_songdesc_file(songdesc_ckd_path)
                if error_msg:
                    logging.error(error_msg, exc_info=True)
                    error_folders.append(str(songdesc_ckd_path))
                    continue
                if song_json:
                    songs_list.append(self._build_song_entry(song_json, maps_dir, songdesc_ckd_path))
            except Exception as e:
                error_msg = f"Error processing:\n{songdesc_ckd_path}\nError: {e}"
                logging.exception(error_msg)
                error_folders.append(str(songdesc_ckd_path))

        logging.info(f"Total folders analyzed: {total_folders_analyzed}")
        logging.info(f"Folders with errors: {len(error_folders)}")
        logging.info(f"Folders loaded successfully: {len(songs_list)}")

        if error_folders:
            error_list_str = "\n".join(error_folders)
            error_message = texts.DATA_SONGS_LOAD_FAILED.format(
                error_count=len(error_folders),
                total=total_folders_analyzed,
                loaded=len(songs_list),
                errors=len(error_folders),
                error_list=error_list_str,
            )
            logging.error(error_message)
            raise RuntimeError(error_message)

        return songs_list

    def load_songs_from_json(self):
        """Load tblSongs from cached data/songs.json."""
        input_path = config.DATA_DIR / "songs.json"
        if not input_path.exists():
            raise FileNotFoundError(texts.DATA_SONGS_JSON_NOT_FOUND)

        payload = json.loads(input_path.read_text(encoding="utf-8"))
        songs_list = payload.get("songs", [])

        def _abs_path(path_value):
            if not path_value:
                return path_value
            p = Path(path_value)
            if p.is_absolute():
                return str(p)
            return str((config.BASE_DIR / p).resolve())

        for song in songs_list:
            if "SourceFilePath" in song:
                song["SourceFilePath"] = _abs_path(song["SourceFilePath"])
            if "VideoFilePath" in song:
                song["VideoFilePath"] = _abs_path(song["VideoFilePath"])
            if "AudioFilePaths" in song:
                song["AudioFilePaths"] = [_abs_path(p) for p in song.get("AudioFilePaths") or []]

        return songs_list
