import json
import logging

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QBrush, QColor, QFont, QPixmap, QTextCursor
from PySide6.QtWidgets import QCheckBox, QMessageBox, QTreeWidgetItem

from ... import config
from ..shared.constants import (
    TREE_ITEM_TYPE_ROLE,
    MISSING_SONG_MESSAGE_ROLE,
    MISSING_SONG_CODE_ROLE,
    SONG_CODE_ROLE,
    PLAYLIST_ID_ROLE,
    PLAYLIST_TITLE_TEXT_ROLE,
    PLAYLIST_DESCRIPTION_TEXT_ROLE,
    PLAYLIST_COVER_PNG_PATH_ROLE,
    SECTION_TITLE_ROLE,
    SECTION_TITLE_ID_ROLE,
    TreeItemType,
)
from ..utils.utils import set_label_pixmap
from ..shared import texts


class PlaylistsTreeController:
    """UI logic for the playlists tree in main window."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.pending_cover_assets_to_delete = set()
        self._last_cover_path = ""

    def populate_playlists(self, playlists_payload):
        """Populate Playlist Tree (UI-only)."""
        try:
            logging.info("populate_playlists thread=%s tree_thread=%s", QThread.currentThread(), self.main_window.ui.treePlaylists.thread())
        except Exception:
            pass
        tree = self.main_window.ui.treePlaylists
        tree.clear()

        for section in playlists_payload:
            section_name = section.get("title", "")
            section_title_id = section.get("titleId", "")
            section_item = QTreeWidgetItem(tree)
            section_item.setText(0, section_name)
            section_item.setData(0, SECTION_TITLE_ROLE, section_name)
            section_item.setData(0, SECTION_TITLE_ID_ROLE, section_title_id)
            section_item.setData(0, Qt.UserRole, self._build_section_role_data(section_name, section_title_id, []))
            section_item.setData(0, TREE_ITEM_TYPE_ROLE, TreeItemType.SECTION.value)
            section_font = QFont()
            section_font.setPointSize(14)
            section_item.setFont(0, section_font)
            section_item.setForeground(0, QBrush(QColor("#FF0000")))
            section_item.setFlags(
                section_item.flags()
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
            )
            section_item.setExpanded(True)

            for playlist_entry in section.get("playlists", []):
                playlist_data = playlist_entry.get("playlist_data", {})

                playlist_id = playlist_data.get("playlistID", "")
                description_text = playlist_data.get("descriptionText", "")
                cover_png_path = playlist_data.get("coverPngPath", "")
                title_text = playlist_data.get("titleText", "")

                maps_list = playlist_data.get("maps", None)
                if maps_list is None:
                    maps_list = playlist_data.get("songs", [])

                role_data = {
                    "__class": playlist_data.get("__class", "OfflinePlaylist"),
                    "titleId": playlist_data.get("titleId", ""),
                    "descriptionId": playlist_data.get("descriptionId", ""),
                    "coverPath": playlist_data.get("coverPath", ""),
                    "maps": list(maps_list or []),
                }

                playlist_item = QTreeWidgetItem(section_item)
                playlist_item.setText(0, f'{playlist_id}: "{title_text} - {description_text}"')
                playlist_item.setData(0, PLAYLIST_ID_ROLE, playlist_id)
                playlist_item.setData(0, PLAYLIST_TITLE_TEXT_ROLE, title_text)
                playlist_item.setData(0, PLAYLIST_DESCRIPTION_TEXT_ROLE, description_text)
                playlist_item.setData(0, PLAYLIST_COVER_PNG_PATH_ROLE, cover_png_path)
                playlist_item.setData(0, Qt.UserRole, role_data)
                playlist_item.setData(0, TREE_ITEM_TYPE_ROLE, TreeItemType.PLAYLIST.value)
                playlist_font = QFont()
                playlist_font.setPointSize(12)
                playlist_item.setFont(0, playlist_font)
                playlist_item.setForeground(0, QBrush(QColor("#214cce")))
                playlist_item.setFlags(
                    playlist_item.flags()
                    | Qt.ItemIsDragEnabled
                    | Qt.ItemIsDropEnabled
                )

                for song_entry in playlist_entry.get("songs", []):
                    song_code = song_entry.get("code", "")
                    song_data = song_entry.get("song_data", {})
                    song_string = song_entry.get("song_string", "")
                    missing_message = song_entry.get("missing_message")
                    missing_code = song_entry.get("missing_code")

                    song_item = QTreeWidgetItem(playlist_item)
                    song_item.setText(0, f'{song_code}: ({song_string})')
                    song_item.setData(0, SONG_CODE_ROLE, song_code)

                    if missing_message:
                        song_item.setBackground(0, QBrush(QColor("#FFCDD2")))
                        song_item.setForeground(0, QBrush(QColor("#000000")))
                        song_item.setData(0, MISSING_SONG_MESSAGE_ROLE, missing_message)
                        song_item.setData(0, MISSING_SONG_CODE_ROLE, missing_code)

                    song_item.setData(0, Qt.UserRole, song_data)
                    song_item.setData(0, TREE_ITEM_TYPE_ROLE, TreeItemType.SONG.value)
                    song_font = QFont()
                    song_font.setPointSize(10)
                    song_item.setFont(0, song_font)
                    song_item.setFlags(
                        (song_item.flags() | Qt.ItemIsDragEnabled)
                        & ~Qt.ItemIsDropEnabled
                    )

            self.update_section_requests(section_item)

    def _build_section_role_data(self, title, title_id, requests_list):
        return {
            "__class": "CategoryRule",
            "act": "ui_carousel",
            "isc": "grp_row",
            "title": title,
            "titleId": title_id,
            "requests": list(requests_list or []),
        }

    def _build_section_requests(self, section_item):
        requests = []
        if not section_item:
            return requests
        for i in range(section_item.childCount()):
            playlist_item = section_item.child(i)
            if not playlist_item or playlist_item.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.PLAYLIST.value:
                continue
            playlist_id = playlist_item.data(0, PLAYLIST_ID_ROLE)
            if not playlist_id:
                continue
            requests.append({
                "__class": "JD_CarouselPlaylistsRequestDesc",
                "isc": "grp_row",
                "act": "ui_carousel",
                "type": "edito-pinned",
                "playlistID": playlist_id,
            })
        return requests

    def update_section_requests(self, section_item):
        if not section_item or section_item.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.SECTION.value:
            return
        data = section_item.data(0, Qt.UserRole) or {}
        title = section_item.data(0, SECTION_TITLE_ROLE) or data.get("title") or section_item.text(0)
        title_id = section_item.data(0, SECTION_TITLE_ID_ROLE) or data.get("titleId") or ""
        section_item.setData(0, SECTION_TITLE_ROLE, title)
        section_item.setData(0, SECTION_TITLE_ID_ROLE, title_id)
        requests = self._build_section_requests(section_item)
        section_item.setData(0, Qt.UserRole, self._build_section_role_data(title, title_id, requests))

    def get_section_items(self):
        """Return top-level section items from treePlaylists."""
        items = []
        tree = self.main_window.ui.treePlaylists
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item and item.data(0, TREE_ITEM_TYPE_ROLE) == TreeItemType.SECTION.value:
                items.append(item)
        return items

    def get_playlist_items(self, section_item):
        """Return playlist items under a section."""
        items = []
        if not section_item or section_item.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.SECTION.value:
            return items
        for i in range(section_item.childCount()):
            child = section_item.child(i)
            if child and child.data(0, TREE_ITEM_TYPE_ROLE) == TreeItemType.PLAYLIST.value:
                items.append(child)
        return items

    def on_item_double_clicked(self, item, column):
        """Open edit for sections/playlists on double click."""
        try:
            if not item:
                return
            try:
                self.main_window.ui.treePlaylists.setFocus()
            except Exception:
                pass
            item_type = item.data(0, TREE_ITEM_TYPE_ROLE)
            if item_type == TreeItemType.SECTION.value:
                self.main_window.section_controller.open(mode="edit", item=item)
                return
            if item_type == TreeItemType.PLAYLIST.value:
                self.main_window.playlist_controller.open(mode="edit", item=item)
        except Exception as e:
            logging.exception(f"Error handling section double click: {e}")

    def on_item_clicked(self, item, column):
        """Show playlist cover when clicking a playlist; clear for sections/songs"""
        try:
            # Track last clicked tree item for debug shortcut
            self.main_window.last_click_source = "treePlaylists"
            self.main_window.last_clicked_tree_item = item
            try:
                self.main_window.ui.treePlaylists.setFocus()
            except Exception:
                pass
            item_type = item.data(0, TREE_ITEM_TYPE_ROLE)
            if item_type == TreeItemType.SONG.value:
                full_message = item.data(0, MISSING_SONG_MESSAGE_ROLE)
                missing_code = item.data(0, MISSING_SONG_CODE_ROLE)
                if full_message and not getattr(self.main_window, "suppress_missing_song_message", False):
                    msg = QMessageBox(self.main_window)
                    msg.setIcon(QMessageBox.Information)
                    msg.setWindowTitle(texts.SONG_NOT_FOUND_TITLE)
                    msg.setText(str(full_message))
                    btn_search = msg.addButton(texts.SONG_NOT_FOUND_ACTION, QMessageBox.ActionRole)
                    checkbox = QCheckBox(texts.SONG_NOT_FOUND_DONT_SHOW)
                    msg.setCheckBox(checkbox)
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec()
                    if msg.clickedButton() == btn_search and missing_code:
                        try:
                            self.main_window.ui.txtSearchSongs.setPlainText(str(missing_code))
                            self.main_window.ui.txtSearchSongs.moveCursor(QTextCursor.End)
                            self.main_window.ui.txtSearchSongs.setFocus()
                        except Exception as e:
                            logging.exception(f"Failed to apply song search filter: {e}")
                    if checkbox.isChecked():
                        self.main_window.suppress_missing_song_message = True

            if not getattr(self.main_window, "media_enabled", True):
                self.main_window.ui.lblImg.setPixmap(QPixmap())
                self.main_window.ui.lblImg.setText("")
                return

            if item_type == TreeItemType.PLAYLIST.value:
                # Clear any playing media/video before showing cover (only if playback is active)
                if hasattr(self.main_window, "media_controller"):
                    mc = self.main_window.media_controller
                    if getattr(mc, "current_media_path", None) or getattr(mc, "is_playing", False):
                        self.main_window._reset_media_player(for_video=False)
                cover_path = item.data(0, PLAYLIST_COVER_PNG_PATH_ROLE) or ""
                if not cover_path:
                    data = item.data(0, Qt.UserRole) or {}
                    cover_path = data.get("coverPngPath", "")
                if cover_path == self._last_cover_path:
                    return
                self._last_cover_path = cover_path
                logging.debug(f"Playlist click: coverPngPath={cover_path}")
                if cover_path:
                    if set_label_pixmap(self.main_window.ui.lblImg, cover_path) is False:
                        logging.error("Failed to load cover image: %s", cover_path)
                        self.main_window.ui.lblImg.setPixmap(QPixmap())
                        self.main_window.ui.lblImg.setText("")
                else:
                    logging.warning("coverPngPath is empty for playlist")
                    self.main_window.ui.lblImg.setPixmap(QPixmap())
                    self.main_window.ui.lblImg.setText("")
            else:
                self.main_window.ui.lblImg.setPixmap(QPixmap())
                self.main_window.ui.lblImg.setText("")
        except Exception as e:
            logging.exception(f"Error handling playlist click: {e}")

    def on_current_item_changed(self, current, previous):
        """Sync playlist cover when navigating with keyboard."""
        try:
            if current is None:
                return
            from PySide6.QtWidgets import QApplication
            if QApplication.mouseButtons() != Qt.NoButton:
                return
            self.on_item_clicked(current, 0)
        except Exception as e:
            logging.exception(f"Error handling playlist current item change: {e}")

    def _get_tree_selected_items(self):
        """Return selected items in treePlaylists, falling back to current item"""
        items = self.main_window.ui.treePlaylists.selectedItems() or []
        if not items:
            current = self.main_window.ui.treePlaylists.currentItem()
            if current:
                items = [current]
        return [item for item in items if item is not None]

    def _get_tree_root_items(self, items):
        """Remove items that are descendants of other selected items"""
        selected_set = set(items)
        root_items = []
        for item in items:
            parent = item.parent()
            skip = False
            while parent:
                if parent in selected_set:
                    skip = True
                    break
                parent = parent.parent()
            if not skip:
                root_items.append(item)
        return root_items

    def on_delete_clicked(self):
        """Delete selected item(s) from treePlaylists with confirmation"""
        try:
            items = self._get_tree_selected_items()
            if not items:
                QMessageBox.information(self.main_window, texts.TITLE_WARNING, texts.TREE_NO_SELECTION)
                return

            playlists_to_rebuild = self._get_playlist_parents_for_items(items)

            root_items = self._get_tree_root_items(items)

            has_complex = any(
                item.data(0, TREE_ITEM_TYPE_ROLE) in (TreeItemType.PLAYLIST.value, TreeItemType.SECTION.value)
                for item in root_items
            )

            if has_complex:
                msg = QMessageBox(self.main_window)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle(texts.TITLE_CONFIRMATION)
                msg.setText(texts.TREE_DELETE_CONFIRM)
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec() != QMessageBox.Yes:
                    return
            elif len(root_items) > 1:
                msg = QMessageBox(self.main_window)
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle(texts.TITLE_CONFIRMATION)
                msg.setText(texts.TREE_DELETE_CONFIRM_MULTI.format(count=len(root_items)))
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec() != QMessageBox.Yes:
                    return

            # Collect locale IDs and cover assets to delete (sections/playlists)
            locale_ids_to_delete = set()
            cover_pngs_to_delete = set()
            cover_assets_to_delete = set()
            sections_to_update = set()
            for item in root_items:
                item_type = item.data(0, TREE_ITEM_TYPE_ROLE)
                if item_type == TreeItemType.SECTION.value:
                    title_id = str(item.data(0, SECTION_TITLE_ID_ROLE) or "").strip()
                    if not title_id:
                        data = item.data(0, Qt.UserRole) or {}
                        title_id = str(data.get("titleId", "")).strip()
                    if title_id:
                        locale_ids_to_delete.add(title_id)
                    for i in range(item.childCount()):
                        child = item.child(i)
                        if not child or child.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.PLAYLIST.value:
                            continue
                        pdata = child.data(0, Qt.UserRole) or {}
                        tid = str(pdata.get("titleId", "")).strip()
                        did = str(pdata.get("descriptionId", "")).strip()
                        if tid:
                            locale_ids_to_delete.add(tid)
                        if did:
                            locale_ids_to_delete.add(did)
                        cover_path = str(child.data(0, PLAYLIST_COVER_PNG_PATH_ROLE) or "").strip()
                        if not cover_path:
                            cover_path = str(pdata.get("coverPngPath", "")).strip()
                        if cover_path:
                            cover_pngs_to_delete.add(cover_path)
                        cover_act_path = str(pdata.get("coverPath", "")).strip()
                        if cover_act_path:
                            cover_assets_to_delete.update(self.resolve_cover_asset_paths(cover_act_path))
                elif item_type == TreeItemType.PLAYLIST.value:
                    pdata = item.data(0, Qt.UserRole) or {}
                    tid = str(pdata.get("titleId", "")).strip()
                    did = str(pdata.get("descriptionId", "")).strip()
                    if tid:
                        locale_ids_to_delete.add(tid)
                    if did:
                        locale_ids_to_delete.add(did)
                    cover_path = str(item.data(0, PLAYLIST_COVER_PNG_PATH_ROLE) or "").strip()
                    if not cover_path:
                        cover_path = str(pdata.get("coverPngPath", "")).strip()
                    if cover_path:
                        cover_pngs_to_delete.add(cover_path)
                    cover_act_path = str(pdata.get("coverPath", "")).strip()
                    if cover_act_path:
                        cover_assets_to_delete.update(self.resolve_cover_asset_paths(cover_act_path))
                    parent = item.parent()
                    if parent and parent.data(0, TREE_ITEM_TYPE_ROLE) == TreeItemType.SECTION.value:
                        sections_to_update.add(parent)

            for item in root_items:
                parent = item.parent()
                if parent:
                    parent.takeChild(parent.indexOfChild(item))
                else:
                    index = self.main_window.ui.treePlaylists.indexOfTopLevelItem(item)
                    if index != -1:
                        self.main_window.ui.treePlaylists.takeTopLevelItem(index)

            for section_item in list(sections_to_update):
                self.update_section_requests(section_item)

            for playlist_item in playlists_to_rebuild:
                self._rebuild_playlist_songs(playlist_item)

            # Delete cover PNGs for removed playlists
            for cover_path in cover_pngs_to_delete:
                try:
                    from pathlib import Path
                    cover_file = Path(cover_path)
                    if cover_file.exists():
                        cover_file.unlink()
                except Exception as e:
                    logging.exception(f"Failed to delete cover PNG: {cover_path} | {e}")

            # Queue cover ACT/TGA assets for deletion on Save
            self.queue_cover_asset_deletions(cover_assets_to_delete)

            # Remove locale IDs from localisation.json and refresh tblLocales
            if locale_ids_to_delete and config.TEMP_LOCALISATION_JSON.exists():
                locales_dict = json.loads(
                    config.TEMP_LOCALISATION_JSON.read_text(encoding="utf-8")
                )
                for locale_id in locale_ids_to_delete:
                    locales_dict.pop(locale_id, None)
                config.TEMP_LOCALISATION_JSON.write_text(
                    json.dumps(locales_dict, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
                _, locales_items = self.main_window.data_service.load_locales_data()
                self.main_window.locales_controller.populate_locales(locales_items)

            # Update UI after deletion
            self.main_window.ui.treePlaylists.clearSelection()
            self.main_window.ui.lblImg.setPixmap(QPixmap())
            self.main_window.ui.lblImg.setText("")
            self.main_window.ui.treePlaylists.viewport().update()
            self.main_window.update_action_buttons()

            logging.info(f"Deleted {len(root_items)} item(s) from playlists tree")
        except Exception as e:
            logging.exception(f"Error deleting items from playlists tree: {e}")
            QMessageBox.critical(self.main_window, texts.TITLE_ERROR, texts.TREE_DELETE_ERROR.format(error=e))

    def _get_playlist_parents_for_items(self, items):
        playlists = set()
        for item in items:
            if item.data(0, TREE_ITEM_TYPE_ROLE) == TreeItemType.SONG.value:
                parent = item.parent()
                if parent and parent.data(0, TREE_ITEM_TYPE_ROLE) == TreeItemType.PLAYLIST.value:
                    playlists.add(parent)
        return playlists

    def _rebuild_playlist_songs(self, playlist_item):
        try:
            if not playlist_item:
                return
            if playlist_item.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.PLAYLIST.value:
                return
            songs_list = []
            for i in range(playlist_item.childCount()):
                child = playlist_item.child(i)
                if child.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.SONG.value:
                    continue
                song_code = child.data(0, SONG_CODE_ROLE)
                if song_code:
                    songs_list.append(str(song_code))
            pdata = playlist_item.data(0, Qt.UserRole) or {}
            pdata["maps"] = songs_list
            playlist_item.setData(0, Qt.UserRole, pdata)
        except Exception as e:
            logging.exception(f"Failed to rebuild playlist songs list: {e}")

    def resolve_cover_asset_paths(self, cover_path_str):
        """Resolve .act.ckd and .tga.ckd paths from a coverPath value."""
        paths = set()
        try:
            from pathlib import Path
            raw = Path(str(cover_path_str))
            name = raw.name
            if name.endswith(".act.ckd"):
                base = name[:-8]
            elif name.endswith(".act"):
                base = name[:-4]
            else:
                base = raw.stem

            if raw.is_absolute():
                base_dir = raw.parent
                paths.add(base_dir / f"{base}.act.ckd")
                paths.add(base_dir / f"{base}.tga.ckd")

            # Common extracted location
            paths.add(config.INPUT_COVERS_FOLDER / f"{base}.act.ckd")
            paths.add(config.INPUT_COVERS_FOLDER / f"{base}.tga.ckd")

            # If coverPath includes world/... relative path, map to extracted root
            if not raw.is_absolute() and str(raw.parent):
                candidate_dir = config.INPUT_PATCH_NX_FOLDER / "cache" / "itf_cooked" / "nx" / raw.parent
                paths.add(candidate_dir / f"{base}.act.ckd")
                paths.add(candidate_dir / f"{base}.tga.ckd")
        except Exception as e:
            logging.exception(f"Failed to resolve cover asset paths: {cover_path_str} | {e}")
        return paths

    def queue_cover_asset_deletions(self, asset_paths):
        """Queue cover assets for deletion on Save."""
        try:
            if not asset_paths:
                return
            for path in asset_paths:
                if path:
                    self.pending_cover_assets_to_delete.add(path)
        except Exception as e:
            logging.exception(f"Failed to queue cover asset deletions: {e}")

    def delete_pending_cover_assets(self):
        """Delete queued cover assets (called on Save)."""
        try:
            if not self.pending_cover_assets_to_delete:
                return
            logging.info(f"Deleting {len(self.pending_cover_assets_to_delete)} pending cover assets")
            for asset_path in list(self.pending_cover_assets_to_delete):
                try:
                    if asset_path and asset_path.exists():
                        asset_path.unlink()
                except Exception as e:
                    logging.exception(f"Failed to delete cover asset: {asset_path} | {e}")
            self.pending_cover_assets_to_delete.clear()
        except Exception as e:
            logging.exception(f"Failed to delete pending cover assets: {e}")
