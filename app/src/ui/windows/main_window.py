import sys
from ... import config
import logging
from PySide6.QtWidgets import QMainWindow, QApplication, QMessageBox, QAbstractItemView, QHeaderView, QVBoxLayout, QDialog, QPlainTextEdit, QDialogButtonBox, QLineEdit, QTextEdit, QComboBox
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QFont, QPixmap, QIcon, QShortcut
from collections import OrderedDict
from ..shared.constants import (
    TREE_ITEM_TYPE_ROLE,
    MISSING_SONG_MESSAGE_ROLE,
    MISSING_SONG_CODE_ROLE,
    SONG_CODE_ROLE,
    PLAYLIST_ID_ROLE,
    PLAYLIST_DESCRIPTION_TEXT_ROLE,
    PLAYLIST_COVER_PNG_PATH_ROLE,
    PLAYLIST_TITLE_TEXT_ROLE,
    TreeItemType,
)
from ..shared import texts
from ..shared.dialogs import show_info, show_warning, show_error
from ..shared.delegates import MultiLineDelegate
from ..shared.filters import (
    GlobalFocusEventFilter,
    FocusLossEventFilter,
    TblSongsPlayColumnFilter,
    PlaylistsTreeDropFilter,
    TreeToSearchDropFilter,
    NoNewlineFilter,
)
from ..controllers.playlists_tree_controller import PlaylistsTreeController
from .section_window import SectionWindowController
from .playlist_window import PlaylistWindowController
from ..controllers.save_controller import SaveController
from ..controllers.media_controller import MediaController
from ..controllers.volume_controller import VolumeController
from ..controllers.songs_table_controller import SongsTableController
from ..controllers.locales_controller import LocalesController
from ..controllers.load_controller import LoadController
from ...services.data_service import DataService


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # REMOVE MINIMIZE AND MAXIMIZE (Keep only Close)
        # Qt.CustomizeWindowHint allows us to customize native buttons
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint)

        # Initial directory configuration
        config.setup_directories()

        # Load Interface (just loads, doesn't process data yet)
        loader = QUiLoader()
        ui_path = str(config.GUI_DIR / "mainWindow.ui")
        import os
        print("DEBUG: ui_path =", ui_path)
        print("DEBUG: exists =", os.path.exists(ui_path))
        self.ui = loader.load(ui_path, None)

        if not self.ui:
            logging.error("Critical Error: UI file [%s] could not be loaded.", ui_path)
            sys.exit(1)

        self.setCentralWidget(self.ui)
        self.setWindowTitle(texts.APP_TITLE)

        # Apply application/window icon (also affects dialogs)
        self._apply_app_icon()

        # Ensure now playing label starts empty
        self.ui.lblPlayingNow.setText("")

        # Lock size based on what was drawn in the Designer
        self.setFixedSize(self.ui.size())

        # Track last selected row for Shift+Click range selection
        self.tblSongs_last_selected_row = None

        # Track last clicked source for debug shortcut
        self.last_click_source = None
        self.last_clicked_tree_item = None
        self.last_clicked_tblSongs_row = None

        # Data service (pure logic)
        self.data_service = DataService()

        # Child window controllers
        self.section_controller = SectionWindowController(self)
        self.playlist_controller = PlaylistWindowController(self)
        self.playlists_tree_controller = PlaylistsTreeController(self)
        self.save_controller = SaveController(self)
        self.media_controller = MediaController(self)
        self.volume_controller = VolumeController(self)
        self.songs_table_controller = SongsTableController(self)
        self.locales_controller = LocalesController(self)
        self.load_controller = LoadController(self)

        # Initialize Audio Player
        self.media_controller.init_audio_player()
        self.volume_controller.initialize()

        # Media controls enabled by default
        self.media_enabled = True
        self.use_songs_json = False
        self._load_mode = None

        # UI setup and signal wiring
        self._setup_ui()

    def _apply_app_icon(self):
        """Set app/window icon for main window and dialogs."""
        try:
            icon_path = config.GUI_DIR / "icon_256.png"
            if not icon_path.exists():
                icon_path = config.GUI_DIR / "icon.jpg"
            if not icon_path.exists():
                logging.warning("App icon not found in resources/gui (icon_256.png or icon.jpg).")
                return
            icon = QIcon(str(icon_path))
            self.setWindowIcon(icon)
            QApplication.setWindowIcon(icon)
        except Exception as e:
            logging.exception(f"Failed to apply app icon: {e}")

    def _setup_ui(self):
        """Configure UI widgets and connect signals."""
        # ==== Locales Table Configuration ====
        self.ui.tblLocales.setColumnCount(2)
        self.ui.tblLocales.setHorizontalHeaderLabels(self.locales_controller.original_headers)
        for col in range(self.ui.tblLocales.columnCount()):
            header_item = self.ui.tblLocales.horizontalHeaderItem(col)
            font = header_item.font()
            font.setBold(True)
            header_item.setFont(font)
            header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.ui.tblLocales.setEditTriggers(QAbstractItemView.DoubleClicked)
        self.ui.tblLocales.setAcceptDrops(False)
        self.ui.tblLocales.setDragEnabled(False)
        self.ui.tblLocales.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tblLocales.setWordWrap(False)

        self.multi_line_delegate = MultiLineDelegate(self.ui.tblLocales)

        self.ui.tblLocales.verticalHeader().setVisible(False)
        self.ui.tblLocales.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.tblLocales.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.tblLocales.setTextElideMode(Qt.ElideNone)
        self.ui.tblLocales.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.tblLocales.setStyleSheet(
            "QTableWidget::item { border: none; }"
            "QTableWidget:focus { outline: none; }"
            "QTableWidget::item:selected { background-color: #90CAF9; color: #000000; outline: none; }"
            "QTableWidget::item:selected:focus { outline: none; }"
            "QTableWidget::item:selected:active { outline: none; }"
            "QTableWidget::item:focus { outline: none; }"
        )

        self.ui.tblLocales.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.ui.tblLocales.verticalHeader().setDefaultSectionSize(25)

        header = self.ui.tblLocales.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(50)
        header.setSortIndicatorShown(False)
        header.sectionClicked.connect(self.locales_controller.handle_header_click)
        self.ui.tblLocales.itemChanged.connect(self.locales_controller.on_item_changed)

        # ==== Playlist Tree Configuration ====
        self.ui.treePlaylists.setAcceptDrops(True)
        self.ui.treePlaylists.setDragEnabled(True)
        self.ui.treePlaylists.setDragDropMode(QAbstractItemView.DragDrop)
        self.ui.treePlaylists.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.treePlaylists.setDefaultDropAction(Qt.MoveAction)
        self.ui.treePlaylists.setColumnCount(1)
        self.ui.treePlaylists.setHeaderLabels([texts.TREE_PLAYLIST_HEADER])
        self.ui.treePlaylists.setDropIndicatorShown(True)
        self.ui.treePlaylists.setIndentation(12)
        self.ui.treePlaylists.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.ui.treePlaylists.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.ui.treePlaylists.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.treePlaylists.setTextElideMode(Qt.ElideNone)
        self.ui.treePlaylists.setStyleSheet(
            "QTreeWidget::item { padding-top: 3px; padding-bottom: 3px; padding-left: 6px; padding-right: 6px; }"
            "QTreeWidget:focus { outline: none; }"
            "QTreeWidget::item:selected { background-color: #90CAF9; color: #000000; outline: none; }"
            "QTreeWidget::item:selected:focus { outline: none; }"
            "QTreeWidget::item:selected:active { outline: none; }"
            "QTreeWidget::item:focus { outline: none; }"
        )
        self.ui.treePlaylists.itemDoubleClicked.connect(self.playlists_tree_controller.on_item_double_clicked)
        self.ui.treePlaylists.itemClicked.connect(self.playlists_tree_controller.on_item_clicked)
        self.ui.treePlaylists.currentItemChanged.connect(
            lambda current, previous: self.playlists_tree_controller.on_item_clicked(current, 0)
            if current is not None and QApplication.mouseButtons() == Qt.NoButton
            else None
        )

        # ==== Songs Table Configuration ====
        self.ui.tblSongs.setColumnCount(6)
        self.ui.tblSongs.setHorizontalHeaderLabels(self.songs_table_controller.original_headers)
        for col in range(self.ui.tblSongs.columnCount()):
            header_item = self.ui.tblSongs.horizontalHeaderItem(col)
            font = header_item.font()
            font.setBold(True)
            header_item.setFont(font)
            if col == 0:
                header_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            else:
                header_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.ui.tblSongs.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ui.tblSongs.setAcceptDrops(False)
        self.ui.tblSongs.setDragEnabled(True)
        self.ui.tblSongs.setDragDropMode(QAbstractItemView.DragOnly)
        self.ui.tblSongs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ui.tblSongs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.ui.tblSongs.setWordWrap(False)
        self.ui.tblSongs.verticalHeader().setVisible(True)
        self.ui.tblSongs.verticalHeader().setDefaultAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.ui.tblSongs.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.tblSongs.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.ui.tblSongs.setTextElideMode(Qt.ElideNone)
        self.ui.tblSongs.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.ui.tblSongs.setStyleSheet(
            "QTableWidget::item { border: none; }"
            "QTableWidget:focus { outline: none; }"
            "QTableWidget::item:selected { background-color: #90CAF9; color: #000000; outline: none; }"
            "QTableWidget::item:selected:focus { outline: none; }"
            "QTableWidget::item:selected:active { outline: none; }"
            "QTableWidget::item:focus { outline: none; }"
        )

        songs_header = self.ui.tblSongs.horizontalHeader()
        songs_header.setStretchLastSection(False)
        songs_header.setSectionResizeMode(0, QHeaderView.Fixed)
        songs_header.setMinimumSectionSize(22)
        songs_header.sectionClicked.connect(self.songs_table_controller.handle_header_click)
        play_header = self.ui.tblSongs.horizontalHeaderItem(0)
        if play_header:
            play_header.setText("▶️")
        self.ui.tblSongs.setColumnWidth(0, 22)

        # Search placeholders and filters
        if hasattr(self.ui, "txtSearchSongs"):
            self.ui.txtSearchSongs.setPlaceholderText(texts.PLACEHOLDER_SEARCH_ALL)
            self.ui.txtSearchSongs.textChanged.connect(self.songs_table_controller.filter_tblSongs)
        if hasattr(self.ui, "txtSearchLocales"):
            self.ui.txtSearchLocales.setPlaceholderText(texts.PLACEHOLDER_SEARCH_ALL)
            self.ui.txtSearchLocales.textChanged.connect(self.locales_controller.filter_tblLocales)
        if hasattr(self.ui, "btnClearSearchSongs"):
            self.ui.btnClearSearchSongs.clicked.connect(self.songs_table_controller.on_btnClearSearchSongs_clicked)
        if hasattr(self.ui, "btnClearSearchLocales"):
            self.ui.btnClearSearchLocales.clicked.connect(self.locales_controller.on_btnClearSearchLocales_clicked)

        # Event filters
        self.tblSongs_play_filter = TblSongsPlayColumnFilter(
            self.ui.tblSongs,
            self.media_controller.handle_tblSongs_play_click,
        )
        self.ui.tblSongs.viewport().installEventFilter(self.tblSongs_play_filter)

        if hasattr(self.ui, "txtSearchSongs"):
            self.txtSongs_no_newline_filter = NoNewlineFilter(self.ui.txtSearchSongs)
            self.ui.txtSearchSongs.installEventFilter(self.txtSongs_no_newline_filter)

        self.tree_drop_filter = PlaylistsTreeDropFilter(self.ui.treePlaylists, self.ui.tblSongs)
        self.ui.treePlaylists.installEventFilter(self.tree_drop_filter)
        self.ui.treePlaylists.viewport().installEventFilter(self.tree_drop_filter)

        self.tree_to_search_song_filter = TreeToSearchDropFilter(
            self.ui.treePlaylists,
            self.ui.txtSearchSongs,
            "song",
        )
        self.ui.txtSearchSongs.installEventFilter(self.tree_to_search_song_filter)

        self.tree_to_search_locales_filter = TreeToSearchDropFilter(
            self.ui.treePlaylists,
            self.ui.txtSearchLocales,
            "titleId",
        )
        self.ui.txtSearchLocales.installEventFilter(self.tree_to_search_locales_filter)

        # --- Table signals ---
        self.ui.tblSongs.cellClicked.connect(self.media_controller.on_tblSongs_cell_clicked)
        self.ui.tblSongs.itemSelectionChanged.connect(self.songs_table_controller.update_selected_count)
        self.ui.tblSongs.currentCellChanged.connect(self.media_controller.on_tblSongs_current_cell_changed)
        self.songs_table_controller.update_selected_count()
        self.ui.tblSongs.shortcut_select_all = QKeySequence(QKeySequence.SelectAll)
        self.ui.tblSongs.shortcut_select_all = QShortcut(self.ui.tblSongs.shortcut_select_all, self.ui.tblSongs)
        self.ui.tblSongs.shortcut_select_all.activated.connect(self.songs_table_controller.select_visible_rows)

        # --- Media controls ---
        self.ui.btnPlay.clicked.connect(self.media_controller.on_btnPlay_clicked)
        self.ui.sldTimeline.sliderMoved.connect(self.media_controller.on_sldTimeline_moved)
        self.media_controller.set_playback_controls_enabled(False)

        # --- Connect song selection buttons ---
        self.ui.btnSelectAllSongs.clicked.connect(self.songs_table_controller.on_btnSelectAllSongs_clicked)
        self.ui.btnSelectAllSongs.setEnabled(False)
        self.ui.btnClearSelectedSongs.clicked.connect(self.songs_table_controller.on_btnClearSelectedSongs_clicked)

        # --- Connect playlist/section buttons ---
        self.ui.btnDelete.clicked.connect(self.playlists_tree_controller.on_delete_clicked)
        self.ui.btnAddSection.clicked.connect(lambda: self.section_controller.open(mode="create"))
        self.ui.btnEdit.clicked.connect(self._on_btnEdit_clicked)
        self.ui.btnAddPlaylist.clicked.connect(lambda: self.playlist_controller.open(mode="create"))
        if hasattr(self.ui, "btnSave"):
            self.ui.btnSave.clicked.connect(self.save_controller.on_btnSave_clicked)
        self.update_action_buttons()

    def _on_btnEdit_clicked(self):
        """Open the Section window to edit the selected section."""
        try:
            item = self.ui.treePlaylists.currentItem()
            if not item:
                show_info(self, texts.TITLE_EDIT, texts.EDIT_SELECT_ITEM)
                return
            item_type = item.data(0, TREE_ITEM_TYPE_ROLE)
            if item_type == TreeItemType.SECTION.value:
                self.section_controller.open(mode="edit", item=item)
                return
            if item_type == TreeItemType.PLAYLIST.value:
                self.playlist_controller.open(mode="edit", item=item)
                return
            show_info(self, texts.TITLE_EDIT, texts.EDIT_SELECT_SECTION_OR_PLAYLIST)
        except Exception as e:
            logging.exception(f"Error opening edit section window: {e}")
            show_error(self, texts.TITLE_ERROR, texts.EDIT_OPEN_ERROR.format(error=e))

    def update_action_buttons(self):
        """Enable/disable playlist actions based on tree content."""
        try:
            has_sections = self.ui.treePlaylists.topLevelItemCount() > 0
            if hasattr(self.ui, "btnAddPlaylist"):
                self.ui.btnAddPlaylist.setEnabled(has_sections)
            if hasattr(self.ui, "btnEdit"):
                self.ui.btnEdit.setEnabled(has_sections)
            if hasattr(self.ui, "btnDelete"):
                self.ui.btnDelete.setEnabled(has_sections)
        except Exception as e:
            logging.exception(f"Failed to update action buttons: {e}")

    def _reset_media_player(self, for_video=False):
        """Reset media player via controller (used by playlist clicks)."""
        try:
            self.media_controller.reset_media_player(for_video=for_video)
        except Exception as e:
            logging.exception(f"Error resetting media player: {e}")

    def keyPressEvent(self, event):
        """Handle Delete key for treePlaylists removal"""
        try:
            if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
                if self.ui.treePlaylists.hasFocus() or self.ui.treePlaylists.viewport().hasFocus():
                    self.playlists_tree_controller.on_delete_clicked()
                    event.accept()
                    return
            if event.key() == Qt.Key_I and (event.modifiers() & Qt.ControlModifier):
                if self._is_debug_shortcut_allowed():
                    if self.last_click_source == "treePlaylists":
                        self._show_tree_item_debug(self.last_clicked_tree_item or self.ui.treePlaylists.currentItem())
                        event.accept()
                        return
                    if self.last_click_source == "tblSongs":
                        row = self.last_clicked_tblSongs_row
                        if row is None or row < 0:
                            row = self.ui.tblSongs.currentRow()
                        self._show_tblSongs_row_debug(row)
                        event.accept()
                        return
        except Exception as e:
            logging.exception(f"Error handling key press: {e}")
        super().keyPressEvent(event)

    def _is_debug_shortcut_allowed(self):
        """Block debug shortcut while editing or typing in inputs."""
        try:
            active_window = QApplication.activeWindow()
            if active_window and active_window not in (self, self.ui):
                return False

            if getattr(self, "section_window", None) and self.section_window.isVisible():
                return False
            if getattr(self, "playlist_window", None) and self.playlist_window.isVisible():
                return False

            focus_widget = QApplication.focusWidget()
            if focus_widget and self._is_text_input_widget(focus_widget):
                return False
        except Exception as e:
            logging.exception(f"Error checking debug shortcut availability: {e}")
            return False
        return True

    def _is_text_input_widget(self, widget):
        """Check if widget (or its parents) is a text input."""
        try:
            w = widget
            while w:
                if isinstance(w, (QLineEdit, QTextEdit, QPlainTextEdit, QComboBox)):
                    return True
                w = w.parent()
        except Exception as e:
            logging.exception(f"Error checking input widget: {e}")
        return False

    def _show_debug_text_dialog(self, title, text):
        """Show a read-only dialog with debug text."""
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle(title)
            dlg.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint)
            dlg.setMinimumSize(700, 500)

            layout = QVBoxLayout(dlg)
            editor = QPlainTextEdit(dlg)
            editor.setReadOnly(True)
            try:
                editor.setFont(QFont("Consolas", 9))
            except Exception:
                pass
            editor.setPlainText(text)
            layout.addWidget(editor)

            buttons = QDialogButtonBox(QDialogButtonBox.Close)
            buttons.rejected.connect(dlg.reject)
            layout.addWidget(buttons)

            dlg.setLayout(layout)
            dlg.exec()
        except Exception as e:
            logging.exception(f"Failed to show debug dialog: {e}")

    def _json_safe_dumps(self, data):
        """Safe JSON dump for debug output."""
        def _default(obj):
            try:
                return str(obj)
            except Exception:
                return "<unserializable>"

        try:
            return json.dumps(data, ensure_ascii=False, indent=2, default=_default)
        except Exception as e:
            logging.exception(f"Failed to serialize debug data: {e}")
            return str(data)

    def _show_tblSongs_row_debug(self, row):
        """Show full debug data for a tblSongs row."""
        try:
            if row is None or row < 0 or row >= self.ui.tblSongs.rowCount():
                return

            headers = []
            for col in range(self.ui.tblSongs.columnCount()):
                header_item = self.ui.tblSongs.horizontalHeaderItem(col)
                headers.append(header_item.text() if header_item else f"Column {col}")

            columns = []
            for col in range(self.ui.tblSongs.columnCount()):
                item = self.ui.tblSongs.item(row, col)
                columns.append({
                    "index": col,
                    "header": headers[col],
                    "text": item.text() if item else None,
                    "userRole": item.data(Qt.UserRole) if item else None,
                })

            code_item = self.ui.tblSongs.item(row, 1)
            song_data = code_item.data(Qt.UserRole) if code_item else None

            payload = {
                "source": "tblSongs",
                "row": row,
                "isHidden": self.ui.tblSongs.isRowHidden(row),
                "songData": song_data,
                "columns": columns,
            }
            self._show_debug_text_dialog(texts.DEBUG_TBLSONGS_TITLE, self._json_safe_dumps(payload))
        except Exception as e:
            logging.exception(f"Failed to show tblSongs debug data: {e}")

    def _show_tree_item_debug(self, item):
        """Show full debug data for a treePlaylists item."""
        try:
            if not item:
                return

            path = []
            node = item
            while node:
                path.append(node.text(0))
                node = node.parent()
            path = list(reversed(path))

            user_role = item.data(0, Qt.UserRole)
            if isinstance(user_role, dict):
                ordered = OrderedDict()
                item_type = item.data(0, TREE_ITEM_TYPE_ROLE)
                if item_type == TreeItemType.SECTION.value:
                    for key in ("__class", "act", "isc", "title", "titleId", "requests"):
                        ordered[key] = user_role.get(key)
                elif item_type == TreeItemType.PLAYLIST.value:
                    for key in ("__class", "titleId", "descriptionId", "coverPath", "maps"):
                        ordered[key] = user_role.get(key)
                for key, value in user_role.items():
                    if key not in ordered:
                        ordered[key] = value
                user_role = ordered

            payload = {
                "source": "treePlaylists",
                "text": item.text(0),
                "path": path,
                "type": item.data(0, TREE_ITEM_TYPE_ROLE),
                "songCode": item.data(0, SONG_CODE_ROLE),
                "missingSongMessage": item.data(0, MISSING_SONG_MESSAGE_ROLE),
                "missingSongCode": item.data(0, MISSING_SONG_CODE_ROLE),
                "playlistId": item.data(0, PLAYLIST_ID_ROLE),
                "playlistTitleText": item.data(0, PLAYLIST_TITLE_TEXT_ROLE),
                "playlistDescriptionText": item.data(0, PLAYLIST_DESCRIPTION_TEXT_ROLE),
                "playlistCoverPngPath": item.data(0, PLAYLIST_COVER_PNG_PATH_ROLE),
                "userRole": user_role,
            }
            self._show_debug_text_dialog(texts.DEBUG_TREEPLAYLISTS_TITLE, self._json_safe_dumps(payload))
        except Exception as e:
            logging.exception(f"Failed to show treePlaylists debug data: {e}")

    def _disable_media_ui(self):
        """Disable media controls and hide play column."""
        try:
            self.ui.chkAutoplayVideo.setEnabled(False)
            self.ui.btnPlay.setEnabled(False)
            self.ui.sldTimeline.setEnabled(False)
            if hasattr(self, "volume_controller"):
                self.volume_controller.set_enabled(False)
            self.ui.tblSongs.setColumnHidden(0, True)
            self.ui.lblImg.setPixmap(QPixmap())
            self.ui.lblImg.setText("")
        except Exception as e:
            logging.exception(f"Failed to disable media UI: {e}")

    def _disable_media_playback_ui(self):
        """Disable audio/video playback controls but keep cover preview enabled."""
        try:
            self.ui.chkAutoplayVideo.setEnabled(False)
            self.ui.btnPlay.setEnabled(False)
            self.ui.sldTimeline.setEnabled(False)
            if hasattr(self, "volume_controller"):
                self.volume_controller.set_enabled(False)
            self.ui.tblSongs.setColumnHidden(0, True)
            try:
                self._reset_media_player(for_video=False)
            except Exception:
                pass
        except Exception as e:
            logging.exception(f"Failed to disable media playback UI: {e}")

    def _clear_directory_contents(self, directory_path, log_label=None):
        """Delete all files and subfolders inside a directory."""
        try:
            label = log_label or str(directory_path)
            logging.info(f"Clearing directory contents: {label}")
            if not directory_path.exists():
                return
            for item in directory_path.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                QApplication.processEvents()
        except Exception as e:
            logging.exception(f"Failed to clear directory contents ({directory_path}): {e}")

    def begin(self):
        """Start the initial load flow."""
        return self.load_controller.begin()
