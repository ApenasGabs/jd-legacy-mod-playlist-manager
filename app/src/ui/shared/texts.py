"""Centralized UI text strings.

Add new dialog messages here to keep text discoverable.
"""

# Generic titles
TITLE_ERROR = "Error"
TITLE_WARNING = "Warning"
TITLE_INFO = "Information"
TITLE_CONFIRMATION = "Confirmation"
TITLE_EDIT = "Edit"
TITLE_SAVE_COMPLETED = "Save Completed"
TITLE_SELECT_MOD_FOLDER = "Select MOD Folder"
TITLE_NO_IPK_FILES = "No IPK Files Found"
TITLE_EXISTING_FILES = "Existing Files Found"
TITLE_LOAD_SONGS_DB = "Load Songs Database"
TITLE_SONGS_DATABASE = "Songs Database"
TITLE_PLAYBACK_ERROR = "Playback Error"
TITLE_FATAL_ERROR = "Fatal Error"

# App/window
APP_TITLE = "Just Dance 2022 Legacy MOD (Switch) Playlist Manager"
TREE_PLAYLIST_HEADER = "Playlist Structure"
SELECT_MOD_FOLDER_DIALOG = "Select the MOD [romfs] folder"
UNKNOWN_TEXT = "Unknown"

# Buttons
BUTTON_PLAY = "Play"
BUTTON_PAUSE = "Pause"
BUTTON_CANCEL = "Cancel"
BUTTON_REEXTRACT_ALL = "Re-extract All"
BUTTON_LOAD_EXISTING = "Load Existing"

# Placeholders
PLACEHOLDER_SEARCH_ALL = "Search in all columns..."

# Media
NO_MEDIA_SELECTED = "Please click on a song first."
NO_MEDIA_SELECTED_TITLE = "No Media Selected"
TIME_ZERO = "00:00"
NOW_PLAYING_AUDIO = "Playing Now (Audio): {code} (\"{title}\" - {artist})"
NOW_PLAYING_VIDEO = "Playing Now (Video): {code} (\"{title}\" - {artist})"
MEDIA_AUDIO_PATH_LABEL = "🎵\n{path}"
PLAYBACK_ERROR_CONTROL = "Error controlling playback: {error}"
PLAYBACK_ERROR_TOO_MANY_RETRIES = (
    "Failed to play audio file after {retries} attempts.\n"
    "File: {path}"
)
PLAYBACK_ERROR_LABEL = "❌ Playback error: {message}"
PLAYBACK_ERROR_AUDIO_LABEL = "❌ Error playing audio: {error}"
PLAYBACK_ERROR_VIDEO_LABEL = "❌ Error loading video: {error}"
MEDIA_AUDIO_NOT_FOUND = "❌ Audio paths not available for this song."
MEDIA_AUDIO_FILE_NOT_FOUND = "❌ Audio file not found. Tried:"
MEDIA_VIDEO_NOT_FOUND = "❌ Video file not found:\n{path}"

# Edit selection
EDIT_SELECT_ITEM = "Please select an item to edit."
EDIT_SELECT_SECTION_OR_PLAYLIST = "Please select a section or playlist to edit."
EDIT_OPEN_ERROR = "Error opening edit section window: {error}"

# Save
SAVE_LOADING_TITLE = "Saving files"
SAVE_LOADING_TEXT = "Saving files...\n\nPlease wait."
SAVE_TITLE_LABEL = "Saving files"
SAVE_FOOTER_TEXT = (
    "This may take a while, but it is working.\n\n"
    "Please do not close this application."
)
SAVE_CONFIRM_TITLE = "Confirm Save"
SAVE_CONFIRM_TEXT = "Do you really want to save the changes?"
SAVE_COMPLETED_TEXT = (
    "All changes have been saved successfully.\n"
    "The output patch.nx file has been created. Now you just need to copy it to your game's mods folder [romfs].\n"
    "Don't worry, your old patch_nx.ipk file has been saved in the 'patch_nx_backups' folder.\n\n"
    "Do you want to open the output folder?"
)
SAVE_ERROR_TEXT = "Error saving changes: {message}"
SAVE_ERROR_DIALOG_TITLE = "Save Error"
SAVE_ERROR_DIALOG_TEXT = (
    "An error occurred while saving. Check the logs for details. "
    "The save was cancelled."
)

# Load mode dialog
LOAD_MODE_INTRO = "Choose how you want to load the song database:"
LOAD_MODE_OPTION_JSON = "1) Use songs.json"
LOAD_MODE_OPTION_JSON_INFO = "1) Use songs.json (fastest, seconds)"
LOAD_MODE_OPTION_EXTRACTED = "2) Use extracted folder"
LOAD_MODE_OPTION_EXTRACTED_INFO = "2) Use existing extracted folder (recommended, up to 1 minute)"
LOAD_MODE_OPTION_IPK = "3) Extract IPK files"
LOAD_MODE_OPTION_IPK_INFO = "3) Extract IPK files now (slow, ~30 minutes for ~150 GB mod files)"
LOAD_MODE_CANCEL = "Cancel"
LOAD_MODE_TOP_WARNING = "PAY ATTENTION, PLEASE! Read carefully before choosing an option."
LOAD_MODE_INFO_JSON = "- Only patch_nx.ipk extracted is required. (NOTE: {patch_note})."
LOAD_MODE_INFO_JSON_1 = "- You can preview/edit playlist covers (loaded from patch_nx). Audio/video playback will not be available."
LOAD_MODE_INFO_JSON_2 = "- New songs added to the MOD will NOT appear until you update songs.json or extract all files again (the third option)."
LOAD_MODE_INFO_EXTRACTED = (
    "- Requires patch_nx.ipk and a previously extracted data/extracted folder. (NOTE: {extracted_note})."
)
LOAD_MODE_INFO_EXTRACTED_1 = "- Audio, video, and cover editing are available."
LOAD_MODE_INFO_EXTRACTED_2 = "- New songs added to the MOD will NOT appear until you extract all files again (the third option)."
LOAD_MODE_INFO_IPK = (
    "- Requires all .ipk files in the MOD folder.\n"
    "- Needs a lot of free disk space on your drive '{drive}' (about ~180 GB for ~150 GB mod files).\n"
    "- Full media features available."
    " But you just need to do this once to get everything set up! On the next runs, you can use the first or second options (recommended)."
)
LOAD_MODE_BACKUP_NOTICE = "Don't worry, regardless of the load type, your patch_nx.ipk file will be backed up on the 'patch_nx_backups' folder."
LOAD_MODE_HELP = "Need help? Please check the GitHub help page for details."
LOAD_MODE_PATCH_NOTE_HAS = "Your 'extracted' folder has patch_nx extracted"
LOAD_MODE_PATCH_NOTE_MISSING = (
    "Your 'extracted' folder does NOT have patch_nx extracted, but you can extract it using this option"
)
LOAD_MODE_EXTRACTED_NOTE_OK = "Your 'extracted' folder has patch_nx and other files extracted"
LOAD_MODE_EXTRACTED_NOTE_MISSING = (
    "Your 'extracted' folder does NOT have patch_nx and other files extracted, select the third option instead"
)

# Loading screen
LOADING_TITLE_LABEL = "Loading files"
LOADING_TITLE_WITH_MODE = "Loading files ({mode})"
LOADING_MODE_LABEL_JSON = "songs.json"
LOADING_MODE_LABEL_EXTRACTED = "extracted folder"
LOADING_MODE_LABEL_IPK = "extract IPK files"
LOADING_FOOTER_TEXT = (
    "This may take a while, but it is working.\n\n"
    "Please do not close this application."
)
LOADING_STATUS_DEFAULT = "0% - Starting..."
PROGRESS_STATUS_FORMAT = "{percent}% - {message}"
LOADING_CANCEL_CONFIRM_TITLE = "Cancel Loading"
LOADING_CANCEL_CONFIRM_TEXT = (
    "Do you really want to cancel the loading process?\n\n"
    "This will permanently delete everything inside the 'extracted' folder."
)
LOADING_CANCELING_TEXT = "Cancelling... please wait."

# Load progress messages
LOAD_PROGRESS_START = "Starting"
LOAD_PROGRESS_CLEAR_EXTRACTED = "Clearing extracted data"
LOAD_PROGRESS_EXTRACT_ALL = "Extracting IPK files"
LOAD_PROGRESS_EXTRACT_PATCH = "Extracting patch_nx"
LOAD_PROGRESS_CLEAR_TEMP = "Clearing temp data"
LOAD_PROGRESS_LOCALISATION = "Decompressing localisation"
LOAD_PROGRESS_COVERS = "Extracting playlist covers"
LOAD_PROGRESS_PRELOAD_COVERS = "Preloading playlist covers"
LOAD_PROGRESS_PRELOAD_COVERS_ITEM = "Preloading playlist covers: {name}"
LOAD_PROGRESS_PRELOAD_COVERS_ITEM_COUNT = "Preloading playlist covers ({idx}/{total}): {name}"
LOAD_PROGRESS_LOCALES = "Loading localisation"
LOAD_PROGRESS_SONGS = "Loading songs"
LOAD_PROGRESS_SAVE_SONGS = "Saving songs.json"
LOAD_PROGRESS_PLAYLISTS = "Building playlists"
LOAD_PROGRESS_DONE = "Done"

# Save progress messages
SAVE_STEP_DELETE_COVERS = "Deleting pending cover assets"
SAVE_STEP_GENERATE_COVERS = "Generating cover assets"
SAVE_STEP_SAVE_LOCALISATION = "Saving localisation"
SAVE_STEP_SAVE_PLAYLISTS = "Saving playlists"
SAVE_STEP_REPACK = "Repacking patch_nx"
SAVE_PROGRESS_DONE = "Done"
SAVE_CANCEL_CONFIRM_TITLE = "Cancel Saving"
SAVE_CANCEL_CONFIRM_TEXT = (
    "Do you really want to cancel the saving process?\n\n"
    "This will permanently delete everything inside the 'output' folder."
)
SAVE_CANCELING_TEXT = "Cancelling... please wait."

# MOD folder selection
MOD_FOLDER_PROMPT = (
    "Please select the MOD folder that contains the .ipk files.\n\n"
    "Make sure you are in the correct MOD [romfs] folder."
)
MOD_FOLDER_MISSING = "No MOD folder selected. Application will close."
NO_IPK_FILES_FOUND = (
    "No .ipk files were found in the selected folder.\n"
    "Please select the correct MOD [romfs] folder."
)
NO_IPK_FILES_FOUND_SIMPLE = "No .ipk files found in the selected MOD folder."
PATCH_NX_MISSING_CLOSE = "patch_nx.ipk not found in the selected MOD folder. Application will close."
MISSING_FILE_TITLE = "Missing File"
MISSING_SONGS_JSON = "songs.json was not found. Please choose another option."
EXTRACTED_DATA_NOT_FOUND_TITLE = "Extracted Data Not Found"
EXTRACTED_DATA_NOT_FOUND_TEXT = "No extracted folders were found. Please choose another option."
PATCH_NX_EXTRACT_CONFIRM_TITLE = "Extract patch_nx"
PATCH_NX_EXTRACT_CONFIRM_TEXT = (
    "The patch_nx folder is not extracted yet.\n\n"
    "This mode needs patch_nx extracted. Do you want to extract it now?\n\n"
    "If you choose No, you can select another load option."
)

# Extraction
PATCH_NX_NOT_FOUND = "patch_nx.ipk was not found in the selected MOD folder."
PATCH_NX_EXTRACT_FAILED = "Failed to extract patch_nx.ipk:\n{error}"
EXTRACTED_FOUND_TEXT = "Extracted folders were found from your last session."
EXTRACTED_FOUND_INFO = (
    "Do you want to RE-EXTRACT the IPKs from input folder? \n\n"
    "(Note: This will delete current modifications in extracted folder)"
)
REEXTRACT_CONFIRM_TITLE = "Delete Extracted Data"
REEXTRACT_CONFIRM_TEXT = (
    "Extracted folders already exist.\n\n"
    "Do you want to delete all extracted folders and RE-EXTRACT now?\n"
    "This could take a long time depending on the MOD size."
)
BACKUP_ERROR_TITLE = "Backup Error"
BACKUP_ERROR_TEXT = "Could not create backup of patch_nx.ipk:\n{error}"

# Songs database info
SONGS_DB_LOADED_TEXT = "The songs database was loaded from a file generated on:"
LOAD_COMPONENTS_ERROR = "An error occurred while loading components, the application will close:\n{error}"
LOAD_DATA_ERROR = "An error occurred while loading data:\n{error}"
EXTRACT_COVER_ERRORS = (
    "Errors occurred while extracting the following playlist covers and some covers may not display correctly, "
    "check logs for details:\n{errors}"
)
EXTRACT_IPK_ERRORS = "Errors occurred while extracting the following files, check logs for details:\n{errors}"

# Playlist/section dialogs
SECTION_INVALID_NAME = "Section name cannot be empty."
PLAYLIST_INVALID_ID = (
    "The chosen Playlist ID is invalid. Please use only letters and numbers, up to 17 characters."
)
PLAYLIST_DUPLICATE_ID = "This Playlist ID already exists. Please choose a different ID."
PLAYLIST_INVALID_TEXT = "Playlist title and description cannot be empty."
PLAYLIST_INVALID_COVER = "Please select a valid PNG cover image."
PLAYLIST_INVALID_IMAGE = "The selected file could not be loaded as a PNG image."
PLAYLIST_INVALID_SIZE = (
    "Invalid image size. The PNG must be exactly 1024x512.\n"
    "Please resize it in an image editor and select it again."
)
PLAYLIST_NO_SECTION = (
    "Please select a section (or a playlist/song inside a section) before adding a playlist."
)
PLAYLIST_WINDOW_LOAD_UI_ERROR = "Failed to load UI: {path}"
PLAYLIST_WINDOW_OPEN_ERROR = "Error opening playlist window: {error}"
PLAYLIST_TITLE_EDIT = "Edit Playlist"
PLAYLIST_TITLE_NEW = "New Playlist"
PLAYLIST_SELECT_COVER_TITLE = "Select PNG Cover (1024x512)"
PLAYLIST_SELECT_COVER_FILTER = "PNG Images (*.png)"
PLAYLIST_INVALID_IMAGE_TITLE = "Invalid Image"
PLAYLIST_INVALID_IMAGE_TEXT = "The selected file could not be loaded as a PNG image."
PLAYLIST_COVER_FILE_NOT_FOUND = "Selected PNG cover file was not found."
PLAYLIST_TITLE_DESC_ID_MISSING = "titleId/descriptionId are missing."
PLAYLIST_LOCALISATION_MISSING = "localisation.json was not found."
PLAYLIST_ERROR_SELECT_COVER = "Error selecting cover: {error}"
PLAYLIST_ERROR_VALIDATE_COVER = "Error validating cover: {error}"
PLAYLIST_ERROR_COPY_COVER = "Error copying cover: {error}"
PLAYLIST_ERROR_SAVE = "Error saving playlist: {error}"

SECTION_WINDOW_LOAD_UI_ERROR = "Failed to load UI: {path}"
SECTION_WINDOW_OPEN_ERROR = "Error opening section window: {error}"
SECTION_TITLE_ID_MISSING = "titleId is missing."
SECTION_LOCALISATION_MISSING = "localisation.json was not found."
SECTION_ERROR_SAVE = "Error saving section: {error}"
SECTION_TITLE_EDIT = "Edit Section"
SECTION_TITLE_NEW = "New Section"

TREE_DELETE_ERROR = "Error deleting item(s): {error}"

FATAL_ERROR_TEXT = "An unexpected error occurred:\n{error}"

DATA_PATCH_NX_NOT_FOUND = "patch_nx.ipk was not found in the selected MOD folder."
DATA_NO_IPK_FILES_FOUND = "No .ipk files found in the selected MOD folder."
DATA_EXTRACT_IPK_ERRORS = "Errors occurred while extracting the following files:\n{errors}"
DATA_SONGS_JSON_NOT_FOUND = "songs.json not found."
DATA_EMPTY_SONG_DATA = "Empty song data: {path}"
DATA_SONGS_LOAD_FAILED = (
    "❌ FAILED TO LOAD {error_count} SONG(S)\n\n"
    "Total folders analyzed: {total}\n"
    "Folders loaded successfully: {loaded}\n"
    "Folders with errors: {errors}\n\n"
    "Files with errors:\n"
    "{error_list}\n\n"
    "See the log file for complete error details."
)

TREE_DELETE_CONFIRM = (
    "You are about to delete an entire playlist/section.\n"
    "All items inside it will also be deleted.\n\n"
    "Do you want to continue?"
)
TREE_DELETE_CONFIRM_MULTI = "You are about to delete {count} item(s).\n\nDo you want to continue?"
TREE_NO_SELECTION = "No items selected in the playlists tree."

SONGS_DUPLICATE_TITLE = "Duplicate Songs Detected"
SONGS_DUPLICATE_TEXT = (
    "Some of the dragged songs are already in this playlist.\n"
    "Duplicates found: {duplicates}\n"
    "Total dragged: {total}\n\n"
    "What do you want to do?"
)
SONGS_DUPLICATE_ADD_ALL = "Add all (allow duplicates)"
SONGS_DUPLICATE_ADD_NONE = "Add none"
SONGS_DUPLICATE_ADD_UNIQUE = "Add only new songs"

SONG_NOT_FOUND_TITLE = "Song not found in the Manager's songs database"
SONG_NOT_FOUND_ACTION = "Search similar song"
SONG_NOT_FOUND_DONT_SHOW = "Don't show this message again"
SONG_NOT_FOUND_MESSAGE = (
    "The CodeName '{code}' was not found in the Manager's songs database.\n\n"
    "1. CASE-SENSITIVITY ISSUE\n"
    "Check for similar names in the 'Songs' table. For example, 'sugar' is different from 'Sugar' and 'SUGAR'. "
    "If you find the correct one, drag it on this playlist to fix the link.\n\n"
    "2. OUTDATED DATABASE\n"
    "If the song works in-game but info is missing here, restart the Manager and use 'Option 3' to re-extract all IPKs and update the database.\n\n"
    "3. CLEANUP (Recommended)\n"
    "If the CodeName is invalid or you've already linked the correct song, you should delete this entry. Keeping this entry will not crash the game "
    "(it will simply be ignored), but deleting it keeps your playlist organized."
)
SONG_NOT_FOUND_SHORT = "Song not found in the Manager's songs database"

# Counters
LOADED_SONGS_COUNT = "Loaded {count} songs"
LOADED_LOCALES_COUNT = "Loaded {count} strings"
FILTER_RESULTS_COUNT = "{count} results"
SELECTED_SONGS_COUNT = "Selected {count}"
LOADED_PLAYLISTS_COUNT = "Loaded {count} playlists"
SELECTED_PLAYLISTS_COUNT = "Selected {count}"
FILTER_PLAYLISTS_COUNT = "{count} results"

# Headers
LOCALES_HEADERS = ["ID", "Text"]
SONGS_HEADERS = ["▶️", "CodeName", "Title", "Artist", "JDVersion", "OriginalJDVersion"]
SONGS_PLAY_ICON = "▶️"

# Debug dialogs
DEBUG_TBLSONGS_TITLE = "Debug: tblSongs row"
DEBUG_TREEPLAYLISTS_TITLE = "Debug: treePlaylists item"
