from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStyledItemDelegate, QPlainTextEdit


class MultiLineDelegate(QStyledItemDelegate):
    """Delegate that allows editing text with multiple lines using QPlainTextEdit"""

    def createEditor(self, parent, option, index):
        """Create a QPlainTextEdit editor that allows Ctrl+Enter for line breaks"""
        editor = QPlainTextEdit(parent)
        editor.setPlainText(index.data(Qt.EditRole) or "")
        return editor

    def setEditorData(self, editor, index):
        """Load text into editor, preserving line breaks"""
        text = index.model().data(index, Qt.EditRole)
        editor.setPlainText(text)

    def setModelData(self, editor, model, index):
        """Save editor text to model, preserving line breaks"""
        model.setData(index, editor.toPlainText(), Qt.EditRole)
