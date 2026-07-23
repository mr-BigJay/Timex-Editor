# -*- coding: utf-8 -*-
"""
پشتیبانی از کشیدن و رها کردن فایل در رابط گرافیکی.
Drag-and-drop support for the Tkinter GUI.

اولویت: tkinterdnd2 (چندسکویی) سپس windnd (ویندوز).
"""

from __future__ import annotations

import sys
from typing import Callable, List, Optional

DND_BACKEND: Optional[str] = None
DND_FILES = None
TkinterDnD = None
_windnd = None


def init_dnd() -> bool:
    """بارگذاری بهترین کتابخانهٔ موجود برای کشیدن و رها کردن."""
    global DND_BACKEND, DND_FILES, TkinterDnD, _windnd

    try:
        from tkinterdnd2 import DND_FILES as _DND_FILES, TkinterDnD as _TkinterDnD

        DND_FILES = _DND_FILES
        TkinterDnD = _TkinterDnD
        DND_BACKEND = "tkinterdnd2"
        return True
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import windnd as w

            _windnd = w
            DND_BACKEND = "windnd"
            return True
        except Exception:
            pass

    DND_BACKEND = None
    return False


def dnd_available() -> bool:
    return DND_BACKEND is not None


def decode_dropped_bytes(raw) -> str:
    """تبدیل مسیر دریافتی از ویندوز به رشته."""
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8", "mbcs", "cp1256", "gbk"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def normalize_dropped_path(path: str) -> str:
    """پاک‌سازی مسیر دریافتی از رویداد کشیدن و رها کردن."""
    path = (path or "").strip().strip('"').strip("'")
    if path.startswith("file://"):
        path = path[7:]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
    return path.replace("/", "\\") if sys.platform == "win32" else path


def parse_tkdnd_data(data: str) -> List[str]:
    """تجزیهٔ دادهٔ tkinterdnd2 به لیست مسیرها."""
    data = (data or "").strip()
    if not data:
        return []

    paths: List[str] = []
    i = 0
    while i < len(data):
        if data[i] == "{":
            end = data.find("}", i)
            if end == -1:
                paths.append(normalize_dropped_path(data[i + 1 :]))
                break
            paths.append(normalize_dropped_path(data[i + 1 : end]))
            i = end + 1
        else:
            space = data.find(" ", i)
            if space == -1:
                paths.append(normalize_dropped_path(data[i:]))
                break
            paths.append(normalize_dropped_path(data[i:space]))
            i = space + 1
        while i < len(data) and data[i] == " ":
            i += 1
    return [p for p in paths if p]


def register_tkdnd_widget(widget, callback) -> None:
    """ثبت یک ویجت به‌عنوان هدف کشیدن و رها کردن."""
    if DND_BACKEND != "tkinterdnd2" or DND_FILES is None:
        return
    widget.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
    widget.dnd_bind("<<Drop>>", callback)  # type: ignore[attr-defined]


def register_tkdnd_tree(widget, callback) -> None:
    """ثبت ویجت و تمام فرزندانش برای کشیدن و رها کردن."""
    register_tkdnd_widget(widget, callback)
    for child in widget.winfo_children():
        register_tkdnd_tree(child, callback)


def hook_windnd(root, on_paths: Callable[[List[str]], None]) -> None:
    """اتصال کشیدن و رها کردن ویندوز به کل پنجره."""
    if DND_BACKEND != "windnd" or _windnd is None:
        return

    def handler(files):
        paths = [normalize_dropped_path(decode_dropped_bytes(f)) for f in files]
        paths = [p for p in paths if p]
        if paths:
            on_paths(paths)

    _windnd.hook_dropfiles(root, func=handler)
