from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QImageReader, QPixmapCache
import os
from collections import OrderedDict

_COVER_CACHE_LIMIT = 100
_cover_cache_keys = OrderedDict()



def load_pixmap_with_fallback(path):
    """Load pixmap with fallback readers (QImageReader/PIL)."""
    pixmap = QPixmap(path)
    if not pixmap.isNull():
        return pixmap

    reader = QImageReader(path)
    reader.setAutoTransform(True)
    image = reader.read()
    if not image.isNull():
        return QPixmap.fromImage(image)

    try:
        from PIL import Image
        with Image.open(path) as pil_img:
            pil_img = pil_img.convert("RGBA")
            data = pil_img.tobytes("raw", "RGBA")
            qimg = QImage(
                data,
                pil_img.width,
                pil_img.height,
                QImage.Format_RGBA8888
            ).copy()
            return QPixmap.fromImage(qimg)
    except Exception:
        return QPixmap()


def set_label_pixmap(label, path, fallback_text=""):
    """Load and scale an image into a QLabel. Returns True if loaded."""
    target_w = label.width() or label.geometry().width()
    target_h = label.height() or label.geometry().height()
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0
    cache_key = f"cover::{path}::{target_w}x{target_h}::{mtime}"
    cached = QPixmapCache.find(cache_key)
    if cached:
        _cover_cache_keys.pop(cache_key, None)
        _cover_cache_keys[cache_key] = True
        label.setPixmap(cached)
        label.setText("")
        return True

    pixmap = load_pixmap_with_fallback(path)
    if pixmap.isNull():
        label.setPixmap(QPixmap())
        label.setText(fallback_text)
        return False

    target_w = target_w or pixmap.width()
    target_h = target_h or pixmap.height()
    scaled = pixmap.scaled(
        target_w,
        target_h,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )
    QPixmapCache.insert(cache_key, scaled)
    _cover_cache_keys[cache_key] = True
    if _COVER_CACHE_LIMIT is not None:
        while len(_cover_cache_keys) > _COVER_CACHE_LIMIT:
            old_key, _ = _cover_cache_keys.popitem(last=False)
            QPixmapCache.remove(old_key)
    label.setPixmap(scaled)
    label.setText("")
    return True


def is_descendant_of(widget, candidates):
    """Return True if widget is or is inside any candidate widget."""
    if not widget:
        return False
    for candidate in candidates or []:
        w = widget
        while w:
            if w == candidate:
                return True
            w = w.parent()
    return False


def prewarm_cover_cache(paths, target_w, target_h, progress_callback=None):
    """Preload and cache scaled pixmaps for cover PNGs."""
    if not paths:
        return 0
    seen = set()
    warmed = 0
    for idx, path in enumerate(paths, start=1):
        if not path:
            continue
        if path in seen:
            continue
        seen.add(path)
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            mtime = 0
        cache_key = f"cover::{path}::{target_w}x{target_h}::{mtime}"
        if QPixmapCache.find(cache_key):
            continue
        pixmap = load_pixmap_with_fallback(path)
        if pixmap.isNull():
            continue
        w = target_w or pixmap.width()
        h = target_h or pixmap.height()
        scaled = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        QPixmapCache.insert(cache_key, scaled)
        _cover_cache_keys[cache_key] = True
        if _COVER_CACHE_LIMIT is not None:
            while len(_cover_cache_keys) > _COVER_CACHE_LIMIT:
                old_key, _ = _cover_cache_keys.popitem(last=False)
                QPixmapCache.remove(old_key)
        warmed += 1
        if progress_callback:
            progress_callback(idx, len(paths), path)
    return warmed
