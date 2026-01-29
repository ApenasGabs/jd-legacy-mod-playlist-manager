import json
import logging
import re
import shutil

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QFont, QBrush, QColor, QImage, QPixmap, QRegularExpressionValidator
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem, QFileDialog

from ... import config
from ...utils.utils import adjust_name_17
from ..shared.constants import (
    TREE_ITEM_TYPE_ROLE,
    PLAYLIST_ID_ROLE,
    PLAYLIST_TITLE_TEXT_ROLE,
    PLAYLIST_DESCRIPTION_TEXT_ROLE,
    PLAYLIST_COVER_PNG_PATH_ROLE,
    TreeItemType,
)
from ..utils.utils import set_label_pixmap
from ..shared import texts


class PlaylistWindowController:
    """UI logic for playlistWindow.ui."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.playlist_window = None

    def open(self, mode="create", item=None):
        """Open the Playlist window in create or edit mode."""
        try:
            # Close section window if open (no save)
            if getattr(self.main_window, "section_window", None):
                try:
                    self.main_window.section_window.close()
                except Exception:
                    pass

            loader = QUiLoader()
            ui_path = str(config.GUI_DIR / "playlistWindow.ui")
            self.playlist_window = loader.load(ui_path, None)
            if not self.playlist_window:
                QMessageBox.critical(self.main_window, texts.TITLE_ERROR, texts.PLAYLIST_WINDOW_LOAD_UI_ERROR.format(path=ui_path))
                return

            # Lock window size and remove minimize/maximize
            self.playlist_window.setWindowFlags(
                Qt.Window | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint
            )
            self.playlist_window.setWindowModality(Qt.ApplicationModal)
            self.playlist_window.setFixedSize(self.playlist_window.size())

            # Track mode and item
            self.playlist_window._mode = mode
            self.playlist_window._tree_item = item

            # Default cover setup
            default_cover = (config.ASSETS_DIR / "default_cover.png").resolve()
            self.playlist_window._default_cover_path = str(default_cover)

            # Reset fields
            if hasattr(self.playlist_window, "txtPlaylistId"):
                self.playlist_window.txtPlaylistId.setText("")
                try:
                    self.playlist_window.txtPlaylistId.setMaxLength(17)
                    self.playlist_window.txtPlaylistId.setValidator(
                        QRegularExpressionValidator(QRegularExpression(r"[A-Za-z0-9]{0,17}"))
                    )
                except Exception:
                    pass
            if hasattr(self.playlist_window, "txtPlaylistTitleText"):
                self.playlist_window.txtPlaylistTitleText.setText("")
            if hasattr(self.playlist_window, "txtPlaylistDescriptionText"):
                self.playlist_window.txtPlaylistDescriptionText.setText("")
            if hasattr(self.playlist_window, "txtPlaylistTitleId"):
                self.playlist_window.txtPlaylistTitleId.setText("")
            if hasattr(self.playlist_window, "txtPlaylistDescriptionId"):
                self.playlist_window.txtPlaylistDescriptionId.setText("")
            if hasattr(self.playlist_window, "txtPlaylistPNGCoverPath"):
                self.playlist_window.txtPlaylistPNGCoverPath.setText(self.playlist_window._default_cover_path)

            # Default preview only for create mode
            if mode != "edit":
                self.set_cover_preview(self.playlist_window._default_cover_path)

            # Edit mode setup
            if mode == "edit" and item is not None:
                pdata = item.data(0, Qt.UserRole) or {}
                playlist_id = item.data(0, PLAYLIST_ID_ROLE) or pdata.get("playlistID", "")
                title_text = item.data(0, PLAYLIST_TITLE_TEXT_ROLE) or pdata.get("titleText", "")
                description_text = item.data(0, PLAYLIST_DESCRIPTION_TEXT_ROLE) or pdata.get("descriptionText", "")
                cover_path = str(item.data(0, PLAYLIST_COVER_PNG_PATH_ROLE) or pdata.get("coverPngPath", "")).strip()
                if hasattr(self.playlist_window, "lblPlaylistTitle"):
                    self.playlist_window.lblPlaylistTitle.setText(texts.PLAYLIST_TITLE_EDIT)
                if hasattr(self.playlist_window, "lblSectionLocaleInfo"):
                    self.playlist_window.lblSectionLocaleInfo.setVisible(False)
                if hasattr(self.playlist_window, "txtPlaylistId"):
                    self.playlist_window.txtPlaylistId.setText(str(playlist_id))
                if hasattr(self.playlist_window, "txtPlaylistTitleText"):
                    self.playlist_window.txtPlaylistTitleText.setText(str(title_text))
                if hasattr(self.playlist_window, "txtPlaylistDescriptionText"):
                    self.playlist_window.txtPlaylistDescriptionText.setText(str(description_text))
                if hasattr(self.playlist_window, "txtPlaylistTitleId"):
                    self.playlist_window.txtPlaylistTitleId.setText(str(pdata.get("titleId", "")))
                if hasattr(self.playlist_window, "txtPlaylistDescriptionId"):
                    self.playlist_window.txtPlaylistDescriptionId.setText(str(pdata.get("descriptionId", "")))
                cover_path = cover_path or self.playlist_window._default_cover_path
                if hasattr(self.playlist_window, "txtPlaylistPNGCoverPath"):
                    self.playlist_window.txtPlaylistPNGCoverPath.setText(cover_path)
                self.set_cover_preview(cover_path)
            else:
                if hasattr(self.playlist_window, "lblPlaylistTitle"):
                    self.playlist_window.lblPlaylistTitle.setText(texts.PLAYLIST_TITLE_NEW)
                if hasattr(self.playlist_window, "lblSectionLocaleInfo"):
                    self.playlist_window.lblSectionLocaleInfo.setVisible(True)

            # Button handlers
            if hasattr(self.playlist_window, "btnPlaylistChangeCover"):
                self.playlist_window.btnPlaylistChangeCover.clicked.connect(self.on_change_cover)
            if hasattr(self.playlist_window, "btnPlaylistLoadDefaultCover"):
                self.playlist_window.btnPlaylistLoadDefaultCover.clicked.connect(self.on_load_default_cover)
            if hasattr(self.playlist_window, "btnPlaylistSave"):
                self.playlist_window.btnPlaylistSave.clicked.connect(self.on_save)

            # Show window
            self.playlist_window.show()
            self.playlist_window.raise_()
            self.playlist_window.activateWindow()
            try:
                from PySide6.QtCore import QTimer
                if mode != "edit":
                    QTimer.singleShot(0, lambda: self.set_cover_preview(self.playlist_window._default_cover_path))
            except Exception:
                pass

            # Expose to main window for focus checks
            self.main_window.playlist_window = self.playlist_window
        except Exception as e:
            logging.exception(f"Error opening playlist window: {e}")
            QMessageBox.critical(self.main_window, texts.TITLE_ERROR, texts.PLAYLIST_WINDOW_OPEN_ERROR.format(error=e))

    def set_cover_preview(self, path):
        try:
            if not self.playlist_window or not hasattr(self.playlist_window, "lblPlaylistCover"):
                return
            label = self.playlist_window.lblPlaylistCover
            if label.width() <= 0 or label.height() <= 0:
                label.resize(label.geometry().size())
            set_label_pixmap(label, path)
        except Exception as e:
            logging.exception(f"Error setting playlist cover preview: {e}")

    def on_load_default_cover(self):
        try:
            if not self.playlist_window:
                return
            default_path = self.playlist_window._default_cover_path
            if hasattr(self.playlist_window, "txtPlaylistPNGCoverPath"):
                self.playlist_window.txtPlaylistPNGCoverPath.setText(default_path)
            self.set_cover_preview(default_path)
        except Exception as e:
            logging.exception(f"Error loading default cover: {e}")

    def on_change_cover(self):
        try:
            if not self.playlist_window:
                return

            while True:
                file_path, _ = QFileDialog.getOpenFileName(
                    self.playlist_window,
                    texts.PLAYLIST_SELECT_COVER_TITLE,
                    "",
                    texts.PLAYLIST_SELECT_COVER_FILTER
                )
                if not file_path:
                    return

                image = QImage(file_path)
                if image.isNull():
                    try:
                        from PIL import Image
                        with Image.open(file_path) as pil_img:
                            width, height = pil_img.size
                    except Exception:
                        QMessageBox.warning(
                            self.playlist_window,
                            texts.PLAYLIST_INVALID_IMAGE_TITLE,
                            texts.PLAYLIST_INVALID_IMAGE_TEXT
                        )
                        continue
                else:
                    width, height = image.width(), image.height()

                if width != 1024 or height != 512:
                    QMessageBox.warning(
                        self.playlist_window,
                        texts.PLAYLIST_INVALID_IMAGE_TITLE,
                        texts.PLAYLIST_INVALID_SIZE
                    )
                    continue

                if hasattr(self.playlist_window, "txtPlaylistPNGCoverPath"):
                    self.playlist_window.txtPlaylistPNGCoverPath.setText(file_path)
                self.set_cover_preview(file_path)
                return
        except Exception as e:
            logging.exception(f"Error selecting playlist cover: {e}")
            QMessageBox.critical(self.playlist_window, texts.TITLE_ERROR, texts.PLAYLIST_ERROR_SELECT_COVER.format(error=e))

    def _get_target_section_item(self):
        """Return the section item based on current tree selection."""
        item = self.main_window.ui.treePlaylists.currentItem()
        if not item:
            return None
        item_type = item.data(0, TREE_ITEM_TYPE_ROLE)
        if item_type == TreeItemType.SECTION.value:
            return item
        if item_type == TreeItemType.PLAYLIST.value:
            return item.parent()
        if item_type == TreeItemType.SONG.value:
            parent = item.parent()
            return parent.parent() if parent else None
        return None

    def on_save(self):
        """Create a new playlist from the Playlist window."""
        try:
            if not self.playlist_window:
                return

            playlist_id = ""
            if hasattr(self.playlist_window, "txtPlaylistId"):
                playlist_id = self.playlist_window.txtPlaylistId.text().strip()

            if not re.fullmatch(r"[A-Za-z0-9]{1,17}", playlist_id or ""):
                QMessageBox.warning(
                    self.playlist_window,
                    texts.TITLE_WARNING,
                    texts.PLAYLIST_INVALID_ID,
                )
                return

            title_text = ""
            desc_text = ""
            if hasattr(self.playlist_window, "txtPlaylistTitleText"):
                title_text = self.playlist_window.txtPlaylistTitleText.text().strip()
            if hasattr(self.playlist_window, "txtPlaylistDescriptionText"):
                desc_text = self.playlist_window.txtPlaylistDescriptionText.text().strip()

            if not title_text or not desc_text:
                QMessageBox.warning(
                    self.playlist_window,
                    texts.TITLE_WARNING,
                    texts.PLAYLIST_INVALID_TEXT,
                )
                return

            cover_path = ""
            if hasattr(self.playlist_window, "txtPlaylistPNGCoverPath"):
                cover_path = self.playlist_window.txtPlaylistPNGCoverPath.text().strip()

            if not cover_path:
                QMessageBox.warning(
                    self.playlist_window,
                    texts.TITLE_WARNING,
                    texts.PLAYLIST_INVALID_COVER,
                )
                return

            # Validate cover size before any writes
            try:
                image = QImage(cover_path)
                if image.isNull():
                    try:
                        from PIL import Image
                        with Image.open(cover_path) as pil_img:
                            width, height = pil_img.size
                    except Exception:
                        QMessageBox.warning(
                            self.playlist_window,
                            texts.TITLE_WARNING,
                            texts.PLAYLIST_INVALID_IMAGE,
                        )
                        return
                else:
                    width, height = image.width(), image.height()

                if width != 1024 or height != 512:
                    QMessageBox.warning(
                        self.playlist_window,
                        texts.TITLE_WARNING,
                        texts.PLAYLIST_INVALID_SIZE,
                    )
                    return
            except Exception as e:
                logging.exception(f"Error validating cover: {e}")
                QMessageBox.critical(self.playlist_window, texts.TITLE_ERROR, texts.PLAYLIST_ERROR_VALIDATE_COVER.format(error=e))
                return

            mode = getattr(self.playlist_window, "_mode", "create")
            if mode != "edit":
                section_item = self._get_target_section_item()
                if not section_item or section_item.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.SECTION.value:
                    QMessageBox.warning(
                        self.playlist_window,
                        texts.TITLE_WARNING,
                        texts.PLAYLIST_NO_SECTION,
                    )
                    return

            if not config.TEMP_LOCALISATION_JSON.exists():
                QMessageBox.critical(
                    self.playlist_window,
                    texts.TITLE_ERROR,
                    texts.PLAYLIST_LOCALISATION_MISSING
                )
                return

            locales_dict = json.loads(
                config.TEMP_LOCALISATION_JSON.read_text(encoding="utf-8")
            )

            # Copy cover to temp/playlists_covers using adjusted 17-char lowercase name
            cover_act_path = ""
            try:
                from pathlib import Path
                src_cover = Path(cover_path)
                if not src_cover.exists():
                    QMessageBox.warning(
                        self.playlist_window,
                        texts.TITLE_WARNING,
                        texts.PLAYLIST_COVER_FILE_NOT_FOUND
                    )
                    return

                safe_name = adjust_name_17(playlist_id.lower())
                dest_cover = config.TEMP_PLAYLISTS_COVERS / f"{safe_name}.png"
                dest_cover.parent.mkdir(parents=True, exist_ok=True)
                # If editing, remove old cover when it differs
                mode = getattr(self.playlist_window, "_mode", "create")
                if mode == "edit":
                    playlist_item = getattr(self.playlist_window, "_tree_item", None)
                    if playlist_item is not None:
                        old_cover = playlist_item.data(0, PLAYLIST_COVER_PNG_PATH_ROLE) or (playlist_item.data(0, Qt.UserRole) or {}).get("coverPngPath", "")
                        try:
                            old_path = Path(str(old_cover))
                            if old_path.exists() and old_path.resolve() != dest_cover.resolve():
                                # If source is the old cover, copy first, then delete old
                                if src_cover.resolve() == old_path.resolve():
                                    shutil.copy2(src_cover, dest_cover)
                                    src_cover = dest_cover
                                old_path.unlink()
                        except Exception as e:
                            logging.exception(f"Failed to delete old cover PNG: {old_cover} | {e}")
                if src_cover.resolve() != dest_cover.resolve():
                    shutil.copy2(src_cover, dest_cover)
                cover_path = str(dest_cover)
                cover_act_path = f"world/ui/textures/covers/playlists_offline/{safe_name}.act"
            except Exception as e:
                logging.exception(f"Error copying playlist cover: {e}")
                QMessageBox.critical(self.playlist_window, texts.TITLE_ERROR, texts.PLAYLIST_ERROR_COPY_COVER.format(error=e))
                return

            if mode == "edit":
                title_id = ""
                desc_id = ""
                if hasattr(self.playlist_window, "txtPlaylistTitleId"):
                    title_id = self.playlist_window.txtPlaylistTitleId.text().strip()
                if hasattr(self.playlist_window, "txtPlaylistDescriptionId"):
                    desc_id = self.playlist_window.txtPlaylistDescriptionId.text().strip()
                if not title_id or not desc_id:
                    QMessageBox.warning(
                        self.playlist_window,
                        texts.TITLE_WARNING,
                        texts.PLAYLIST_TITLE_DESC_ID_MISSING
                    )
                    return

                locales_dict[title_id] = title_text
                locales_dict[desc_id] = desc_text
            else:
                # Determine target section (already validated above)
                section_item = self._get_target_section_item()

                numeric_ids = []
                for key in locales_dict.keys():
                    try:
                        numeric_ids.append(int(str(key)))
                    except (ValueError, TypeError):
                        continue

                next_id = (max(numeric_ids) + 1) if numeric_ids else 1
                title_id = str(next_id)
                desc_id = str(next_id + 1)
                locales_dict[title_id] = title_text
                locales_dict[desc_id] = desc_text

            config.TEMP_LOCALISATION_JSON.write_text(
                json.dumps(locales_dict, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            # Reload locales table in default order (last item appears first)
            _, locales_items = self.main_window.data_service.load_locales_data()
            self.main_window.locales_controller.populate_locales(locales_items)

            # Filter locales by titleId
            self.main_window.ui.txtSearchLocales.setPlainText(title_id)

            if mode == "edit":
                playlist_item = getattr(self.playlist_window, "_tree_item", None)
                if playlist_item is None:
                    return
                section_item = playlist_item.parent()
                existing = playlist_item.data(0, Qt.UserRole) or {}
                maps_list = existing.get("maps", existing.get("songs", []))
                playlist_data = {
                    "__class": existing.get("__class", "OfflinePlaylist"),
                    "titleId": title_id,
                    "descriptionId": desc_id,
                    "coverPath": cover_act_path or existing.get("coverPath", ""),
                    "maps": list(maps_list or []),
                }
                playlist_item.setData(0, PLAYLIST_ID_ROLE, playlist_id)
                playlist_item.setData(0, PLAYLIST_TITLE_TEXT_ROLE, title_text)
                playlist_item.setData(0, PLAYLIST_DESCRIPTION_TEXT_ROLE, desc_text)
                playlist_item.setData(0, PLAYLIST_COVER_PNG_PATH_ROLE, cover_path)
                playlist_item.setText(0, f'{playlist_id}: "{title_text} - {desc_text}"')
                playlist_item.setData(0, Qt.UserRole, playlist_data)
                if section_item and hasattr(self.main_window, "playlists_tree_controller"):
                    self.main_window.playlists_tree_controller.update_section_requests(section_item)
                self.main_window.ui.treePlaylists.setCurrentItem(playlist_item)
                self.main_window.ui.treePlaylists.scrollToItem(playlist_item)
                self.main_window.ui.treePlaylists.setFocus()
                # Refresh main cover preview if still selected
                self.main_window.playlists_tree_controller.on_item_clicked(playlist_item, 0)
            else:
                playlist_data = {
                    "__class": "OfflinePlaylist",
                    "titleId": title_id,
                    "descriptionId": desc_id,
                    "coverPath": cover_act_path,
                    "maps": []
                }

                playlist_item = QTreeWidgetItem(section_item)
                playlist_item.setText(0, f'{playlist_id}: "{title_text} - {desc_text}"')
                playlist_item.setData(0, PLAYLIST_ID_ROLE, playlist_id)
                playlist_item.setData(0, PLAYLIST_TITLE_TEXT_ROLE, title_text)
                playlist_item.setData(0, PLAYLIST_DESCRIPTION_TEXT_ROLE, desc_text)
                playlist_item.setData(0, PLAYLIST_COVER_PNG_PATH_ROLE, cover_path)
                playlist_item.setData(0, Qt.UserRole, playlist_data)
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

                section_item.setExpanded(True)
                self.main_window.ui.treePlaylists.setCurrentItem(playlist_item)
                self.main_window.ui.treePlaylists.scrollToItem(playlist_item)
                self.main_window.ui.treePlaylists.setFocus()

                if hasattr(self.main_window, "playlists_tree_controller"):
                    self.main_window.playlists_tree_controller.update_section_requests(section_item)

                if hasattr(self.playlist_window, "txtPlaylistTitleId"):
                    self.playlist_window.txtPlaylistTitleId.setText(title_id)
                if hasattr(self.playlist_window, "txtPlaylistDescriptionId"):
                    self.playlist_window.txtPlaylistDescriptionId.setText(desc_id)

            self.playlist_window.close()
        except Exception as e:
            logging.exception(f"Error saving playlist: {e}")
            QMessageBox.critical(self.playlist_window, texts.TITLE_ERROR, texts.PLAYLIST_ERROR_SAVE.format(error=e))
