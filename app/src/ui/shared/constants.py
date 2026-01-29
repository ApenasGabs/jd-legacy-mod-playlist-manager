from enum import Enum

from PySide6.QtCore import Qt

TREE_ITEM_TYPE_ROLE = Qt.UserRole + 100
MISSING_SONG_MESSAGE_ROLE = Qt.UserRole + 101
MISSING_SONG_CODE_ROLE = Qt.UserRole + 102
SONG_CODE_ROLE = Qt.UserRole + 103
PLAYLIST_ID_ROLE = Qt.UserRole + 104
PLAYLIST_DESCRIPTION_TEXT_ROLE = Qt.UserRole + 105
PLAYLIST_COVER_PNG_PATH_ROLE = Qt.UserRole + 106
PLAYLIST_TITLE_TEXT_ROLE = Qt.UserRole + 107
SECTION_TITLE_ROLE = Qt.UserRole + 108
SECTION_TITLE_ID_ROLE = Qt.UserRole + 109


class TreeItemType(str, Enum):
	SECTION = "section"
	PLAYLIST = "playlist"
	SONG = "song"
