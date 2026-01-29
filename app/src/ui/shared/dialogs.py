from PySide6.QtWidgets import QMessageBox


def show_info(parent, title, text, informative_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle(title)
    msg.setText(text)
    if informative_text:
        msg.setInformativeText(informative_text)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()
    return msg


def show_warning(parent, title, text, informative_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(title)
    msg.setText(text)
    if informative_text:
        msg.setInformativeText(informative_text)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()
    return msg


def show_error(parent, title, text, informative_text=None):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Critical)
    msg.setWindowTitle(title)
    msg.setText(text)
    if informative_text:
        msg.setInformativeText(informative_text)
    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec()
    return msg


def confirm(parent, title, text, default_yes=False):
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Warning)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setDefaultButton(QMessageBox.Yes if default_yes else QMessageBox.No)
    return msg.exec() == QMessageBox.Yes
