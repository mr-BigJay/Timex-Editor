# -*- coding: utf-8 -*-
"""
پشتیبانی از کشیدن و رها کردن فایل در رابط گرافیکی.
Drag-and-drop support for the Tkinter GUI.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Callable, List, Optional

DND_BACKEND: Optional[str] = None
DND_FILES = None
TkinterDnD = None
_hook_dropfiles = None
DND_STATUS = "غیرفعال"
_root_hooked = False


def init_dnd() -> bool:
    """بارگذاری بهترین روش موجود برای کشیدن و رها کردن."""
    global DND_BACKEND, DND_FILES, TkinterDnD, _hook_dropfiles, DND_STATUS

    # ویندوز: tkinterdnd2 پایدارتر است؛ سپس win32_dnd بومی
    if sys.platform == "win32":
        if _load_tkinterdnd2():
            return True
        try:
            from win32_dnd import hook_dropfiles

            _hook_dropfiles = hook_dropfiles
            DND_BACKEND = "win32"
            DND_STATUS = "فعال (ویندوز)"
            return True
        except Exception:
            pass
        try:
            import windnd as w

            _hook_dropfiles = w.hook_dropfiles
            DND_BACKEND = "windnd"
            DND_STATUS = "فعال (windnd)"
            return True
        except Exception:
            pass
        if _try_pip_install("tkinterdnd2") and _load_tkinterdnd2():
            return True
        if _try_pip_install("windnd"):
            try:
                import windnd as w

                _hook_dropfiles = w.hook_dropfiles
                DND_BACKEND = "windnd"
                DND_STATUS = "فعال (windnd)"
                return True
            except Exception:
                pass

    # لینوکس/مک
    elif _load_tkinterdnd2():
        return True
    elif _try_pip_install("tkinterdnd2") and _load_tkinterdnd2():
        return True

    DND_BACKEND = None
    DND_STATUS = "غیرفعال — pip install tkinterdnd2"
    return False


def _load_tkinterdnd2() -> bool:
    global DND_BACKEND, DND_FILES, TkinterDnD, DND_STATUS
    try:
        from tkinterdnd2 import DND_FILES as _DND_FILES, TkinterDnD as _TkinterDnD

        DND_FILES = _DND_FILES
        TkinterDnD = _TkinterDnD
        DND_BACKEND = "tkinterdnd2"
        DND_STATUS = "فعال (tkinterdnd2)"
        return True
    except Exception:
        return False


def _try_pip_install(package: str) -> bool:
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "-q"],
            check=False,
            capture_output=True,
            timeout=120,
        )
        return True
    except Exception:
        return False


def dnd_available() -> bool:
    return DND_BACKEND is not None


def decode_dropped_bytes(raw) -> str:
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8", "mbcs", "cp1256", "gbk"):
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", errors="replace")


def normalize_dropped_path(path: str) -> str:
    path = (path or "").strip().strip('"').strip("'")
    if path.startswith("file://"):
        path = path[7:]
        if path.startswith("/") and len(path) > 2 and path[2] == ":":
            path = path[1:]
    return path.replace("/", "\\") if sys.platform == "win32" else path


def parse_tkdnd_data(tk, data: str) -> List[str]:
    """تجزیهٔ دادهٔ tkinterdnd2 با splitlist تکل."""
    data = (data or "").strip()
    if not data:
        return []
    if tk is not None:
        try:
            paths = list(tk.splitlist(data))
        except Exception:
            paths = _parse_tkdnd_manual(data)
    else:
        paths = _parse_tkdnd_manual(data)
    return [normalize_dropped_path(p) for p in paths if p]


def _parse_tkdnd_manual(data: str) -> List[str]:
    paths: List[str] = []
    i = 0
    while i < len(data):
        if data[i] == "{":
            end = data.find("}", i)
            if end == -1:
                paths.append(data[i + 1 :])
                break
            paths.append(data[i + 1 : end])
            i = end + 1
        else:
            space = data.find(" ", i)
            if space == -1:
                paths.append(data[i:])
                break
            paths.append(data[i:space])
            i = space + 1
        while i < len(data) and data[i] == " ":
            i += 1
    return paths


def register_tkdnd_widget(widget, callback) -> None:
    if DND_BACKEND != "tkinterdnd2" or DND_FILES is None:
        return
    try:
        widget.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
        widget.dnd_bind("<<Drop>>", callback)  # type: ignore[attr-defined]
    except Exception:
        pass


def register_tkdnd_tree(widget, callback) -> None:
    register_tkdnd_widget(widget, callback)
    for child in widget.winfo_children():
        register_tkdnd_tree(child, callback)


def hook_root_dnd(root, on_paths: Callable[[List[str]], None]) -> None:
    """اتصال کشیدن و رها کردن به کل پنجره (بعد از نمایش پنجره فراخوانی شود)."""
    global _root_hooked

    if DND_BACKEND in ("win32", "windnd") and _hook_dropfiles is not None:
        if _root_hooked:
            return

        def handler(files):
            paths = [normalize_dropped_path(decode_dropped_bytes(f)) for f in files]
            paths = [p for p in paths if p]
            if paths:
                root.after(0, lambda p=paths: on_paths(p))

        try:
            root.update_idletasks()
            _hook_dropfiles(root, handler)
            _root_hooked = True
        except Exception:
            pass
        return

    if DND_BACKEND == "tkinterdnd2":

        def on_drop(event):
            paths = parse_tkdnd_data(root.tk, event.data)
            if paths:
                on_paths(paths)

        register_tkdnd_tree(root, on_drop)
