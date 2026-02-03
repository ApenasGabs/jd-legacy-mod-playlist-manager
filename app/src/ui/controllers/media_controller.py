import logging
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QVBoxLayout, QTableWidgetItem

from ..shared import texts
from ..shared.dialogs import show_info, show_error


class MediaController:
    def __init__(self, main_window):
        self.main = main_window

        # Debounce rapid audio switches (prevents device-in-use on fast clicks)
        self._pending_audio_request = None
        self._audio_request_id = 0
        self._audio_switch_timer = QTimer(self.main)
        self._audio_switch_timer.setSingleShot(True)
        self._audio_switch_timer.timeout.connect(self.execute_audio_play_request)

        # Force reinit after device switch (headsets can keep device busy)
        self.force_audio_output_reinit = False

        # Media state
        self.media_player = None
        self.audio_output = None
        self.video_widget = None
        self.current_media_path = None
        self.is_playing = False
        self.user_is_seeking = False
        self.seek_to_middle_on_load = False
        self.defer_video_autoplay = False
        self.pending_midpoint_seek = False
        self.pending_seek_position = 0
        self.play_after_seek = False
        self.audio_retry_count = 0
        self.max_audio_retries = 3
        self.last_default_audio_device_id = None
        self.audio_device_timer = None
        self.media_devices = None

    def init_audio_player(self):
        """Initialize the audio player with QMediaPlayer and QAudioOutput"""
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)

        # Video output inside placeholder widget
        self.video_widget = QVideoWidget(self.main.ui.wdVideo)
        video_layout = QVBoxLayout(self.main.ui.wdVideo)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(self.video_widget)
        self.video_widget.setVisible(False)

        # Store current audio state
        self.current_media_path = None
        self.is_playing = False
        self.user_is_seeking = False
        self.seek_to_middle_on_load = False
        self.defer_video_autoplay = False
        self.pending_midpoint_seek = False
        self.pending_seek_position = 0
        self.play_after_seek = False
        self.audio_retry_count = 0
        self.max_audio_retries = 3
        self.last_default_audio_device_id = None

        # Connect player signals
        self.media_player.positionChanged.connect(self.on_audio_position_changed)
        self.media_player.durationChanged.connect(self.on_audio_duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.errorOccurred.connect(self.on_audio_error)

        # Track Windows default audio device changes
        try:
            self.media_devices = QMediaDevices()
            if hasattr(self.media_devices, "defaultAudioOutputChanged"):
                self.media_devices.defaultAudioOutputChanged.connect(self.on_default_audio_output_changed)
            else:
                logging.warning("QMediaDevices.defaultAudioOutputChanged is not available in this PySide6 version.")
        except Exception as e:
            logging.exception(f"Failed to init media devices watcher: {e}")

        # Polling fallback to detect default device changes
        try:
            self.audio_device_timer = QTimer(self.main)
            self.audio_device_timer.setInterval(1000)
            self.audio_device_timer.timeout.connect(self.poll_default_audio_output)
            self.audio_device_timer.start()
        except Exception as e:
            logging.exception(f"Failed to start audio device polling: {e}")

    def set_playback_controls_enabled(self, enabled: bool):
        """Enable/disable playback controls"""
        try:
            self.main.ui.btnPlay.setEnabled(enabled)
            self.main.ui.sldTimeline.setEnabled(enabled)
        except Exception as e:
            logging.exception(f"Error toggling playback controls: {e}")

    def reset_media_player(self, for_video=False):
        """Stop current playback and release previous media buffers to avoid leaks"""
        try:
            self.seek_to_middle_on_load = False
            self.defer_video_autoplay = False
            self.pending_midpoint_seek = False
            self.pending_seek_position = 0
            self.play_after_seek = False
            self.audio_retry_count = 0
            self.media_player.stop()
            # Detach previous source to release buffers
            self.media_player.setSource(QUrl())
            if for_video:
                self.media_player.setVideoOutput(self.video_widget)
                self.video_widget.setVisible(True)
            else:
                # Detach video surface when playing audio to free video buffers
                self.media_player.setVideoOutput(None)
                self.clear_video_output()
            # Reset timeline visuals
            self.main.ui.sldTimeline.setValue(0)
            self.main.ui.lblTime.setText(texts.TIME_ZERO)
            self.main.ui.lblPlayingNow.setText("")
            self.set_playback_controls_enabled(False)
        except Exception as e:
            logging.exception(f"Error resetting media player: {e}")

    def wrap_text(self, text, width=65):
        """Break long text into multiple lines for label visibility"""
        if not text:
            return ""
        text = str(text)
        lines = []
        while len(text) > width:
            lines.append(text[:width])
            text = text[width:]
        if text:
            lines.append(text)
        return "\n".join(lines)

    def _is_playback_allowed(self):
        return bool(getattr(self.main, "media_enabled", True)) and not bool(
            getattr(self.main, "use_songs_json", False)
        )

    def on_btnPlay_clicked(self):
        """Handle Play/Pause button click"""
        try:
            if not self._is_playback_allowed():
                return
            logging.info(f"Play button clicked (is_playing={self.is_playing})")
            if not self.current_media_path:
                show_info(self.main, texts.NO_MEDIA_SELECTED_TITLE, texts.NO_MEDIA_SELECTED)
                return

            if self.is_playing:
                # Pause
                self.media_player.pause()
                self.is_playing = False
                self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)
            else:
                # Resume or Play
                is_video = self.video_widget.isVisible()
                logging.debug(f"Play request media_type={'video' if is_video else 'audio'}")

                if not is_video:
                    self.refresh_default_audio_output()

                # If a video is pending midpoint seek and duration is not ready, wait
                if is_video and self.seek_to_middle_on_load and self.media_player.duration() == 0:
                    self.defer_video_autoplay = True
                    return

                # If duration is known, jump to midpoint before playing
                if is_video and self.seek_to_middle_on_load and self.media_player.duration() > 0:
                    midpoint = self.media_player.duration() // 2
                    self.media_player.setPosition(midpoint)
                    self.main.ui.sldTimeline.blockSignals(True)
                    self.main.ui.sldTimeline.setValue(midpoint)
                    self.main.ui.sldTimeline.blockSignals(False)
                    self.seek_to_middle_on_load = False
                    self.defer_video_autoplay = False

                self.media_player.play()
                self.is_playing = True
                self.main.ui.btnPlay.setText(texts.BUTTON_PAUSE)

        except Exception as e:
            logging.exception(f"Error toggling play/pause: {e}")
            show_error(self.main, texts.TITLE_PLAYBACK_ERROR, texts.PLAYBACK_ERROR_CONTROL.format(error=e))

    def on_sldTimeline_moved(self, position):
        """Handle slider movement for seeking"""
        try:
            logging.debug(f"Timeline slider moved to position={position}")
            self.user_is_seeking = True
            self.media_player.setPosition(position)
            self.user_is_seeking = False
        except Exception as e:
            logging.exception(f"Error seeking audio: {e}")
            self.user_is_seeking = False

    def on_audio_position_changed(self, position):
        try:
            if not self.user_is_seeking:
                # Update slider position (don't block signals)
                self.main.ui.sldTimeline.blockSignals(True)
                self.main.ui.sldTimeline.setValue(position)
                self.main.ui.sldTimeline.blockSignals(False)

            # Update time label in MM:SS format
            total_ms = position
            minutes = (total_ms // 1000) // 60
            seconds = (total_ms // 1000) % 60
            self.main.ui.lblTime.setText(f"{minutes:02d}:{seconds:02d}")

        except Exception as e:
            logging.exception(f"Error updating playback position: {e}")

    def on_audio_duration_changed(self, duration):
        """Update slider max when media duration is known; seek videos to midpoint always, audio to midpoint if > 60s"""
        try:
            self.main.ui.sldTimeline.setMaximum(duration)

            # Determine if we should seek to midpoint
            is_video = self.video_widget.isVisible()
            should_seek_video = self.seek_to_middle_on_load and duration > 0 and is_video
            should_seek_audio = self.seek_to_middle_on_load and duration > 60000 and not is_video

            if should_seek_video or should_seek_audio:
                midpoint = duration // 2
                self.pending_seek_position = midpoint
                self.pending_midpoint_seek = True

                # Avoid starting at 0 before seek; play only after seek
                self.play_after_seek = self.defer_video_autoplay
                self.media_player.pause()
                self.is_playing = False
                self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)

                # Schedule the seek to happen shortly after, allowing media player to be ready
                QTimer.singleShot(100, self.apply_pending_seek)

                # One-shot flags cleared after applying seek
                self.seek_to_middle_on_load = False
                self.defer_video_autoplay = False
            elif self.seek_to_middle_on_load and not is_video and duration <= 60000:
                # Audio is shorter than 1 minute, just play it from the start
                if self.defer_video_autoplay:
                    self.media_player.play()
                    self.is_playing = True
                    self.main.ui.btnPlay.setText(texts.BUTTON_PAUSE)
                else:
                    self.media_player.pause()
                    self.is_playing = False
                    self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)

                # Clear one-shot flags
                self.seek_to_middle_on_load = False
                self.defer_video_autoplay = False
        except Exception as e:
            logging.exception(f"Error handling media duration change: {e}")

    def apply_pending_seek(self):
        """Apply the pending midpoint seek after media player is ready"""
        try:
            if self.pending_midpoint_seek and self.pending_seek_position > 0:
                self.user_is_seeking = True
                self.media_player.setPosition(self.pending_seek_position)
                self.main.ui.sldTimeline.blockSignals(True)
                self.main.ui.sldTimeline.setValue(self.pending_seek_position)
                self.main.ui.sldTimeline.blockSignals(False)
                self.user_is_seeking = False
                self.pending_midpoint_seek = False
                if self.play_after_seek:
                    self.media_player.play()
                    self.is_playing = True
                    self.main.ui.btnPlay.setText(texts.BUTTON_PAUSE)
                self.play_after_seek = False
        except Exception as e:
            logging.exception(f"Error applying pending seek: {e}")

    def on_playback_state_changed(self, state):
        """Sync UI with playback state"""
        try:
            if state == QMediaPlayer.PlayingState:
                self.is_playing = True
                self.main.ui.btnPlay.setText(texts.BUTTON_PAUSE)
            elif state == QMediaPlayer.PausedState:
                self.is_playing = False
                self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)
            elif state == QMediaPlayer.StoppedState:
                self.is_playing = False
                self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)
                self.main.ui.lblTime.setText(texts.TIME_ZERO)
                self.main.ui.sldTimeline.setValue(0)
                self.main.ui.lblPlayingNow.setText("")
                self.set_playback_controls_enabled(False)
        except Exception as e:
            logging.exception(f"Error handling playback state: {e}")

    def on_audio_error(self, error):
        """Display and log media errors inline"""
        try:
            message = self.media_player.errorString() or str(error)
            if self.is_audio_device_invalidated(message):
                if self.retry_audio_playback():
                    return

                if self.audio_retry_count >= self.max_audio_retries:
                    error_text = texts.PLAYBACK_ERROR_TOO_MANY_RETRIES.format(
                        retries=self.max_audio_retries,
                        path=self.current_media_path,
                    )
                    try:
                        raise RuntimeError(error_text)
                    except RuntimeError:
                        logging.exception(error_text)
                    show_error(self.main, texts.TITLE_PLAYBACK_ERROR, error_text)

            formatted = self.wrap_text(texts.PLAYBACK_ERROR_LABEL.format(message=message))
            self.main.ui.lblImg.setText(formatted)
            logging.error(formatted)
            self.set_playback_controls_enabled(False)
        except Exception as e:
            logging.exception(f"Error handling audio error: {e}")

    def is_audio_device_invalidated(self, message: str) -> bool:
        """Check if the error indicates an invalidated audio device"""
        if not message:
            return False
        msg = message.lower()
        return (
            "audclnt_e_device_invalidated" in msg
            or "device invalidated" in msg
            or "audclnt_e_device_in_use" in msg
            or "device in use" in msg
        )

    def retry_audio_playback(self) -> bool:
        """Attempt to reinitialize audio output and retry playback"""
        if not self.current_media_path:
            return False

        if self.audio_retry_count >= self.max_audio_retries:
            return False

        self.audio_retry_count += 1
        logging.warning(
            f"Audio device invalidated. Retrying playback ({self.audio_retry_count}/{self.max_audio_retries})."
        )

        if not self.reinit_audio_output():
            return False

        try:
            last_position = self.media_player.position()
            self.media_player.stop()

            # Delay to allow audio device to release before re-opening
            def _retry():
                try:
                    self.media_player.setSource(QUrl.fromLocalFile(self.current_media_path))
                    if last_position > 0:
                        self.media_player.setPosition(last_position)
                    self.media_player.play()
                except Exception as e:
                    logging.exception(f"Retry playback failed: {e}")
            QTimer.singleShot(150, _retry)
            return True
        except Exception as e:
            logging.exception(f"Retry playback failed: {e}")
            return False

    def reinit_audio_output(self) -> bool:
        """Recreate QAudioOutput and rebind it to the media player"""
        try:
            self.audio_output = QAudioOutput()
            try:
                default_device = QMediaDevices.defaultAudioOutput()
                if default_device and default_device.isNull() is False:
                    self.audio_output.setDevice(default_device)
                    try:
                        self.last_default_audio_device_id = default_device.id()
                    except Exception:
                        self.last_default_audio_device_id = None
            except Exception as e:
                logging.exception(f"Failed to set default audio device: {e}")
            self.media_player.setAudioOutput(self.audio_output)
            self.apply_current_volume()
            return True
        except Exception as e:
            logging.exception(f"Failed to reinitialize audio output: {e}")
            return False

    def apply_current_volume(self):
        """Apply the current volume slider value to the audio output."""
        try:
            if not self.audio_output:
                return
            volume_controller = getattr(self.main, "volume_controller", None)
            if not volume_controller:
                return
            volume = volume_controller.get_volume()
            self.audio_output.setVolume(volume)
        except Exception as e:
            logging.exception(f"Failed to apply current volume: {e}")

    def refresh_default_audio_output(self):
        """Refresh audio output device to the current Windows default"""
        try:
            default_device = QMediaDevices.defaultAudioOutput()
            if not default_device or default_device.isNull():
                return

            # If no audio output exists, recreate it
            if not hasattr(self, "audio_output") or self.audio_output is None:
                self.reinit_audio_output()
                return

            # Rebind device to current default
            self.audio_output.setDevice(default_device)
            self.media_player.setAudioOutput(self.audio_output)
            self.apply_current_volume()
            try:
                self.last_default_audio_device_id = default_device.id()
            except Exception:
                self.last_default_audio_device_id = None
        except Exception as e:
            logging.exception(f"Failed to refresh default audio output: {e}")

    def on_default_audio_output_changed(self, device):
        """Handle Windows default audio device change"""
        try:
            if not device or device.isNull():
                return
            if not hasattr(self, "audio_output") or self.audio_output is None:
                self.reinit_audio_output()
                return
            self.audio_output.setDevice(device)
            self.media_player.setAudioOutput(self.audio_output)
            self.apply_current_volume()
            try:
                self.last_default_audio_device_id = device.id()
            except Exception:
                self.last_default_audio_device_id = None
            # Force reinit on next playback to avoid device-in-use on headsets
            self.force_audio_output_reinit = True
            logging.info("Default audio output changed. Switched device without stopping playback.")
        except Exception as e:
            logging.exception(f"Failed to switch default audio output: {e}")

    def poll_default_audio_output(self):
        """Polling fallback for default audio output changes"""
        try:
            default_device = QMediaDevices.defaultAudioOutput()
            if not default_device or default_device.isNull():
                return

            device_id = None
            try:
                device_id = default_device.id()
            except Exception:
                device_id = None

            if device_id != self.last_default_audio_device_id:
                self.refresh_default_audio_output()
        except Exception as e:
            logging.exception(f"Failed to poll default audio output: {e}")

    def create_tblSongs_play_item(self):
        """Create the Play column item with centered alignment."""
        item = QTableWidgetItem(texts.SONGS_PLAY_ICON)
        item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        return item

    def handle_tblSongs_play_click(self, row):
        """Handle play click without affecting selection state."""
        if not self._is_playback_allowed():
            return
        logging.info("Songs table action: play audio (play column)")
        self.play_audio_for_row(row)

    def on_tblSongs_cell_clicked(self, row, column):
        """Handle clicks: column 0 plays audio; other columns load video or range-select with Shift"""
        # Track last clicked row for debug shortcut
        self.main.last_click_source = "tblSongs"
        self.main.last_clicked_tblSongs_row = row
        # Check if Shift is pressed for range selection
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QItemSelection, QItemSelectionModel

        modifiers = QApplication.keyboardModifiers()
        logging.info(f"Songs table click: row={row}, column={column}, shift={modifiers == Qt.ShiftModifier}")

        if column == 0:
            # Play column handled separately; do not affect selection anchor
            self.handle_tblSongs_play_click(row)
            return

        if modifiers == Qt.ShiftModifier and self.main.tblSongs_shift_active:
            # Range selection with Shift - select only visible rows in range
            visible_rows = [
                r for r in range(self.main.ui.tblSongs.rowCount())
                if not self.main.ui.tblSongs.isRowHidden(r)
            ]
            if not visible_rows:
                return

            anchor = self.main.tblSongs_shift_anchor_row
            if anchor is None:
                anchor = self.main.tblSongs_last_selected_row if self.main.tblSongs_last_selected_row is not None else row
                self.main.tblSongs_shift_anchor_row = anchor

            try:
                start_index = visible_rows.index(anchor)
                end_index = visible_rows.index(row)
            except ValueError:
                logging.debug("Shift selection anchor not visible; falling back to single selection")
                self.main.tblSongs_shift_anchor_row = row
                self.main.tblSongs_last_selected_row = row
                self.load_video_for_row(row)
                return

            start_index, end_index = sorted((start_index, end_index))

            selection = QItemSelection()
            for r in visible_rows[start_index:end_index + 1]:
                top_left = self.main.ui.tblSongs.model().index(r, 0)
                bottom_right = self.main.ui.tblSongs.model().index(r, self.main.ui.tblSongs.columnCount() - 1)
                selection.select(top_left, bottom_right)

            self.main.ui.tblSongs.selectionModel().clearSelection()
            self.main.ui.tblSongs.selectionModel().select(selection, QItemSelectionModel.ClearAndSelect)
            logging.debug(
                f"Selected visible range: rows {visible_rows[start_index]} to {visible_rows[end_index]}"
            )
        else:
            # Normal click - play audio/video based on column
            logging.info("Songs table action: load video")
            self.load_video_for_row(row)

            # Track this as the last selected row for Shift+Click
            self.main.tblSongs_last_selected_row = row
            self.main.tblSongs_shift_anchor_row = None

    def on_tblSongs_current_cell_changed(self, current_row, current_column, previous_row, previous_column):
        """Update media when navigating tblSongs with keyboard."""
        try:
            if current_row is None or current_row < 0:
                return
            if not self._is_playback_allowed():
                return
            from PySide6.QtWidgets import QApplication
            if QApplication.mouseButtons() != Qt.NoButton:
                return
            # Only react when the row changes (avoid restarts on left/right)
            if current_row == previous_row:
                return
            logging.info(f"Songs table keyboard navigation: row={current_row}, column={current_column}")
            self.load_video_for_row(current_row)
            self.main.tblSongs_last_selected_row = current_row
        except Exception as e:
            logging.exception(f"Error handling tblSongs current cell change: {e}")

    def start_audio_playback(self, found_path, song_data):
        """Configure player source and UI for audio playback."""
        try:
            self.audio_retry_count = 0
            # Always recreate audio output before opening new stream (reduces headset device-in-use)
            self.reinit_audio_output()
            self.force_audio_output_reinit = False
            self.current_media_path = found_path
            self.media_player.setSource(QUrl.fromLocalFile(found_path))
            # Nudge position to initialize audio client (helps headsets)
            self.media_player.setPosition(0)
            self.set_playback_controls_enabled(True)

            # Show path in label with wrapping
            formatted_path = self.wrap_text(found_path)
            self.main.ui.lblImg.setWordWrap(True)
            self.main.ui.lblImg.setText(texts.MEDIA_AUDIO_PATH_LABEL.format(path=formatted_path))

            # Update now playing label
            self.main.ui.lblPlayingNow.setText(
                texts.NOW_PLAYING_AUDIO.format(
                    code=song_data.get("CodeName", ""),
                    title=song_data.get("Title", ""),
                    artist=song_data.get("Artist", ""),
                )
            )

            # Prepare to seek to midpoint if audio duration > 1 minute once duration is available
            self.seek_to_middle_on_load = True
            self.defer_video_autoplay = True  # Always auto-play audio once loaded and mid-seeked

            # Keep paused until duration arrives and midpoint seek is applied
            self.media_player.pause()
            self.is_playing = False
            self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)
            logging.info(f"Audio loaded, will seek to midpoint if duration > 60s: {found_path}")
        except Exception as e:
            logging.exception(f"Error starting audio playback: {e}")
            self.main.ui.lblImg.setText(self.wrap_text(texts.PLAYBACK_ERROR_AUDIO_LABEL.format(error=e)))

    def queue_audio_play(self, found_path, song_data):
        """Queue audio playback to debounce rapid clicks."""
        self._audio_request_id += 1
        request_id = self._audio_request_id
        self._pending_audio_request = (request_id, found_path, song_data)
        # Restart debounce timer
        self._audio_switch_timer.start(200)

    def execute_audio_play_request(self):
        """Execute the last queued audio request after debounce delay."""
        if not self._pending_audio_request:
            return
        request_id, found_path, song_data = self._pending_audio_request
        self._pending_audio_request = None

        # Reset player to release previous buffers, then load and play audio
        self.reset_media_player(for_video=False)

        # Extra delay to allow device to release (headsets can be slower)
        def _start_if_latest():
            if request_id != self._audio_request_id:
                return
            self.start_audio_playback(found_path, song_data)

        QTimer.singleShot(250, _start_if_latest)

    def play_audio_for_row(self, row):
        """Play audio for the given row, trying all available audio paths"""
        try:
            if not self._is_playback_allowed():
                return
            # Clear video visual when switching to audio
            self.clear_video_output()

            code_item = self.main.ui.tblSongs.item(row, 1)
            if not code_item:
                return

            song_data = code_item.data(Qt.UserRole)
            if not song_data:
                return

            audio_paths = song_data.get("AudioFilePaths", [])
            if not audio_paths or not any(audio_paths):
                message = texts.MEDIA_AUDIO_NOT_FOUND
                self.main.ui.lblImg.setText(self.wrap_text(message))
                logging.error(message)
                self.set_playback_controls_enabled(False)
                return

            found_path = None
            failed_paths = []

            for audio_path in audio_paths:
                if not audio_path or not audio_path.strip():
                    continue
                candidate = audio_path.strip()
                if Path(candidate).exists():
                    found_path = candidate
                    break
                failed_paths.append(candidate)

            if not found_path:
                error_lines = [texts.MEDIA_AUDIO_FILE_NOT_FOUND] + [self.wrap_text(p) for p in failed_paths]
                error_text = "\n".join(error_lines)
                self.main.ui.lblImg.setText(error_text)
                logging.error(error_text)
                self.set_playback_controls_enabled(False)
                return

            # Debounce rapid switches to avoid device-in-use errors
            self.queue_audio_play(found_path, song_data)

        except Exception as e:
            logging.exception(f"Error playing audio: {e}")
            self.main.ui.lblImg.setText(self.wrap_text(texts.PLAYBACK_ERROR_AUDIO_LABEL.format(error=e)))

    def load_video_for_row(self, row):
        """Load (and optionally autoplay) the video for the given row"""
        try:
            if not self._is_playback_allowed():
                return
            code_item = self.main.ui.tblSongs.item(row, 1)
            if not code_item:
                return

            song_data = code_item.data(Qt.UserRole)
            if not song_data:
                return

            video_path = song_data.get("VideoFilePath", "")
            self.main.ui.lblImg.setText("")  # Clear image label for video load

            if not video_path or not Path(video_path).exists():
                error_text = self.wrap_text(texts.MEDIA_VIDEO_NOT_FOUND.format(path=video_path))
                self.main.ui.lblImg.setText(error_text)
                logging.error(error_text)
                self.set_playback_controls_enabled(False)
                return

            # Reset player to release previous buffers, then prepare video output
            self.reset_media_player(for_video=True)

            self.current_media_path = video_path
            self.media_player.setSource(QUrl.fromLocalFile(video_path))
            self.media_player.setPosition(0)
            self.set_playback_controls_enabled(True)

            autoplay = self.main.ui.chkAutoplayVideo.isChecked()
            # Prepare midpoint seek once duration is available
            self.seek_to_middle_on_load = True
            self.defer_video_autoplay = autoplay

            # Keep paused until midpoint seek is applied
            self.media_player.pause()
            self.is_playing = False
            self.main.ui.btnPlay.setText(texts.BUTTON_PLAY)

            # Reset timeline visuals
            self.main.ui.sldTimeline.setValue(0)
            self.main.ui.lblTime.setText(texts.TIME_ZERO)

            # Update now playing label
            self.main.ui.lblPlayingNow.setText(
                texts.NOW_PLAYING_VIDEO.format(
                    code=song_data.get("CodeName", ""),
                    title=song_data.get("Title", ""),
                    artist=song_data.get("Artist", ""),
                )
            )

            logging.info(f"Video loaded (autoplay={'on' if autoplay else 'off'}), will seek to midpoint: {video_path}")

        except Exception as e:
            logging.exception(f"Error loading video: {e}")
            self.main.ui.lblImg.setText(self.wrap_text(texts.PLAYBACK_ERROR_VIDEO_LABEL.format(error=e)))

    def clear_video_output(self):
        """Hide video widget when switching back to audio"""
        try:
            if self.video_widget:
                self.video_widget.setVisible(False)
        except Exception as e:
            logging.exception(f"Error hiding video widget: {e}")
