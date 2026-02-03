import logging

from PySide6.QtCore import Qt, QEvent, QObject, QTimer
from PySide6.QtWidgets import QApplication, QAbstractItemView, QTreeWidgetItem, QMessageBox
from PySide6.QtGui import QFont, QTextCursor

from .constants import (
    TREE_ITEM_TYPE_ROLE,
    MISSING_SONG_CODE_ROLE,
    SONG_CODE_ROLE,
    PLAYLIST_ID_ROLE,
    PLAYLIST_TITLE_TEXT_ROLE,
    SECTION_TITLE_ROLE,
    TreeItemType,
)
from ..utils.utils import is_descendant_of
from ..shared import texts


class GlobalFocusEventFilter(QObject):
    """Global event filter that clears tblSongs selection when focus moves to another widget"""

    def __init__(self, tblSongs, safe_widgets=None):
        super().__init__()  # No parent for global filter
        self.tblSongs = tblSongs
        self.safe_widgets = safe_widgets or []

    def _is_safe(self, widget):
        """Check if widget is safe or a descendant of a safe widget"""
        return is_descendant_of(widget, self.safe_widgets)

    def eventFilter(self, obj, event):
        """Monitor FocusIn events - clear selection unless focus is in a safe widget"""
        if event.type() == QEvent.FocusIn:
            if obj != self.tblSongs and not self._is_safe(obj):
                try:
                    if self.tblSongs.selectedIndexes():
                        self.tblSongs.clearSelection()
                except Exception as e:
                    logging.exception(f"Error clearing tblSongs selection on focus change: {e}")
        return False  # Don't block the event


class FocusLossEventFilter(QObject):
    """Event filter that clears table selection when focus is lost, except to safe widgets"""

    def __init__(self, table_widget, safe_widgets=None):
        super().__init__(table_widget)
        self.table_widget = table_widget
        self.safe_widgets = safe_widgets or []

    def _is_safe(self, widget):
        """Check if widget is safe or a descendant of a safe widget"""
        return is_descendant_of(widget, self.safe_widgets)

    def eventFilter(self, obj, event):
        """Handle focus out events"""
        if event.type() == QEvent.FocusOut:
            try:
                next_focus = QApplication.focusWidget()
                # Only clear if next widget is NOT a safe widget and NOT tblSongs itself
                if next_focus not in self.safe_widgets and next_focus != self.table_widget:
                    # Also check if next_focus is a child of tblSongs (still part of the table)
                    is_table_child = False
                    w = next_focus
                    while w:
                        if w == self.table_widget:
                            is_table_child = True
                            break
                        w = w.parent()

                    if not is_table_child:
                        self.table_widget.clearSelection()
            except Exception as e:
                logging.exception(f"Error clearing tblSongs selection on focus loss: {e}")
        return False  # Allow other handlers to process the event


class TblSongsPlayColumnFilter(QObject):
    """Intercepts clicks on tblSongs play column to avoid row selection and trigger play."""

    def __init__(self, table_widget, play_callback):
        super().__init__(table_widget)
        self.table_widget = table_widget
        self.play_callback = play_callback
        self._pressed_row = None

    def eventFilter(self, obj, event):
        if obj != self.table_widget.viewport():
            return False

        try:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                index = self.table_widget.indexAt(event.pos())
                if index.isValid() and index.column() == 0:
                    self._pressed_row = index.row()
                    return False

            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                index = self.table_widget.indexAt(event.pos())
                if index.isValid() and index.column() == 0:
                    if self._pressed_row == index.row():
                        try:
                            self.play_callback(index.row())
                        except Exception as e:
                            logging.exception(f"Error handling play column click: {e}")
                    self._pressed_row = None
                    return False

            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                index = self.table_widget.indexAt(event.pos())
                if index.isValid() and index.column() == 0:
                    return False
        except Exception as e:
            logging.exception(f"Error in play column event filter: {e}")

        return False


class PlaylistsTreeDropFilter(QObject):
    """Validates drag/drop so items keep their hierarchy level"""

    def __init__(self, tree, tblSongs, playlists_tree_controller=None):
        super().__init__(tree)
        self.tree = tree
        self.tblSongs = tblSongs
        self.playlists_tree_controller = playlists_tree_controller

    def eventFilter(self, obj, event):
        if obj not in (self.tree, self.tree.viewport()):
            return False

        if event.type() == QEvent.Drop:
            if self._is_external_tblsongs_drop(event):
                if not self._handle_tblsongs_drop(event):
                    event.ignore()
                return True
            if not self._is_valid_drop(event):
                event.ignore()
                return True
            self._schedule_rebuild_for_internal_drop(event)
        return False

    def _has_selection(self):
        if self.tree.selectedItems():
            return True
        return self.tree.currentItem() is not None

    def _get_item_type(self, item):
        if not item:
            return None
        return item.data(0, TREE_ITEM_TYPE_ROLE)

    def _get_event_pos(self, event):
        try:
            return event.position().toPoint()
        except Exception as e:
            logging.exception(f"Failed to read drop event position: {e}")
            return event.pos()

    def _is_external_tblsongs_drop(self, event):
        try:
            return event.source() == self.tblSongs
        except Exception as e:
            logging.exception(f"Failed to inspect drop event source: {e}")
            return False

    def _get_tblsongs_selected_rows(self):
        selection = self.tblSongs.selectionModel()
        if not selection:
            return []
        rows = selection.selectedRows(1)  # column 1 has CodeName + UserRole
        if not rows:
            rows = selection.selectedRows(0)
        # Preserve visual order (top-to-bottom) regardless of click order
        return sorted({idx.row() for idx in rows})

    def _format_song_text(self, song_code, song_data):
        title = song_data.get("Title", "") if song_data else ""
        artist = song_data.get("Artist", "") if song_data else ""
        return f'{song_code} ("{title}" - {artist})'

    def _create_song_item(self, parent, song_code, song_data):
        item = QTreeWidgetItem(parent)
        item.setText(0, self._format_song_text(song_code, song_data))
        item.setData(0, SONG_CODE_ROLE, song_code)
        item.setData(0, Qt.UserRole, song_data or {})
        item.setData(0, TREE_ITEM_TYPE_ROLE, TreeItemType.SONG.value)
        song_font = QFont()
        song_font.setPointSize(10)
        item.setFont(0, song_font)
        item.setFlags((item.flags() | Qt.ItemIsDragEnabled) & ~Qt.ItemIsDropEnabled)
        return item

    def _handle_tblsongs_drop(self, event):
        pos = self._get_event_pos(event)
        target = self.tree.itemAt(pos)
        indicator = self.tree.dropIndicatorPosition()

        # Determine intended parent for songs
        if indicator == QAbstractItemView.OnItem:
            intended_parent = target
        elif indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
            intended_parent = target.parent() if target else None
        else:
            intended_parent = None

        if self._get_item_type(intended_parent) != TreeItemType.PLAYLIST.value:
            return False

        # Determine insert index when dropping above/below a song
        insert_index = -1
        if indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem) and target:
            if self._get_item_type(target) == TreeItemType.SONG.value:
                base_index = intended_parent.indexOfChild(target)
                insert_index = base_index + (1 if indicator == QAbstractItemView.BelowItem else 0)

        rows = self._get_tblsongs_selected_rows()
        if not rows:
            return False

        selected_songs = []
        for row in rows:
            code_item = self.tblSongs.item(row, 1)
            if not code_item:
                continue
            song_code = str(code_item.text())
            song_data = code_item.data(Qt.UserRole) or {}
            selected_songs.append((song_code, song_data))

        if not selected_songs:
            return False

        existing_codes = set()
        for i in range(intended_parent.childCount()):
            child = intended_parent.child(i)
            if child and child.data(0, TREE_ITEM_TYPE_ROLE) == TreeItemType.SONG.value:
                existing_codes.add(str(child.data(0, SONG_CODE_ROLE) or ""))

        duplicates = [code for code, _ in selected_songs if code in existing_codes]
        if duplicates:
            msg = QMessageBox(self.tree)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle(texts.SONGS_DUPLICATE_TITLE)
            msg.setText(texts.SONGS_DUPLICATE_TEXT.format(
                duplicates=len(duplicates),
                total=len(selected_songs),
            ))
            btn_add_all = msg.addButton(texts.SONGS_DUPLICATE_ADD_ALL, QMessageBox.AcceptRole)
            btn_add_unique = msg.addButton(texts.SONGS_DUPLICATE_ADD_UNIQUE, QMessageBox.ActionRole)
            btn_add_none = msg.addButton(texts.SONGS_DUPLICATE_ADD_NONE, QMessageBox.RejectRole)
            msg.setDefaultButton(btn_add_unique)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_add_none:
                return False
            if clicked == btn_add_unique:
                selected_songs = [(code, data) for code, data in selected_songs if code not in existing_codes]
                if not selected_songs:
                    return False

        # Insert songs in order
        offset = 0
        for song_code, song_data in selected_songs:
            new_item = self._create_song_item(intended_parent, song_code, song_data)
            if insert_index != -1:
                intended_parent.takeChild(intended_parent.indexOfChild(new_item))
                intended_parent.insertChild(insert_index + offset, new_item)
                offset += 1

        event.setDropAction(Qt.CopyAction)
        event.accept()
        self._rebuild_playlist_songs(intended_parent)
        return True

    def _schedule_rebuild_for_internal_drop(self, event):
        try:
            selected = self.tree.selectedItems()
            if not selected:
                current = self.tree.currentItem()
                selected = [current] if current else []
            if not selected:
                return

            src_type = self._get_item_type(selected[0])
            if src_type == TreeItemType.SONG.value:
                old_parents = {item.parent() for item in selected if item.parent()}
                intended_parent = self._get_intended_parent(event)
                if intended_parent:
                    old_parents.add(intended_parent)

                def _do_rebuild_songs():
                    for parent in list(old_parents):
                        self._rebuild_playlist_songs(parent)

                QTimer.singleShot(0, _do_rebuild_songs)
                return

            if src_type == TreeItemType.PLAYLIST.value:
                old_sections = {item.parent() for item in selected if item.parent()}
                intended_parent = self._get_intended_parent(event)
                if intended_parent:
                    old_sections.add(intended_parent)

                def _do_rebuild_requests():
                    for section_item in list(old_sections):
                        self._rebuild_section_requests(section_item)

                QTimer.singleShot(0, _do_rebuild_requests)
        except Exception as e:
            logging.exception(f"Failed to schedule playlist songs rebuild: {e}")

    def _rebuild_section_requests(self, section_item):
        try:
            if not section_item:
                return
            if self._get_item_type(section_item) != TreeItemType.SECTION.value:
                return

            if self.playlists_tree_controller:
                self.playlists_tree_controller.update_section_requests(section_item)
                return

            requests = []
            for i in range(section_item.childCount()):
                playlist_item = section_item.child(i)
                if self._get_item_type(playlist_item) != TreeItemType.PLAYLIST.value:
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

            data = section_item.data(0, Qt.UserRole) or {}
            data = {
                "__class": "CategoryRule",
                "act": "ui_carousel",
                "isc": "grp_row",
                "title": section_item.data(0, SECTION_TITLE_ROLE) or section_item.text(0),
                "titleId": section_item.data(0, SECTION_TITLE_ID_ROLE) or data.get("titleId", ""),
                "requests": requests,
            }
            section_item.setData(0, Qt.UserRole, data)
        except Exception as e:
            logging.exception(f"Failed to rebuild section requests list: {e}")

    def _get_intended_parent(self, event):
        pos = self._get_event_pos(event)
        target = self.tree.itemAt(pos)
        indicator = self.tree.dropIndicatorPosition()

        if indicator == QAbstractItemView.OnItem:
            return target
        if indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
            return target.parent() if target else None
        return None

    def _rebuild_playlist_songs(self, playlist_item):
        try:
            if not playlist_item:
                return
            if self._get_item_type(playlist_item) != TreeItemType.PLAYLIST.value:
                return

            songs_list = []
            for i in range(playlist_item.childCount()):
                child = playlist_item.child(i)
                if self._get_item_type(child) != TreeItemType.SONG.value:
                    continue
                song_code = child.data(0, SONG_CODE_ROLE)
                if song_code:
                    songs_list.append(str(song_code))

            pdata = playlist_item.data(0, Qt.UserRole) or {}
            pdata["maps"] = songs_list
            playlist_item.setData(0, Qt.UserRole, pdata)
        except Exception as e:
            logging.exception(f"Failed to rebuild playlist songs list: {e}")

    def _is_valid_drop(self, event):
        pos = self._get_event_pos(event)
        target = self.tree.itemAt(pos)
        indicator = self.tree.dropIndicatorPosition()

        selected = self.tree.selectedItems()
        if not selected:
            current = self.tree.currentItem()
            selected = [current] if current else []
        if not selected:
            return False

        # Ensure all selected items are the same type
        src_type = self._get_item_type(selected[0])
        if not src_type or any(self._get_item_type(it) != src_type for it in selected):
            return False

        # Ensure all selected items share the same parent (multi-drag must be same group)
        parents = {item.parent() for item in selected}
        if len(parents) > 1:
            return False

        tgt_type = self._get_item_type(target)

        # Determine intended parent based on drop indicator
        if indicator == QAbstractItemView.OnItem:
            intended_parent = target
        elif indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
            intended_parent = target.parent() if target else None
        elif indicator == QAbstractItemView.OnViewport:
            intended_parent = None
        else:
            intended_parent = None

        intended_parent_type = self._get_item_type(intended_parent)

        # Enforce parent type by hierarchy
        if src_type == TreeItemType.SECTION.value:
            if intended_parent is not None:
                return False
        elif src_type == TreeItemType.PLAYLIST.value:
            if intended_parent_type != TreeItemType.SECTION.value:
                return False
        elif src_type == TreeItemType.SONG.value:
            if intended_parent_type != TreeItemType.PLAYLIST.value:
                return False
        else:
            return False

        # If dropping above/below, ensure same-level reorder
        if indicator in (QAbstractItemView.AboveItem, QAbstractItemView.BelowItem):
            return tgt_type == src_type

        # OnItem is allowed only for valid parent types above
        if indicator == QAbstractItemView.OnItem:
            return True

        # OnViewport only valid for sections at top level
        if indicator == QAbstractItemView.OnViewport:
            return src_type == TreeItemType.SECTION.value

        return False


class TreeToSearchDropFilter(QObject):
    """Enable drag/drop from treePlaylists into search fields."""

    def __init__(self, tree, target_widget, mode):
        super().__init__(target_widget)
        self.tree = tree
        self.target_widget = target_widget
        self.mode = mode  # "song", "titleId", or "playlistSearch"

    def eventFilter(self, obj, event):
        if obj != self.target_widget and obj != getattr(self.target_widget, "viewport", lambda: None)():
            return False

        if event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if not self._is_tree_source(event):
                return False
            if self._is_valid_source_item(event):
                action = Qt.CopyAction if (event.possibleActions() & Qt.CopyAction) else event.proposedAction()
                event.setDropAction(action)
                event.accept()
                return True
            event.ignore()
            return True

        if event.type() == QEvent.Drop:
            if not self._is_tree_source(event):
                return False
            if not self._is_valid_source_item(event):
                event.ignore()
                return True

            item = self._get_selected_item()
            if not item:
                event.ignore()
                return True

            value = self._extract_value(item)
            if value is None:
                event.ignore()
                return True

            try:
                self.target_widget.setPlainText(str(value))
                self.target_widget.moveCursor(QTextCursor.End)
                self.target_widget.setFocus()
                action = Qt.CopyAction if (event.possibleActions() & Qt.CopyAction) else event.proposedAction()
                event.setDropAction(action)
                event.accept()
            except Exception as e:
                logging.exception(f"Failed to handle drop into search field: {e}")
            return True

        return False

    def _is_tree_source(self, event):
        try:
            src = event.source()
            if src in (self.tree, getattr(self.tree, "viewport", lambda: None)()):
                return True
            if src is None:
                return self.tree is not None and (self.tree.selectedItems() or self.tree.currentItem())
        except Exception:
            return False
        return False

    def _get_selected_item(self):
        items = self.tree.selectedItems() or []
        if not items:
            return self.tree.currentItem()
        return items[0]

    def _get_item_type(self, item):
        if not item:
            return None
        return item.data(0, TREE_ITEM_TYPE_ROLE)

    def _is_valid_source_item(self, event):
        try:
            src = event.source()
            if src not in (self.tree, getattr(self.tree, "viewport", lambda: None)()) and src is not None:
                return False
        except Exception:
            return False

        item = self._get_selected_item()
        item_type = self._get_item_type(item)
        if self.mode == "song":
            return item_type == TreeItemType.SONG.value
        if self.mode == "titleId":
            return item_type in (TreeItemType.SECTION.value, TreeItemType.PLAYLIST.value)
        if self.mode == "playlistSearch":
            return item_type in (TreeItemType.SECTION.value, TreeItemType.PLAYLIST.value, TreeItemType.SONG.value)
        return False

    def _extract_value(self, item):
        item_type = self._get_item_type(item)
        if self.mode == "song":
            if item_type != TreeItemType.SONG.value:
                return None
            code = item.data(0, SONG_CODE_ROLE)
            if code:
                return code
            missing_code = item.data(0, MISSING_SONG_CODE_ROLE)
            if missing_code:
                return missing_code
            text = item.text(0) or ""
            return text.split(":", 1)[0].strip()

        if self.mode == "titleId":
            if item_type not in (TreeItemType.SECTION.value, TreeItemType.PLAYLIST.value):
                return None
            title_text = None
            if item_type == TreeItemType.SECTION.value:
                title_text = item.data(0, SECTION_TITLE_ROLE)
            if title_text is None and item_type == TreeItemType.PLAYLIST.value:
                title_text = item.data(0, PLAYLIST_TITLE_TEXT_ROLE)
            if title_text is None:
                data = item.data(0, Qt.UserRole) or {}
                title_text = data.get("titleText") or data.get("title")
            return title_text if title_text is not None else ""

        if self.mode == "playlistSearch":
            if item_type == TreeItemType.SONG.value:
                code = item.data(0, SONG_CODE_ROLE)
                if code:
                    return code
                missing_code = item.data(0, MISSING_SONG_CODE_ROLE)
                if missing_code:
                    return missing_code
                text = item.text(0) or ""
                return text.split(":", 1)[0].strip()

            if item_type == TreeItemType.SECTION.value:
                title_text = item.data(0, SECTION_TITLE_ROLE)
                if title_text is None:
                    data = item.data(0, Qt.UserRole) or {}
                    title_text = data.get("title")
                return title_text if title_text is not None else (item.text(0) or "")

            if item_type == TreeItemType.PLAYLIST.value:
                title_text = item.data(0, PLAYLIST_TITLE_TEXT_ROLE)
                if title_text is None:
                    data = item.data(0, Qt.UserRole) or {}
                    title_text = data.get("titleText")
                return title_text if title_text is not None else (item.text(0) or "")

        return None


class TblSongsToSearchDropFilter(QObject):
    """Enable drag/drop from tblSongs into search fields."""

    def __init__(self, table, target_widget):
        super().__init__(target_widget)
        self.table = table
        self.target_widget = target_widget

    def eventFilter(self, obj, event):
        if obj != self.target_widget and obj != getattr(self.target_widget, "viewport", lambda: None)():
            return False

        if event.type() in (QEvent.DragEnter, QEvent.DragMove):
            if not self._is_valid_source(event):
                return False
            action = Qt.CopyAction if (event.possibleActions() & Qt.CopyAction) else event.proposedAction()
            event.setDropAction(action)
            event.accept()
            return True

        if event.type() == QEvent.Drop:
            if not self._is_valid_source(event):
                return False

            value = self._get_selected_song_code()
            if value is None:
                return False

            try:
                self.target_widget.setPlainText(str(value))
                self.target_widget.moveCursor(QTextCursor.End)
                self.target_widget.setFocus()
                action = Qt.CopyAction if (event.possibleActions() & Qt.CopyAction) else event.proposedAction()
                event.setDropAction(action)
                event.accept()
            except Exception as e:
                logging.exception(f"Failed to handle tblSongs drop into search field: {e}")
            return True

        return False

    def _is_valid_source(self, event):
        try:
            if event.source() != self.table:
                return False
        except Exception:
            return False
        return self._get_selected_song_code() is not None

    def _get_selected_song_code(self):
        try:
            selection = self.table.selectionModel()
            if not selection:
                return None
            rows = selection.selectedRows(1)
            if not rows:
                rows = selection.selectedRows(0)
            if not rows:
                return None
            row = rows[0].row()
            item = self.table.item(row, 1) or self.table.item(row, 0)
            if item:
                return item.text().strip()
        except Exception as e:
            logging.exception(f"Failed to read selected tblSongs row for drop: {e}")
        return None


class NoNewlineFilter(QObject):
    """Prevent newline/return in text inputs."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                event.ignore()
                return True
        return False
