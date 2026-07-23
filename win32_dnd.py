# -*- coding: utf-8 -*-
"""
کشیدن و رها کردن فایل در ویندوز (بدون وابستگی خارجی).
Embedded Windows drag-and-drop hook (MIT, based on windnd by vilame).
"""

from __future__ import annotations

import ctypes
import platform
import sys
from ctypes import wintypes


def hook_dropfiles(tkwindow_or_hwnd, func, force_unicode: bool = True):
    """ثبت دریافت فایل رها شده روی پنجرهٔ tkinter یا hwnd."""
    if sys.platform != "win32":
        return

    hwnd = (
        tkwindow_or_hwnd.winfo_id()
        if getattr(tkwindow_or_hwnd, "winfo_id", None)
        else tkwindow_or_hwnd
    )

    if platform.architecture()[0] == "32bit":
        get_window_long = ctypes.windll.user32.GetWindowLongW
        set_window_long = ctypes.windll.user32.SetWindowLongW
        argtype = wintypes.DWORD
    else:
        get_window_long = ctypes.windll.user32.GetWindowLongPtrW
        set_window_long = ctypes.windll.user32.SetWindowLongPtrW
        argtype = ctypes.c_uint64

    prototype = ctypes.WINFUNCTYPE(argtype, argtype, argtype, argtype, argtype)
    wm_dropfiles = 0x233
    gwl_wndproc = -4
    create_buffer = ctypes.create_unicode_buffer if force_unicode else ctypes.c_buffer
    drag_query_file = (
        ctypes.windll.shell32.DragQueryFileW
        if force_unicode
        else ctypes.windll.shell32.DragQueryFile
    )

    old_proc_holder: dict[str, object] = {"proc": None}

    def py_drop_func(hwnd, msg, wp, lp):
        if msg == wm_dropfiles:
            count = drag_query_file(argtype(wp), 0xFFFFFFFF, None, 0)
            files = []
            for i in range(count):
                size = drag_query_file(argtype(wp), i, None, 0) + 1
                buffer = create_buffer(size)
                drag_query_file(argtype(wp), i, buffer, size)
                files.append(buffer.value)
            if files:
                func(files)
            ctypes.windll.shell32.DragFinish(argtype(wp))
        old = old_proc_holder["proc"]
        return ctypes.windll.user32.CallWindowProcW(
            argtype(old), argtype(hwnd), argtype(msg), argtype(wp), argtype(lp)
        )

    new_proc = prototype(py_drop_func)
    ctypes.windll.shell32.DragAcceptFiles(hwnd, True)
    old_proc_holder["proc"] = get_window_long(hwnd, gwl_wndproc)
    set_window_long(hwnd, gwl_wndproc, new_proc)
    # جلوگیری از جمع‌آوری زبالهٔ callback
    hook_dropfiles._refs = getattr(hook_dropfiles, "_refs", [])  # type: ignore[attr-defined]
    hook_dropfiles._refs.append((new_proc, old_proc_holder))  # type: ignore[attr-defined]
