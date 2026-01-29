import sys
import logging
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from . import config
from .ui.windows.main_window import MainWindow
from .ui.shared import texts


def setup_logging():
    log_file = config.get_log_filepath()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(funcName)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging system initialized.")


def run():
    try:
        config.setup_directories()
        setup_logging()

        logging.info("Application starting")
        app = QApplication(sys.argv)

        window = MainWindow()
        window.show()

        logging.info("Beginning initial load")
        window.begin()

        logging.info("Entering Qt event loop")
        sys.exit(app.exec())
    except Exception as e:
        try:
            tb = traceback.format_exc()
            logging.exception(f"Unhandled exception in __main__: {e}\nTraceback:\n{tb}")
        except Exception:
            pass
        try:
            QMessageBox.critical(None, texts.TITLE_FATAL_ERROR, texts.FATAL_ERROR_TEXT.format(error=e))
        except Exception:
            pass
        sys.exit(1)
