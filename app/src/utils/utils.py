import logging
from pathlib import Path

from .. import config

def adjust_name_17(name):
    """Ensure 17 characters to maintain binary integrity."""
    clean_name = Path(name).stem
    return clean_name[:17].ljust(17, "0")


def resolve_cover_png_path(cover_path, temp_dir=None):
    """Resolve cover PNG path from a coverPath value."""
    if not cover_path:
        return ""
    if temp_dir is None:
        temp_dir = config.TEMP_PLAYLISTS_COVERS
    try:
        path_value = Path(cover_path)
        if path_value.is_absolute() and path_value.exists():
            return str(path_value)

        name = path_value.name
        while True:
            stem = Path(name).stem
            if stem == name:
                break
            name = stem

        candidates = [name, name.lower(), name.upper()]
        for candidate_name in candidates:
            candidate = temp_dir / f"{candidate_name}.png"
            if candidate.exists():
                return str(candidate)
    except Exception as e:
        logging.exception("Failed to resolve cover PNG path: %s | %s", cover_path, e)
    logging.warning("coverPngPath not found for coverPath=%s", cover_path)
    return ""
