# JD2022 Legacy MOD Playlist Manager (Internal Docs)

This document explains the runtime flow, data paths, and where to edit specific features.
Paths below are relative to app/.

## Structure
- main.py: lightweight launcher (adds src to path and runs app).
- requirements.txt: Python dependencies for the app.
- python-version.txt: Python version used for local development.
- src/app.py: application entry point.
- src/config.py: central paths, runtime folders, and asset locations.
- src/ui/windows/: top-level windows (main and dialogs).
- src/ui/controllers/: UI controllers (logic and wiring).
- src/ui/shared/: shared UI texts, dialogs, filters, delegates.
- src/ui/utils/: UI helpers.
- src/services/: data/IO services (read/write, transformation).
- src/workers/: background tasks (QThread).
- src/core/: enums and domain types.
- src/utils/: IPK/localisation/cover helpers and misc utilities.
- resources/: bundled, read-only assets shipped with the app.
	- resources/assets/: icons, binaries, and packaging configs.
	- resources/gui/: Qt Designer .ui files.
- runtime/: user/runtime data (temporary files, extracted data, logs).
	- runtime/extracted/: extracted game data.
	- runtime/temp/: intermediate temp files.
	- runtime/logs/: application logs.
- output/: export output.
- patch_nx_backups/: backup IPK files.

## Key Links
- Entry point: [app.py](app.py)
- Main window: [ui/windows/main_window.py](ui/windows/main_window.py)
- Playlist window: [ui/windows/playlist_window.py](ui/windows/playlist_window.py)
- Section window: [ui/windows/section_window.py](ui/windows/section_window.py)
- Controllers: [ui/controllers](ui/controllers)
- Shared UI: [ui/shared](ui/shared)
- Services: [services](services)
- Workers: [workers](workers)
- Enums: [core/enums.py](core/enums.py)

## Runtime Flow (files → data → UI)
1. src/app.py creates the main window and calls `MainWindow.begin()`.
2. ui/controllers/load_controller.py prompts for input and starts `DataLoadWorker`.
3. workers/data_load_worker.py reads files from the mod and writes temporary JSON to runtime/.
4. services/data_service.py parses the JSON and returns normalized structures.
5. ui/controllers/songs_table_controller.py and locales_controller.py populate tables.
6. ui/controllers/playlists_tree_controller.py builds the tree model.
7. ui/controllers/save_controller.py writes changes back to output/ and backups.

## Data Paths (important)
- Bundled assets: resources/assets (read-only).
	- default_cover.png is used by Playlist window.
	- xtx_extract.exe and texconv.exe are used for playlist cover conversion.
	- justdance2026mode.act.ckd is the base ACT template for cover generation.
	- config_ipk_packer.json is the default config used by the IPK tooling.
- GUI layouts: resources/gui (read-only).
- Runtime data: runtime/ (volatile).
  - extracted/ and temp/ hold intermediate data.
  - logs/ stores logs.
- Output: output/ and patch_nx_backups/.

## Config and Paths (src/config.py)
- Uses a portable runtime root: when frozen, runtime/ is next to the .exe; otherwise, it is app/runtime.
- Creates all runtime directories on startup (`setup_directories`).
- Input root (`INPUT_MOD_ROOT_DIR`) is set by the UI; patch_nx.ipk and extracted file paths are derived from it.
- Centralizes paths to external tools in resources/assets (texconv.exe, xtx_extract.exe, base ACT, config_ipk_packer.json).
- Runtime temp folders: localisation JSON, playlist cover PNGs, and extraction folders.

## Utilities (src/utils)
- ipk_manager.py: pack/extract .ipk files (merged/extended UbiArt tools). Used by load/save flows.
- localisation.py: loc8 ↔ JSON conversion (supports legacy mode). Used during load/save.
- playlist_covers.py: converts PNG covers to DDS → TGA.CKD and builds ACT.CKD; also extracts TGA.CKD to PNG for previews.
- utils.py: cover path resolution and 17-char name normalization helpers.
- act.py: standalone dev script for editing ACT.CKD name/CRC (not used in app runtime).

## Services and Workers
- services/data_service.py: core data pipeline (extracts IPKs, converts covers, loads songs/locales/playlists).
- services/save_service.py: save pipeline (delete pending covers → generate covers → write loc8 → save playlists → repack IPK).
- workers/data_load_worker.py: background load stages for LoadMode (`json`, `extracted`, `ipk`).
- workers/save_worker.py: background save runner with cancel support.

## GUI Layout Files (resources/gui)
- mainWindow.ui: main app layout, including playlists tree, songs/locales tables, and search inputs.
- playlistWindow.ui: playlist editor dialog (ID, title/description IDs, cover path, and cover preview).
- sectionWindow.ui: section editor dialog (title ID + text).

## Quick Cheatsheet ("where do I change X?")
- Change main UI wiring: src/ui/windows/main_window.py
- Playlist/Section dialogs: src/ui/windows/playlist_window.py, src/ui/windows/section_window.py
- Playlist tree behavior (drag/drop, selection): src/ui/controllers/playlists_tree_controller.py
- Songs table (filter/sort/selection): src/ui/controllers/songs_table_controller.py
- Locales table (filter/edit/sort): src/ui/controllers/locales_controller.py
- Load/import flow: src/ui/controllers/load_controller.py and src/workers/data_load_worker.py
- Save/export flow: src/ui/controllers/save_controller.py and src/services/save_service.py
- Data parsing/transforms: src/services/data_service.py
- Shared UI texts: src/ui/shared/texts.py
- Shared dialogs: src/ui/shared/dialogs.py
- UI delegates/filters: src/ui/shared/delegates.py and src/ui/shared/filters.py

## Maintenance Tips (devs)
- When you add or remove third-party imports, update requirements.txt.
- When you change Python versions locally, update python-version.txt.
- Keep runtime/ and output/ clean in the repo (they are runtime artifacts, not source).
- If you edit resources/gui .ui files, validate the UI wiring in the matching window/controller.
- Review runtime/logs when debugging issues before changing core logic.
- Backup IPK handling lives in patch_nx_backups/; avoid deleting files unless you intend to reset history.

## Build and Automated Release

### Automated Release via GitHub Actions

This project uses GitHub Actions and cx_Freeze to automate builds and releases whenever a new version tag (`v*`) is pushed to the repository. The workflow ensures a clean environment, reproducible builds, and provides an official SHA-256 checksum for each release.

**How to trigger a release:**
1. Make sure all your changes are committed and pushed to the main branch.
2. Create and push a new version tag:
	```powershell
	git tag v1.0.0
	git push origin v1.0.0
	```

3. GitHub Actions will automatically:
		- Install Python 3.10 and all dependencies (including cx_Freeze, zstandard, pyside6).
		- Build the application using cx_Freeze, placing all required files and folders in the root of the release folder.
		- Ensure the `runtime/songs.json` file is present in the correct location.
		- Package everything into `JD2022LMPlaylistManager.zip` with the following structure:
			- JD2022LMPlaylistManager/JD2022LMPlaylistManager.exe
			- JD2022LMPlaylistManager/runtime/songs.json
			- JD2022LMPlaylistManager/resources/
			- JD2022LMPlaylistManager/src/
			- (other required files/folders)
		- Generate the SHA-256 hash of the ZIP and attach it to the release.
		- Publish a new GitHub Release with the ZIP and the hash for verification.

**What is included in the release:**
- `JD2022LMPlaylistManager.exe` (main executable, at the root of the folder)
- `runtime/` folder containing only `songs.json`
- `resources/`, `src/`, and other required folders

**How to install:**
1. Download and extract the `JD2022LMPlaylistManager.zip` file from the corresponding Release.
2. The folder structure should be:
		- JD2022LMPlaylistManager/JD2022LMPlaylistManager.exe
		- JD2022LMPlaylistManager/runtime/songs.json
		- JD2022LMPlaylistManager/resources/
		- JD2022LMPlaylistManager/src/
3. Run `JD2022LMPlaylistManager.exe`.

### Manual Build (Local)

If you want to build locally, navigate to the `app` folder and run:

```powershell
# Install dependencies
pip install -r requirements.txt

# Build with cx_Freeze
python setup.py build

# The output will be in app/build_output/
# Copy the contents to your release folder as:
# JD2022LMPlaylistManager/JD2022LMPlaylistManager.exe
# JD2022LMPlaylistManager/runtime/songs.json
# JD2022LMPlaylistManager/resources/
# JD2022LMPlaylistManager/src/
```

---

## Security & Integrity Verification

To ensure the file you downloaded is authentic and has not been tampered with, compare the SHA-256 hash of the downloaded ZIP with the hash published in the corresponding GitHub Release.

### How to verify on Windows (PowerShell)

1. Open PowerShell in the folder where the downloaded `.zip` file is located.
2. Run:
	```powershell
	Get-FileHash ./JD2022LMPlaylistManager.zip -Algorithm SHA256
	```
3. Compare the displayed hash with the hash listed in the corresponding Release section on GitHub.

---


## Distribution Note

The distributed ZIP file contains:
- `JD2022LMPlaylistManager.exe` (main executable)
- `runtime/songs.json`
- `resources/`, `src/`, and other required folders

All other required folders (`output/`, `patch_nx_backups/`, `runtime/logs`, etc.) are automatically created by the application on first launch.

**Important:** Always extract the entire ZIP contents to a folder before running the application. The application will create any missing folders on first launch.