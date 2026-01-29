import json
import logging

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import QTableWidgetItem, QHeaderView

from ... import config
from ..shared import texts
from ..shared.constants import (
    TREE_ITEM_TYPE_ROLE,
    PLAYLIST_ID_ROLE,
    PLAYLIST_TITLE_TEXT_ROLE,
    PLAYLIST_DESCRIPTION_TEXT_ROLE,
    SECTION_TITLE_ROLE,
    SECTION_TITLE_ID_ROLE,
    TreeItemType,
)


class LocalesController:
    def __init__(self, main_window):
        self.main = main_window
        self.sort_column = -1
        self.sort_state = 0  # 0=original, 1=asc, 2=desc
        self.original_headers = list(texts.LOCALES_HEADERS)
        self.original_rows = []
        self._bulk_loading = False

    def handle_header_click(self, column):
        """3-state sorting for tblLocales: original -> asc -> desc -> original"""
        if self.sort_column == column:
            self.sort_state = (self.sort_state + 1) % 3
        else:
            if self.sort_column != -1:
                prev_header = self.main.ui.tblLocales.horizontalHeaderItem(self.sort_column)
                prev_header.setText(self.original_headers[self.sort_column])
            self.sort_column = column
            self.sort_state = 1  # start asc

        header_item = self.main.ui.tblLocales.horizontalHeaderItem(column)
        if self.sort_state == 0:
            header_item.setText(self.original_headers[column])
        elif self.sort_state == 1:
            header_item.setText(f"↑ {self.original_headers[column]}")
        else:
            header_item.setText(f"↓ {self.original_headers[column]}")

        if self.sort_state == 1:
            self.main.ui.tblLocales.sortItems(column, Qt.AscendingOrder)
        elif self.sort_state == 2:
            self.main.ui.tblLocales.sortItems(column, Qt.DescendingOrder)
        else:
            self.restore_original_order()

    def on_item_changed(self, item):
        """Recalculate row height when a cell is edited (to support line breaks)."""
        try:
            if self._bulk_loading:
                return
            if item.column() != 1:
                return

            row = item.row()
            id_item = self.main.ui.tblLocales.item(row, 0)
            if not id_item:
                return
            locale_id = id_item.text().strip()
            new_text = item.text()
            if not locale_id:
                return

            self.main.ui.tblLocales.resizeRowToContents(row)

            if not config.TEMP_LOCALISATION_JSON.exists():
                return

            locales_dict = json.loads(
                config.TEMP_LOCALISATION_JSON.read_text(encoding="utf-8")
            )
            if str(locales_dict.get(locale_id, "")) == str(new_text):
                return

            locales_dict[locale_id] = new_text
            config.TEMP_LOCALISATION_JSON.write_text(
                json.dumps(locales_dict, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

            modified_item = None
            for i in range(self.main.ui.treePlaylists.topLevelItemCount()):
                section_item = self.main.ui.treePlaylists.topLevelItem(i)
                if not section_item:
                    continue
                section_type = section_item.data(0, TREE_ITEM_TYPE_ROLE)
                if section_type == TreeItemType.SECTION.value:
                    data = section_item.data(0, Qt.UserRole) or {}
                    title_id = section_item.data(0, SECTION_TITLE_ID_ROLE) or data.get("titleId", "")
                    if str(title_id) == locale_id:
                        section_item.setText(0, new_text)
                        section_item.setData(0, SECTION_TITLE_ROLE, new_text)
                        data["title"] = new_text
                        data["titleId"] = title_id
                        if hasattr(self.main, "playlists_tree_controller"):
                            self.main.playlists_tree_controller.update_section_requests(section_item)
                        modified_item = section_item
                for j in range(section_item.childCount()):
                    playlist_item = section_item.child(j)
                    if not playlist_item:
                        continue
                    if playlist_item.data(0, TREE_ITEM_TYPE_ROLE) != TreeItemType.PLAYLIST.value:
                        continue
                    pdata = playlist_item.data(0, Qt.UserRole) or {}
                    updated = False
                    if str(pdata.get("titleId", "")) == locale_id:
                        playlist_item.setData(0, PLAYLIST_TITLE_TEXT_ROLE, new_text)
                        pdata.pop("titleText", None)
                        updated = True
                    if str(pdata.get("descriptionId", "")) == locale_id:
                        playlist_item.setData(0, PLAYLIST_DESCRIPTION_TEXT_ROLE, new_text)
                        pdata.pop("descriptionText", None)
                        updated = True
                    if updated:
                        playlist_id = playlist_item.data(0, PLAYLIST_ID_ROLE) or pdata.get("playlistID", "")
                        title_text = playlist_item.data(0, PLAYLIST_TITLE_TEXT_ROLE) or pdata.get("titleText", "")
                        description_text = playlist_item.data(0, PLAYLIST_DESCRIPTION_TEXT_ROLE) or pdata.get("descriptionText", "")
                        playlist_item.setText(0, f'{playlist_id}: "{title_text} - {description_text}"')
                        playlist_item.setData(0, Qt.UserRole, pdata)
                        modified_item = playlist_item

            if modified_item is not None:
                self.main.ui.treePlaylists.setCurrentItem(modified_item)
                self.main.ui.treePlaylists.scrollToItem(modified_item)
                self.main.ui.treePlaylists.setFocus()
        except Exception as e:
            logging.exception(f"Error resizing row after editing: {e}")

    def filter_tblLocales(self):
        """Filter tblLocales according to text typed in txtSearchLocales."""
        try:
            search_text = self.main.ui.txtSearchLocales.toPlainText().lower()
            filter_empty = not search_text

            for row in range(self.main.ui.tblLocales.rowCount()):
                if filter_empty:
                    self.main.ui.tblLocales.setRowHidden(row, False)
                    continue

                match_found = False
                id_item = self.main.ui.tblLocales.item(row, 0)
                text_item = self.main.ui.tblLocales.item(row, 1)

                if (id_item and search_text in id_item.text().lower()) or \
                   (text_item and search_text in text_item.text().lower()):
                    match_found = True

                self.main.ui.tblLocales.setRowHidden(row, not match_found)
        except Exception as e:
            logging.exception(f"Error filtering locales table: {e}")

        self.main.ui.tblLocales.resizeColumnsToContents()
        self.update_count()

    def on_btnClearSearchLocales_clicked(self):
        """Clear locales search box and remove filter."""
        try:
            self.main.ui.txtSearchLocales.blockSignals(True)
            self.main.ui.txtSearchLocales.setPlainText("")
            self.main.ui.txtSearchLocales.blockSignals(False)
            self.filter_tblLocales()
        except Exception as e:
            logging.exception(f"Error clearing locales search: {e}")

    def update_count(self):
        """Update filter result count for locales table."""
        try:
            visible_rows = sum(
                not self.main.ui.tblLocales.isRowHidden(row)
                for row in range(self.main.ui.tblLocales.rowCount())
            )
            self.main.ui.lblFilterLocalesCount.setText(texts.FILTER_RESULTS_COUNT.format(count=visible_rows))
        except Exception as e:
            logging.exception(f"Error updating locales count label: {e}")

    def restore_original_order(self):
        """Restore original order of tblLocales (reverse JSON order) and reapply filter."""
        if not self.original_rows:
            return

        self._bulk_loading = True
        table = self.main.ui.tblLocales
        try:
            table.blockSignals(True)
            table.setUpdatesEnabled(False)
            table.setSortingEnabled(False)

            table.setRowCount(0)

            for id_key, text_value in self.original_rows:
                row = table.rowCount()
                table.insertRow(row)

                item_id = QTableWidgetItem(str(id_key))
                item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
                item_text = QTableWidgetItem(str(text_value))

                table.setItem(row, 0, item_id)
                table.setItem(row, 1, item_text)
        finally:
            table.setSortingEnabled(True)
            table.setUpdatesEnabled(True)
            table.blockSignals(False)
            self._bulk_loading = False

        self.filter_tblLocales()
        table.resizeColumnsToContents()
        self.update_count()

    def populate_locales(self, locales_items):
        """Populate locales table using preloaded data (UI-only)."""
        try:
            logging.info("populate_locales thread=%s table_thread=%s", QThread.currentThread(), self.main.ui.tblLocales.thread())
        except Exception:
            pass
        logging.debug("Configuring locales table...")
        self._bulk_loading = True
        if hasattr(self.main.ui, "txtSearchLocales"):
            self.main.ui.txtSearchLocales.blockSignals(True)
            self.main.ui.txtSearchLocales.setPlainText("")
            self.main.ui.txtSearchLocales.blockSignals(False)
        self.main.ui.tblLocales.setRowCount(0)
        self.main.ui.tblLocales.setColumnCount(2)
        self.main.ui.tblLocales.setHorizontalHeaderLabels(self.original_headers)

        logging.debug("Setting multiline delegate...")
        self.main.ui.tblLocales.setItemDelegate(self.main.multi_line_delegate)

        logging.debug("Setting word wrap and row heights...")
        self.main.ui.tblLocales.setWordWrap(True)
        self.main.ui.tblLocales.verticalHeader().setDefaultSectionSize(25)
        self.main.ui.tblLocales.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        logging.debug("Setting header resize modes...")
        header = self.main.ui.tblLocales.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)

        logging.info(f"Inserting {len(locales_items)} locale rows...")
        for idx, (id_key, text_value) in enumerate(locales_items):
            row = self.main.ui.tblLocales.rowCount()
            self.main.ui.tblLocales.insertRow(row)

            item_id = QTableWidgetItem(str(id_key))
            item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
            item_text = QTableWidgetItem(str(text_value))

            self.main.ui.tblLocales.setItem(row, 0, item_id)
            self.main.ui.tblLocales.setItem(row, 1, item_text)

            if (idx + 1) % 1000 == 0:
                logging.debug(f"Inserted {idx + 1}/{len(locales_items)} rows...")

        logging.debug("All rows inserted. Applying ResizeToContents mode...")
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        logging.debug("Resizing columns to content...")

        self.original_rows = [(item[0], item[1]) for item in locales_items]

        self.main.ui.tblLocales.resizeColumnsToContents()
        logging.debug("Columns resized.")

        width_needed = self.main.ui.tblLocales.columnWidth(1)
        self.main.ui.tblLocales.setColumnWidth(1, width_needed + 30)

        self.main.ui.tblLocales.viewport().update()

        self.update_count()
        self.main.ui.lblLoadedLocalesCount.setText(texts.LOADED_LOCALES_COUNT.format(count=len(locales_items)))

        logging.info(f"Populated {len(locales_items)} locale entries in reverse order.")
        self._bulk_loading = False
