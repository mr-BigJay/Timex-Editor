# -*- coding: utf-8 -*-
"""
کشیدن و رها کردن فایل در ویندوز (بدون وابستگی خارجی).
Embedded Windows drag-and-drop hook with correct 64-bit ctypes signatures.
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

# نگه‌داری callbackها برای جلوگیری از GC
_HOOK_REFS: list = []

WM_DROPFILES = 0x0233
GWL_WNDPROC = -4

_IS_64 = ctypes.sizeof(ctypes.c_void_p) == 8
_LRESULT = ctypes.c_longlong if _IS_64 else ctypes.c_long

_WNDPROC = ctypes.WINFUNCTYPE(
    _LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


def _setup_api():
    user32 = ctypes.windll.user32
    shell32 = ctypes.windll.shell32

    shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    shell32.DragAcceptFiles.restype = None

    shell32.DragFinish.argtypes = [wintypes.HANDLE]
    shell32.DragFinish.restype = None

    shell32.DragQueryFileW.argtypes = [
        wintypes.HANDLE,
        wintypes.UINT,
        wintypes.LPWSTR,
        wintypes.UINT,
    ]
    shell32.DragQueryFileW.restype = wintypes.UINT

    user32.CallWindowProcW.argtypes = [
        ctypes.c_void_p,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.CallWindowProcW.restype = _LRESULT

    user32.DefWindowProcW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    user32.DefWindowProcW.restype = _LRESULT

    if _IS_64:
        user32.GetWindowLongPtrW.restype = ctypes.c_void_p
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.SetWindowLongPtrW.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        get_wndproc = user32.GetWindowLongPtrW
        set_wndproc = user32.SetWindowLongPtrW
    else:
        user32.GetWindowLongW.restype = ctypes.c_void_p
        user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetWindowLongW.restype = ctypes.c_void_p
        user32.SetWindowLongW.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        get_wndproc = user32.GetWindowLongW
        set_wndproc = user32.SetWindowLongW

    return user32, shell32, get_wndproc, set_wndproc


def hook_dropfiles(tkwindow_or_hwnd, func, force_unicode: bool = True):
    """ثبت دریافت فایل رها شده روی پنجرهٔ tkinter یا hwnd."""
    if sys.platform != "win32":
        return

    hwnd = (
        tkwindow_or_hwnd.winfo_id()
        if getattr(tkwindow_or_hwnd, "winfo_id", None)
        else int(tkwindow_or_hwnd)
    )

    user32, shell32, get_wndproc, set_wndproc = _setup_api()
    old_wndproc = get_wndproc(hwnd, GWL_WNDPROC)

    def _extract_files(hdrop):
        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        files = []
        for i in range(count):
            size = shell32.DragQueryFileW(hdrop, i, None, 0) + 1
            buf = ctypes.create_unicode_buffer(size)
            shell32.DragQueryFileW(hdrop, i, buf, size)
            files.append(buf.value)
        shell32.DragFinish(hdrop)
        return files

    def py_drop_func(h, msg, wp, lp):
        if msg == WM_DROPFILES:
            try:
                files = _extract_files(wintypes.HANDLE(wp))
                if files:
                    func(files)
            except Exception:
                pass
            return 0

        if old_wndproc:
            return user32.CallWindowProcW(old_wndproc, h, msg, wp, lp)
        return user32.DefWindowProcW(h, msg, wp, lp)

    new_wndproc = _WNDPROC(py_drop_func)
    shell32.DragAcceptFiles(hwnd, True)
    set_wndproc(hwnd, GWL_WNDPROC, ctypes.cast(new_wndproc, ctypes.c_void_p))

    _HOOK_REFS.append((hwnd, old_wndproc, new_wndproc, func))
