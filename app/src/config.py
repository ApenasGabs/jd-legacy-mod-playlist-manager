import os
import sys
from pathlib import Path

APP_NAME = "JDLEGACY_PLAYLIST_MANAGER"
IS_FROZEN = getattr(sys, "frozen", False)

def _get_project_root():
    if IS_FROZEN:
        return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
    return Path(__file__).resolve().parent.parent

PROJECT_ROOT = _get_project_root()

# Resource directories (bundled with the app)
RESOURCES_DIR = PROJECT_ROOT / "resources"
GUI_DIR = RESOURCES_DIR / "gui"
ASSETS_DIR = RESOURCES_DIR / "assets"

def _get_portable_runtime_root():
    if IS_FROZEN:
        return Path(sys.executable).resolve().parent / "runtime"
    return PROJECT_ROOT / "runtime"

USER_DATA_DIR = _get_portable_runtime_root()

def _get_output_root():
    if IS_FROZEN:
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT

# Runtime data directories (volatile)
DATA_DIR = USER_DATA_DIR
OUTPUT_DIR = _get_output_root() / "output"
OUTPUT_PATCH_NX_FOLDER = OUTPUT_DIR
OUTPUT_PATCH_NX_FILE = OUTPUT_DIR / "patch_nx.ipk"
BKP_DIR = _get_output_root() / "patch_nx_backups"
LOGS_DIR = USER_DATA_DIR / "logs"
EXTRACTED_DIR = USER_DATA_DIR / "extracted"
TEMP_DIR = USER_DATA_DIR / "temp"

# Behaviour flags
LOCALISATION_LEGACY_ESCAPE = False

TEMP_LOCALISATION = TEMP_DIR / "localisation"
TEMP_PLAYLISTS_COVERS = TEMP_DIR / "playlists_covers"

# Treat runtime data as base for relative paths
BASE_DIR = USER_DATA_DIR

# List of all folders for automatic creation
ALL_DIRS = [
    USER_DATA_DIR,
    OUTPUT_DIR,
    BKP_DIR,
    LOGS_DIR,
    TEMP_DIR,
    EXTRACTED_DIR,
    TEMP_LOCALISATION,
    TEMP_PLAYLISTS_COVERS,
]

ALL_TEMP_DIRS = [
    TEMP_DIR, TEMP_LOCALISATION, TEMP_PLAYLISTS_COVERS
]

def setup_directories(dirs=ALL_DIRS):
    """Creates folders if they don't exist."""
    for folder in dirs:
        folder.mkdir(parents=True, exist_ok=True)

# Input
INPUT_MOD_ROOT_DIR = None # Will be defined via GUI
def set_mod_root(path):
    global INPUT_MOD_ROOT_DIR
    INPUT_MOD_ROOT_DIR = Path(path)

def get_patch_nx_path():
    if INPUT_MOD_ROOT_DIR:
        return INPUT_MOD_ROOT_DIR / "patch_nx.ipk"
    return None

# Input files within data/
INPUT_PATCH_NX_FOLDER = EXTRACTED_DIR / "patch_nx"
INPUT_LOCALISATION_FOLDER = INPUT_PATCH_NX_FOLDER / "enginedata" / "localisation"
INPUT_LOCALISATION_FILE = INPUT_LOCALISATION_FOLDER / "localisation.itf_language_english.loc8"
INPUT_GAMECONFIG_FOLDER = INPUT_PATCH_NX_FOLDER / "cache" / "itf_cooked" / "nx" / "enginedata" / "gameconfig"
INPUT_SECTIONS_FILE = INPUT_GAMECONFIG_FOLDER / "gc_carousel_rules.json.ckd"
INPUT_PLAYLISTS_FILE = INPUT_GAMECONFIG_FOLDER / "playlists.json.ckd"
INPUT_COVERS_FOLDER = INPUT_PATCH_NX_FOLDER / "cache" / "itf_cooked" / "nx" / "world" / "ui" / "textures" / "covers" / "playlists_offline"
XTX_EXTRACT_EXE = ASSETS_DIR / "xtx_extract.exe"
BASE_ACT_FILE = ASSETS_DIR / "justdance2026mode.act.ckd"
CONFIG_IPK_PACKER = ASSETS_DIR / "config_ipk_packer.json"

# Temp files
TEMP_LOCALISATION_JSON = TEMP_LOCALISATION / "localisation.json"

# Logs
import datetime
def get_log_filepath():
    """Generates the filename in format YYYYDDMM-HHMMSS.log"""
    now = datetime.datetime.now()
    filename = now.strftime("%Y%d%m-%H%M%S.log")
    return LOGS_DIR / filename