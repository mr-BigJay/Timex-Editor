# -*- coding: utf-8 -*-
"""اجرای برنامه بدون پنجرهٔ CMD (ویندوز — با pythonw)."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _show_error(exc: BaseException) -> None:
    log = ROOT / "launch_error.log"
    log.write_text(traceback.format_exc(), encoding="utf-8")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Timex Editor",
            f"خطا در اجرای برنامه:\n{exc}\n\nجزئیات در:\n{log}",
        )
        root.destroy()
    except Exception:
        pass


if __name__ == "__main__":
    try:
        from app.attendance_app import main

        main()
    except Exception as e:
        _show_error(e)
        sys.exit(1)
