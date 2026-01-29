import json
import logging

from PySide6.QtCore import Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMessageBox, QTreeWidgetItem
from PySide6.QtGui import QFont, QBrush, QColor

from ..shared.constants import (
    TREE_ITEM_TYPE_ROLE,
    SECTION_TITLE_ROLE,
    SECTION_TITLE_ID_ROLE,
    TreeItemType,
)
from ..shared import texts
from ... import config


class SectionWindowController:
    """UI logic for sectionWindow.ui."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.section_window = None

    def open(self, mode="create", item=None):
        """Open the Section window in create or edit mode."""
        try:
            # Close playlist window if open (no save)
            if getattr(self.main_window, "playlist_window", None):
                try:
                    self.main_window.playlist_window.close()
                except Exception:
                    pass

            loader = QUiLoader()
            ui_path = str(config.GUI_DIR / "sectionWindow.ui")
            self.section_window = loader.load(ui_path, None)
            if not self.section_window:
                QMessageBox.critical(self.main_window, texts.TITLE_ERROR, texts.SECTION_WINDOW_LOAD_UI_ERROR.format(path=ui_path))
                return

            # Lock window size and remove minimize/maximize
            self.section_window.setWindowFlags(
                Qt.Window | Qt.WindowCloseButtonHint | Qt.CustomizeWindowHint
            )
            self.section_window.setWindowModality(Qt.ApplicationModal)
            self.section_window.setFixedSize(self.section_window.size())

            # Track mode and item
            self.section_window._mode = mode
            self.section_window._tree_item = item

            # Reset fields
            if hasattr(self.section_window, "txtSectionTitle"):
                self.section_window.txtSectionTitle.setText("")
            if hasattr(self.section_window, "txtSectionTitleId"):
                self.section_window.txtSectionTitleId.setText("")

            # Edit mode setup
            if mode == "edit" and item is not None:
                data = item.data(0, Qt.UserRole) or {}
                title_id = str(item.data(0, SECTION_TITLE_ID_ROLE) or data.get("titleId", ""))
                title_text = item.data(0, SECTION_TITLE_ROLE) or data.get("title", item.text(0))
                if hasattr(self.section_window, "txtSectionTitleId"):
                    self.section_window.txtSectionTitleId.setText(title_id)
                if hasattr(self.section_window, "txtSectionTitle"):
                    self.section_window.txtSectionTitle.setText(title_text)
                if hasattr(self.section_window, "lblSectionTitle"):
                    self.section_window.lblSectionTitle.setText(texts.SECTION_TITLE_EDIT)
                if hasattr(self.section_window, "lblSectionLocaleInfo"):
                    self.section_window.lblSectionLocaleInfo.setVisible(False)
            else:
                if hasattr(self.section_window, "lblSectionTitle"):
                    self.section_window.lblSectionTitle.setText(texts.SECTION_TITLE_NEW)
                if hasattr(self.section_window, "lblSectionLocaleInfo"):
                    self.section_window.lblSectionLocaleInfo.setVisible(True)

            # Save handler
            if hasattr(self.section_window, "btnSectionSave"):
                self.section_window.btnSectionSave.clicked.connect(self.on_save)

            # Show window
            self.section_window.show()
            self.section_window.raise_()
            self.section_window.activateWindow()

            # Expose to main window for focus checks
            self.main_window.section_window = self.section_window
            if hasattr(self.main_window, "update_action_buttons"):
                self.main_window.update_action_buttons()
        except Exception as e:
            logging.exception(f"Error opening section window: {e}")
            QMessageBox.critical(self.main_window, texts.TITLE_ERROR, texts.SECTION_WINDOW_OPEN_ERROR.format(error=e))

    def on_save(self):
        """Create/update a localization entry and section item from the Section window."""
        try:
            if not self.section_window:
                return

            title = ""
            if hasattr(self.section_window, "txtSectionTitle"):
                title = self.section_window.txtSectionTitle.text()

            if not title or not title.strip():
                QMessageBox.warning(
                    self.section_window,
                    texts.TITLE_WARNING,
                    texts.SECTION_INVALID_NAME,
                )
                return

            title = title.strip()

            if not config.TEMP_LOCALISATION_JSON.exists():
                QMessageBox.critical(
                    self.section_window,
                    texts.TITLE_ERROR,
                    texts.SECTION_LOCALISATION_MISSING
                )
                return

            locales_dict = json.loads(
                config.TEMP_LOCALISATION_JSON.read_text(encoding="utf-8")
            )

            mode = getattr(self.section_window, "_mode", "create")
            if mode == "edit":
                title_id = ""
                if hasattr(self.section_window, "txtSectionTitleId"):
                    title_id = self.section_window.txtSectionTitleId.text().strip()
                if not title_id:
                    QMessageBox.warning(
                        self.section_window,
                        texts.TITLE_WARNING,
                        texts.SECTION_TITLE_ID_MISSING
                    )
                    return

                locales_dict[title_id] = title
                config.TEMP_LOCALISATION_JSON.write_text(
                    json.dumps(locales_dict, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                # Reload locales table in default order (last item appears first)
                _, locales_items = self.main_window.data_service.load_locales_data()
                self.main_window.locales_controller.populate_locales(locales_items)

                # Filter locales by titleId
                self.main_window.ui.txtSearchLocales.setPlainText(title_id)

                # Update treePlaylists item
                tree_item = getattr(self.section_window, "_tree_item", None)
                if tree_item is not None:
                    tree_item.setText(0, title)
                    tree_item.setData(0, SECTION_TITLE_ROLE, title)
                    tree_item.setData(0, SECTION_TITLE_ID_ROLE, title_id)
                    if hasattr(self.main_window, "playlists_tree_controller"):
                        self.main_window.playlists_tree_controller.update_section_requests(tree_item)
                    self.main_window.ui.treePlaylists.setCurrentItem(tree_item)
                    self.main_window.ui.treePlaylists.scrollToItem(tree_item)
                    self.main_window.ui.treePlaylists.setFocus()
            else:
                numeric_ids = []
                for key in locales_dict.keys():
                    try:
                        numeric_ids.append(int(str(key)))
                    except (ValueError, TypeError):
                        continue

                next_id = str((max(numeric_ids) + 1) if numeric_ids else 1)
                locales_dict[next_id] = title

                config.TEMP_LOCALISATION_JSON.write_text(
                    json.dumps(locales_dict, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )

                # Reload locales table in default order (last item appears first)
                _, locales_items = self.main_window.data_service.load_locales_data()
                self.main_window.locales_controller.populate_locales(locales_items)

                # Add section to treePlaylists (same metadata as populate_playlists)
                section_item = QTreeWidgetItem(self.main_window.ui.treePlaylists)
                section_item.setText(0, title)
                section_item.setData(0, SECTION_TITLE_ROLE, title)
                section_item.setData(0, SECTION_TITLE_ID_ROLE, next_id)
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

                if hasattr(self.main_window, "playlists_tree_controller"):
                    self.main_window.playlists_tree_controller.update_section_requests(section_item)

                self.main_window.ui.treePlaylists.setCurrentItem(section_item)
                self.main_window.ui.treePlaylists.scrollToItem(section_item)
                self.main_window.ui.treePlaylists.setFocus()

                if hasattr(self.section_window, "txtSectionTitleId"):
                    self.section_window.txtSectionTitleId.setText(next_id)

                if hasattr(self.main_window, "update_action_buttons"):
                    self.main_window.update_action_buttons()

            self.section_window.close()
        except Exception as e:
            logging.exception(f"Error saving section: {e}")
            QMessageBox.critical(self.section_window, texts.TITLE_ERROR, texts.SECTION_ERROR_SAVE.format(error=e))
