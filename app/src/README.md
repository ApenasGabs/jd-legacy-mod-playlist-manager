# JD2022 Legacy MOD Playlist Manager (Internal Docs)

This document explains the runtime flow, data paths, and where to edit specific features.
Paths below are relative to app/.

## Structure
- main.py: lightweight launcher (adds src to path and runs app).
- requirements.txt: Python dependencies for the app.
- python-version.txt: Python version used for local development.
- src/app.py: application entry point.
- src/ui/windows/: top-level windows (main and dialogs).
- src/ui/controllers/: UI controllers (logic and wiring).
- src/ui/shared/: shared UI texts, dialogs, filters, delegates.
- src/ui/utils/: UI helpers.
- src/services/: data/IO services (read/write, transformation).
- src/workers/: background tasks (QThread).
- src/core/: enums and domain types.
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
	- xtx_extract.exe and other tools are also here.
- GUI layouts: resources/gui (read-only).
- Runtime data: runtime/ (volatile).
  - extracted/ and temp/ hold intermediate data.
  - logs/ stores logs.
- Output: output/ and patch_nx_backups/.

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

### Automated Release via Tags

The project is configured to build, hash, and publish a release automatically using GitHub Actions whenever a new tag is pushed. This process ensures a clean environment, consistent path mapping, and rovides an official SHA-256 checksum for security.

1. Commit all your changes and ensure your code is pushed to the main branch.
2. Create and push a version tag from your terminal:
```powershell
git tag v1.0.0
git push origin v1.0.0
```

3. The GitHub Action will automatically:
- Set up the Python 3.10 environment and install dependencies.
- Compile the binary using Nuitka with optimized flags.
- Bundle the 'JD2022LMPlaylistManager.exe' and the 'runtime/songs.json' folder into a ZIP archive.
- Generate a SHA-256 checksum.
- Create a new GitHub Release containing the ZIP and the verification hash.

### Manual Compilation (Local)

If you need to build the executable locally, navigate to the 'app' folder and execute the following command in PowerShell:

```powershell
# Set PYTHONPATH to include the src directory
$env:PYTHONPATH="src"

# Run Nuitka compilation
python -m nuitka --standalone --onefile --mingw64 --show-progress --windows-console-mode=disable --plugin-enable=pyside6 --include-package=core --include-package=services --include-package=ui -include-package=utils --include-package=workers --include-data-dir=resources=resources --include-data-dir=src=src --windows-icon-from-ico=resources/gui/icon.ico --output-filename=JD2022LMPlaylistManager -assume-yes-for-downloads --quiet --remove-output --no-deployment-flag=self-execution main.py
```

---

## Security & Integrity Verification

To ensure the file you downloaded is authentic and has not been altered, you should compare its hash with the one provided in the official GitHub Release notes.

### How to verify on Windows (PowerShell)

1. Open PowerShell in the folder where the .zip file is located.
2. Run the following command:

```powershell
Get-FileHash ./JD2022LMPlaylistManager.zip -Algorithm SHA256
```

3. Compare the output hash with the hash listed in the specific version's Release section on GitHub.

---

## Distribution Note

The distributed ZIP file strictly includes the executable and the 'runtime/' folder containing 'songs.json'. All other necessary directories (such as 'output/', 'patch_nx_backups/', or log folders) are automatically generated by the application upon its first launch.