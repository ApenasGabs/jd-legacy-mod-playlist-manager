
import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but some modules need manual inclusion
"""
Build script for JD2022LMPlaylistManager using cx_Freeze.
Ensures only required files are included and all paths are in English.
"""
build_exe_options = {
    "packages": ["os", "sys", "PySide6", "shiboken6"],
    "include_files": [
        ("resources", "resources"),
        ("runtime/songs.json", "runtime/songs.json"),
        ("src", "src"),
    ],
    "excludes": [
        "tkinter", "unittest", "email", "html", "http", "xml", "pydoc_data", "test", "distutils", "setuptools"
    ],
    "bin_path_includes": [],
    "build_exe": "build_output",
    "zip_include_packages": [],
    "zip_exclude_packages": ["*"],
}

if sys.platform == "win32":
    build_exe_options["include_msvcr"] = True

base = "Win32GUI" if sys.platform == "win32" else None
target_name = "JD2022LMPlaylistManager.exe" if sys.platform == "win32" else "JD2022LMPlaylistManager"

setup(
    name="JD2022LMPlaylistManager",
    version="1.0",
    description="Just Dance 2022 Legacy MOD Playlist Manager",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            "main.py",
            base=base,
            target_name=target_name,
            icon="resources/gui/icon.ico"
        )
    ],
)
    # Additional comments can be added here if necessary