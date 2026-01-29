import logging

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QTableWidgetItem

from ui.shared import texts


class SongsTableController:
    def __init__(self, main_window):
        self.main = main_window
        self.sort_column = -1
        self.sort_state = 0  # 0=original, 1=asc, 2=desc
        self.original_headers = list(texts.SONGS_HEADERS)
        self.original_rows = []
        self.all_data = {}

    def handle_header_click(self, column):
        """3-state sorting for tblSongs: original -> asc -> desc -> original"""
        if column == 0:
            header_item = self.main.ui.tblSongs.horizontalHeaderItem(column)
            if header_item:
                header_item.setText("▶️")
            return
        if self.sort_column == column:
            self.sort_state = (self.sort_state + 1) % 3
        else:
            if self.sort_column != -1:
                prev_header = self.main.ui.tblSongs.horizontalHeaderItem(self.sort_column)
                prev_header.setText(self.original_headers[self.sort_column])
            self.sort_column = column
            self.sort_state = 1  # start asc

        header_item = self.main.ui.tblSongs.horizontalHeaderItem(column)
        if self.sort_state == 0:
            header_item.setText(self.original_headers[column])
        elif self.sort_state == 1:
            header_item.setText(f"↑ {self.original_headers[column]}")
        else:
            header_item.setText(f"↓ {self.original_headers[column]}")

        if self.sort_state == 1:
            self.main.ui.tblSongs.sortItems(column, Qt.AscendingOrder)
        elif self.sort_state == 2:
            self.main.ui.tblSongs.sortItems(column, Qt.DescendingOrder)
        else:
            self.restore_original_order()
        self.refresh_row_numbers()

    def filter_tblSongs(self):
        """Filter tblSongs according to text typed in txtSearchSongs."""
        try:
            self.main.ui.tblSongs.clearSelection()

            search_text = self.main.ui.txtSearchSongs.toPlainText().lower()
            filter_empty = not search_text

            for row in range(self.main.ui.tblSongs.rowCount()):
                if filter_empty:
                    self.main.ui.tblSongs.setRowHidden(row, False)
                    continue

                match_found = False
                for col in range(self.main.ui.tblSongs.columnCount()):
                    item = self.main.ui.tblSongs.item(row, col)
                    if item and search_text in item.text().lower():
                        match_found = True
                        break

                self.main.ui.tblSongs.setRowHidden(row, not match_found)

            self.main.ui.btnSelectAllSongs.setEnabled(not filter_empty)
        except Exception as e:
            logging.exception(f"Error filtering songs table: {e}")

        self.update_count()
        self.refresh_row_numbers()
        self.main.ui.tblSongs.resizeColumnsToContents()
        self.main.ui.tblSongs.setColumnWidth(0, 22)

    def on_btnClearSearchSongs_clicked(self):
        """Clear songs search box and remove filter."""
        try:
            self.main.ui.txtSearchSongs.blockSignals(True)
            self.main.ui.txtSearchSongs.setPlainText("")
            self.main.ui.txtSearchSongs.blockSignals(False)
            self.filter_tblSongs()
        except Exception as e:
            logging.exception(f"Error clearing songs search: {e}")

    def update_count(self):
        """Update filter result count for songs table."""
        try:
            visible_rows = sum(
                not self.main.ui.tblSongs.isRowHidden(row)
                for row in range(self.main.ui.tblSongs.rowCount())
            )
            self.main.ui.lblFilterSongsCount.setText(texts.FILTER_RESULTS_COUNT.format(count=visible_rows))
        except Exception as e:
            logging.exception(f"Error updating songs count label: {e}")

    def update_selected_count(self):
        """Update selected rows count for songs table."""
        try:
            selection_model = self.main.ui.tblSongs.selectionModel()
            if not selection_model:
                self.main.ui.lblSelectedSongsCount.setText(texts.SELECTED_SONGS_COUNT.format(count=0))
                return

            rows = selection_model.selectedRows(0)
            if rows:
                selected_count = len({idx.row() for idx in rows})
            else:
                selected_count = len({idx.row() for idx in self.main.ui.tblSongs.selectedIndexes()})

            self.main.ui.lblSelectedSongsCount.setText(texts.SELECTED_SONGS_COUNT.format(count=selected_count))
        except Exception as e:
            logging.exception(f"Error updating selected songs count: {e}")

    def update_row_header_width(self, visible_count=None):
        """Resize tblSongs vertical header to the minimum width needed for row numbers."""
        try:
            if visible_count is None:
                visible_count = sum(
                    not self.main.ui.tblSongs.isRowHidden(row)
                    for row in range(self.main.ui.tblSongs.rowCount())
                )
            row_count = max(visible_count, 1)
            digits_text = str(row_count)
            font = self.main.ui.tblSongs.verticalHeader().font()
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(digits_text)
            padding = 10
            width = text_width + padding
            self.main.ui.tblSongs.verticalHeader().setFixedWidth(width)
        except Exception as e:
            logging.exception(f"Error updating tblSongs row header width: {e}")

    def refresh_row_numbers(self):
        """Update vertical header numbers to match visible rows only."""
        try:
            visible_index = 1
            for row in range(self.main.ui.tblSongs.rowCount()):
                if self.main.ui.tblSongs.isRowHidden(row):
                    self.main.ui.tblSongs.setVerticalHeaderItem(row, QTableWidgetItem(""))
                    continue
                header_item = QTableWidgetItem(str(visible_index))
                header_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                self.main.ui.tblSongs.setVerticalHeaderItem(row, header_item)
                visible_index += 1

            self.update_row_header_width(visible_index - 1)
        except Exception as e:
            logging.exception(f"Error refreshing tblSongs row numbers: {e}")

    def restore_original_order(self):
        """Restore original order of tblSongs (alphabetical) and reapply filter."""
        if not self.original_rows or not self.all_data:
            return

        self.main.ui.tblSongs.setRowCount(0)

        for codename in self.original_rows:
            if codename not in self.all_data:
                continue

            song = self.all_data[codename]
            row = self.main.ui.tblSongs.rowCount()
            self.main.ui.tblSongs.insertRow(row)

            self.main.ui.tblSongs.setItem(row, 0, self.main.media_controller.create_tblSongs_play_item())

            item_code = QTableWidgetItem(song["CodeName"])
            item_code.setData(Qt.UserRole, song)
            self.main.ui.tblSongs.setItem(row, 1, item_code)
            self.main.ui.tblSongs.setItem(row, 2, QTableWidgetItem(song["Title"]))
            self.main.ui.tblSongs.setItem(row, 3, QTableWidgetItem(song["Artist"]))
            self.main.ui.tblSongs.setItem(row, 4, QTableWidgetItem(song["JDVersion"]))
            self.main.ui.tblSongs.setItem(row, 5, QTableWidgetItem(song["OriginalJDVersion"]))

        self.filter_tblSongs()
        self.main.ui.tblSongs.resizeColumnsToContents()
        self.main.ui.tblSongs.setColumnWidth(0, 22)
        self.refresh_row_numbers()
        self.update_count()

    def populate_songs(self, songs_list_sorted):
        """Populate tblSongs using preloaded data (UI-only)."""
        try:
            logging.info("populate_songs thread=%s table_thread=%s", QThread.currentThread(), self.main.ui.tblSongs.thread())
        except Exception:
            pass
        self.all_data = {song["CodeName"]: song for song in songs_list_sorted}
        self.original_rows = [song["CodeName"] for song in songs_list_sorted]

        self.main.ui.tblSongs.setRowCount(0)
        self.main.ui.tblSongs.setColumnCount(6)
        self.main.ui.tblSongs.setHorizontalHeaderLabels(self.original_headers)

        for row, song in enumerate(songs_list_sorted):
            self.main.ui.tblSongs.insertRow(row)
            self.main.ui.tblSongs.setItem(row, 0, self.main.media_controller.create_tblSongs_play_item())

            item_code = QTableWidgetItem(song["CodeName"])
            item_code.setData(Qt.UserRole, song)
            self.main.ui.tblSongs.setItem(row, 1, item_code)
            self.main.ui.tblSongs.setItem(row, 2, QTableWidgetItem(song["Title"]))
            self.main.ui.tblSongs.setItem(row, 3, QTableWidgetItem(song["Artist"]))
            self.main.ui.tblSongs.setItem(row, 4, QTableWidgetItem(song["JDVersion"]))
            self.main.ui.tblSongs.setItem(row, 5, QTableWidgetItem(song["OriginalJDVersion"]))

        self.main.ui.tblSongs.resizeColumnsToContents()
        self.main.ui.tblSongs.setColumnWidth(0, 22)
        self.refresh_row_numbers()

        self.main.ui.lblLoadedSongsCount.setText(texts.LOADED_SONGS_COUNT.format(count=len(songs_list_sorted)))
        self.update_count()

    def on_btnSelectAllSongs_clicked(self):
        """Select all visible songs (respecting current filter)."""
        try:
            from PySide6.QtCore import QItemSelection, QItemSelectionModel

            selection = QItemSelection()
            for row in range(self.main.ui.tblSongs.rowCount()):
                if not self.main.ui.tblSongs.isRowHidden(row):
                    top_left = self.main.ui.tblSongs.model().index(row, 0)
                    bottom_right = self.main.ui.tblSongs.model().index(row, self.main.ui.tblSongs.columnCount() - 1)
                    selection.select(top_left, bottom_right)

            self.main.ui.tblSongs.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
            logging.debug("All visible songs selected")
        except Exception as e:
            logging.exception(f"Error selecting all songs: {e}")

    def select_visible_rows(self):
        """Select only visible rows (helper for Ctrl+A)."""
        try:
            from PySide6.QtCore import QItemSelection, QItemSelectionModel

            selection = QItemSelection()
            for row in range(self.main.ui.tblSongs.rowCount()):
                if not self.main.ui.tblSongs.isRowHidden(row):
                    top_left = self.main.ui.tblSongs.model().index(row, 0)
                    bottom_right = self.main.ui.tblSongs.model().index(row, self.main.ui.tblSongs.columnCount() - 1)
                    selection.select(top_left, bottom_right)

            self.main.ui.tblSongs.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
            logging.debug("Visible rows selected via Ctrl+A")
        except Exception as e:
            logging.exception(f"Error selecting visible rows: {e}")

    def on_btnClearSelectedSongs_clicked(self):
        """Clear all song selections."""
        try:
            self.main.ui.tblSongs.clearSelection()
            logging.debug("All song selections cleared")
        except Exception as e:
            logging.exception(f"Error clearing song selections: {e}")
