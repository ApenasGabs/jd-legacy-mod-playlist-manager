import logging

from PySide6.QtCore import QObject, QEvent
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QToolTip


class VolumeController(QObject):
    """Controls playback volume via sldVolume."""

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window
        self._volume = 0.4

    def initialize(self):
        slider = getattr(self.main.ui, "sldVolume", None)
        if not slider:
            return
        try:
            slider.setRange(0, 100)
            slider.setSingleStep(1)
            slider.setPageStep(10)
            slider.setValue(int(self._volume * 100))
            slider.valueChanged.connect(self.on_volume_changed)
            slider.valueChanged.connect(self._update_tooltip)
            slider.setMouseTracking(True)
            slider.installEventFilter(self)
            self._update_tooltip()
            self.apply_volume(self._volume)
        except Exception as e:
            logging.exception(f"Failed to initialize volume slider: {e}")

    def on_volume_changed(self, value):
        try:
            self._volume = max(0.0, min(1.0, value / 100.0))
            self.apply_volume(self._volume)
            self._show_tooltip(value)
        except Exception as e:
            logging.exception(f"Failed to change volume: {e}")

    def eventFilter(self, obj, event):
        slider = getattr(self.main.ui, "sldVolume", None)
        if obj is slider and event.type() in (QEvent.Enter, QEvent.MouseMove):
            self._show_tooltip(slider.value())
        return False

    def _show_tooltip(self, value):
        slider = getattr(self.main.ui, "sldVolume", None)
        if not slider:
            return
        try:
            QToolTip.showText(QCursor.pos(), str(int(value)), slider)
        except Exception as e:
            logging.exception(f"Failed to show volume tooltip: {e}")

    def _update_tooltip(self):
        slider = getattr(self.main.ui, "sldVolume", None)
        if not slider:
            return
        try:
            slider.setToolTip(str(int(slider.value())))
        except Exception as e:
            logging.exception(f"Failed to update volume tooltip: {e}")

    def apply_volume(self, volume: float):
        try:
            media_controller = getattr(self.main, "media_controller", None)
            if media_controller and media_controller.audio_output:
                media_controller.audio_output.setVolume(volume)
        except Exception as e:
            logging.exception(f"Failed to apply volume: {e}")

    def get_volume(self) -> float:
        """Return the current slider volume (0.0 - 1.0)."""
        try:
            slider = getattr(self.main.ui, "sldVolume", None)
            if slider:
                self._volume = max(0.0, min(1.0, slider.value() / 100.0))
        except Exception as e:
            logging.exception(f"Failed to read volume slider: {e}")
        return self._volume

    def set_enabled(self, enabled: bool):
        slider = getattr(self.main.ui, "sldVolume", None)
        if not slider:
            return
        try:
            slider.setEnabled(enabled)
        except Exception as e:
            logging.exception(f"Failed to set volume slider enabled state: {e}")
