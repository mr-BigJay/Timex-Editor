# -*- coding: utf-8 -*-
"""
نرم‌افزار مدیریت رکوردهای ورود و خروج
Attendance (check-in/out) records manager.

قابلیت‌ها:
- باز شدن با یک کادر «کشیدن و رها کردن» (Drag & Drop) در وسط صفحه برای گرفتن فایل.
- خواندن فایل رکوردها و نمایش آن‌ها در یک لیست.
- فرم ثبت رکورد در بالای صفحه (کد ۶ رقمی، تاریخ، ساعت) با دکمهٔ ثبت.
- امکان ورود تاریخ به صورت شمسی و ذخیرهٔ آن به صورت میلادی.
- نمایش «لیست موارد اضافه‌شده» بین فرم و لیست اصلی.
- اسکرول خودکار و ریل‌تایم لیست به محل رکورد تازه ثبت‌شده.
- دکمهٔ ذخیره به صورت Save As (کنار فایل اصلی، بدون بازنویسی فایل قبلی).
- دکمهٔ خروج برای بازگشت به حالت اولیه (کادر کشیدن و رها کردن).

اجرا:
    python attendance_app.pyw
    python -m app.attendance_app

برای فعال شدن کشیدن‌ورها کردن (اختیاری):
    pip install tkinterdnd2
در صورت نبود این کتابخانه، از دکمهٔ «انتخاب فایل» استفاده کنید.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app import attendance_core as ac
from app import dnd_support as dnd

dnd.init_dnd()
DND_AVAILABLE = dnd.dnd_available()


APP_TITLE = "مدیریت رکوردهای ورود و خروج"
APP_VERSION = "2.0"

# پالت رنگی تم جدید
BG = "#0B1120"
PANEL = "#151F32"
CARD_BORDER = "#2D3B55"
ACCENT = "#0EA5E9"
ACCENT_HOVER = "#0284C7"
TEXT = "#F1F5F9"
MUTED = "#94A3B8"
GOOD = "#22C55E"
GOOD_HOVER = "#16A34A"
DANGER = "#EF4444"
DANGER_HOVER = "#DC2626"
PURPLE = "#8B5CF6"
PURPLE_HOVER = "#7C3AED"
HILITE = "#1E293B"
ROW_ALT = "#1A2538"
ADDED_BG = "#14532D"
ADDED_FG = "#BBF7D0"
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")


class AttendanceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.root.geometry("1100x800")
        self.root.minsize(900, 680)
        self.root.configure(bg=BG)

        self.records: list[ac.Record] = []
        self.source_path: str | None = None
        self.line_prefix = ""
        self.default_extra: list[str] = []
        self.dirty = False
        self._updating_entry = False
        # نگاشت رکورد -> شناسهٔ ردیف در جدول اصلی
        self._row_of_record: dict[int, str] = {}

        self._setup_style()

        # کانتینری که بین «صفحهٔ کشیدن فایل» و «صفحهٔ ویرایش» جابه‌جا می‌شود
        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.show_drop_screen()
        self.root.update_idletasks()
        self.root.after(200, self._setup_dnd)

    def _setup_dnd(self):
        """فعال‌سازی کشیدن و رها کردن پس از نمایش کامل پنجره."""
        dnd.hook_root_dnd(self.root, self._on_dropped_paths)
        self._update_dnd_status()

    def _update_dnd_status(self):
        if hasattr(self, "dnd_status_lbl"):
            if dnd.dnd_available():
                self.dnd_status_lbl.config(text=f"کشیدن و رها کردن: {dnd.DND_STATUS}", fg=GOOD)
            else:
                self.dnd_status_lbl.config(
                    text="کشیدن و رها کردن غیرفعال — pip install tkinterdnd2",
                    fg=DANGER,
                )

    # ------------------------------------------------------------------ style
    def _setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=30,
            borderwidth=0,
            font=FONT,
        )
        style.configure(
            "Treeview.Heading",
            background=HILITE,
            foreground=TEXT,
            font=FONT_BOLD,
            relief="flat",
            padding=(8, 6),
        )
        style.map("Treeview", background=[("selected", ACCENT)], foreground=[("selected", "white")])
        style.configure("Vertical.TScrollbar", background=HILITE, troughcolor=BG, borderwidth=0)

    def _card(self, parent, title: str, expand=False):
        """کارت با عنوان و حاشیهٔ ظریف."""
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="both" if expand else "x", padx=20, pady=(0, 10))
        if expand:
            outer.pack_configure(expand=True)

        box = tk.Frame(outer, bg=PANEL, highlightbackground=CARD_BORDER, highlightthickness=1)
        box.pack(fill="both", expand=expand)

        head = tk.Frame(box, bg=PANEL)
        head.pack(fill="x", padx=14, pady=(10, 4))
        tk.Label(head, text=title, bg=PANEL, fg=TEXT, font=FONT_SECTION).pack(anchor="e")

        body = tk.Frame(box, bg=PANEL)
        body.pack(fill="both", expand=expand, padx=14, pady=(0, 12))
        return outer, body

    def _styled_entry(self, parent, width=14):
        return tk.Entry(
            parent,
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 12),
            justify="center",
            width=width,
            highlightthickness=1,
            highlightbackground=CARD_BORDER,
            highlightcolor=ACCENT,
        )

    def _field(self, parent, label: str, width=14):
        box = tk.Frame(parent, bg=PANEL)
        lbl = tk.Label(box, text=label, bg=PANEL, fg=MUTED, font=FONT)
        lbl.pack(anchor="e")
        entry = self._styled_entry(box, width=width)
        entry.pack(pady=(6, 0), ipady=6, fill="x")
        return box, entry, lbl

    # ---------------------------------------------------------- helper widgets
    def _button(self, parent, text, command, bg=ACCENT, fg="white", width=None, hover=None, font=None):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover or ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
            font=font or FONT_BOLD,
        )
        if width:
            btn.configure(width=width)
        return btn

    def _format_entry(self, entry: tk.Entry, formatter):
        """اعمال قالب‌بندی خودکار و حفظ موقعیت مکان‌نما."""
        if self._updating_entry:
            return
        text = entry.get()
        cursor = entry.index(tk.INSERT)
        digits_before = sum(1 for c in text[:cursor] if c.isdigit())

        formatted = formatter(text)
        if formatted == text:
            return

        self._updating_entry = True
        try:
            entry.delete(0, tk.END)
            entry.insert(0, formatted)

            new_pos = len(formatted)
            digit_count = 0
            for i, ch in enumerate(formatted):
                if ch.isdigit():
                    digit_count += 1
                if digit_count >= digits_before:
                    new_pos = i + 1
                    break
            entry.icursor(new_pos)
        finally:
            self._updating_entry = False

    def _bind_code_entry(self, entry: tk.Entry):
        def on_change(_event=None):
            self._format_entry(entry, ac.format_code_input)

        entry.bind("<KeyRelease>", on_change)
        entry.bind("<FocusOut>", on_change)

    def _bind_date_entry(self, entry: tk.Entry):
        def on_change(_event=None):
            self._format_entry(
                entry, lambda t: ac.format_date_input(t, jalali=self.jalali_var.get())
            )

        entry.bind("<KeyRelease>", on_change)
        entry.bind("<FocusOut>", on_change)

    def _bind_time_entry(self, entry: tk.Entry):
        def on_change(_event=None):
            self._format_entry(entry, ac.format_time_input)

        entry.bind("<KeyRelease>", on_change)
        entry.bind("<FocusOut>", on_change)

    def _on_jalali_toggle(self):
        """تغییر قالب تاریخ هنگام جابه‌جایی بین شمسی/میلادی."""
        self._update_date_hint()
        text = self.date_entry.get()
        if text:
            formatted = ac.format_date_input(text, jalali=self.jalali_var.get())
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, formatted)

    def _clear_container(self):
        for child in self.container.winfo_children():
            child.destroy()

    # ============================================================ DROP SCREEN
    def show_drop_screen(self):
        """حالت اولیه: کادر کشیدن و رها کردن در وسط صفحه."""
        self._clear_container()
        self.records = []
        self.source_path = None
        self.line_prefix = ""
        self.default_extra = []
        self.dirty = False

        wrap = tk.Frame(self.container, bg=BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            wrap, text="🕐", bg=BG, fg=ACCENT, font=("Segoe UI", 36)
        ).pack(pady=(0, 8))
        tk.Label(wrap, text=APP_TITLE, bg=BG, fg=TEXT, font=FONT_TITLE).pack(pady=(0, 4))
        tk.Label(
            wrap,
            text=f"نسخه {APP_VERSION}",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(pady=(0, 14))
        tk.Label(
            wrap,
            text="فایل رکوردهای ورود/خروج را در کادر زیر بیندازید",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 12),
        ).pack(pady=(0, 16))

        drop = tk.Frame(
            wrap,
            bg=PANEL,
            highlightbackground=ACCENT,
            highlightthickness=2,
            width=580,
            height=240,
        )
        drop.pack()
        drop.pack_propagate(False)

        tk.Label(drop, text="⬇", bg=PANEL, fg=ACCENT, font=("Segoe UI", 42, "bold")).pack(
            pady=(44, 4)
        )
        hint = tk.Label(
            drop,
            text="فایل .dat یا .txt را اینجا رها کنید" if DND_AVAILABLE else "برای انتخاب فایل کلیک کنید",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
        )
        hint.pack()
        note = tk.Label(
            drop,
            text="یا روی دکمهٔ زیر کلیک کنید" if DND_AVAILABLE else "برای فعال‌سازی: pip install tkinterdnd2",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        note.pack(pady=(4, 0))

        self.dnd_status_lbl = tk.Label(wrap, text="", bg=BG, fg=MUTED, font=("Segoe UI", 9))
        self.dnd_status_lbl.pack(pady=(10, 6))
        self._update_dnd_status()

        browse = self._button(wrap, "انتخاب فایل", self._browse_open)
        browse.pack(pady=14)

        for w in (drop, hint, note):
            w.bind("<Button-1>", lambda e: self._browse_open())

        if dnd.DND_BACKEND == "tkinterdnd2":
            self.root.after(50, self._setup_dnd)

    def _on_dropped_paths(self, paths: list[str]):
        if paths:
            self._load_file(paths[0])

    def _browse_open(self):
        path = filedialog.askopenfilename(
            title="انتخاب فایل رکوردها",
            filetypes=ac.RECORD_FILETYPES,
        )
        if path:
            self._load_file(path)

    def _load_file(self, path: str):
        if not path or not os.path.isfile(path):
            messagebox.showerror(APP_TITLE, "فایل معتبری انتخاب نشد.")
            return
        try:
            records = ac.read_records(path)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror(APP_TITLE, f"خطا در خواندن فایل:\n{exc}")
            return
        self.records = records
        self.source_path = path
        self.line_prefix, self.default_extra = ac.detect_output_format(records)
        self.dirty = False
        self.show_editor_screen()

    # ========================================================== EDITOR SCREEN
    def show_editor_screen(self):
        self._clear_container()

        # ── هدر ──────────────────────────────────────────────────────────────
        header = tk.Frame(self.container, bg=HILITE, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        hdr_inner = tk.Frame(header, bg=HILITE)
        hdr_inner.pack(fill="both", expand=True, padx=20)

        right = tk.Frame(hdr_inner, bg=HILITE)
        right.pack(side="right", fill="y", pady=10)
        tk.Label(right, text="🕐", bg=HILITE, fg=ACCENT, font=("Segoe UI", 16)).pack(
            side="right", padx=(0, 8)
        )
        tk.Label(right, text=APP_TITLE, bg=HILITE, fg=TEXT, font=FONT_SECTION).pack(side="right")
        tk.Label(
            right, text=f"  v{APP_VERSION}", bg=HILITE, fg=MUTED, font=("Segoe UI", 9)
        ).pack(side="right", padx=(0, 12))

        self._button(
            hdr_inner, "ذخیره", self._on_save_as, bg=GOOD, hover=GOOD_HOVER
        ).pack(side="left", pady=10)

        path_frame = tk.Frame(hdr_inner, bg=HILITE)
        path_frame.pack(side="left", fill="x", expand=True, padx=20)
        tk.Label(path_frame, text="فایل:", bg=HILITE, fg=MUTED, font=FONT).pack(side="left")
        tk.Label(
            path_frame,
            text=self.source_path or "",
            bg=HILITE,
            fg=TEXT,
            font=FONT_BOLD,
            anchor="w",
        ).pack(side="left", padx=(6, 0))

        self.root.bind("<Control-s>", lambda e: self._on_save_as())
        self.root.bind("<Control-S>", lambda e: self._on_save_as())

        # ── فرم ثبت ──────────────────────────────────────────────────────
        _, form_body = self._card(self.container, "ثبت رکورد جدید")

        row = tk.Frame(form_body, bg=PANEL)
        row.pack(fill="x")

        submit_box = tk.Frame(row, bg=PANEL)
        submit_box.pack(side="left", padx=(0, 12), pady=4)
        self._button(submit_box, "ثبت رکورد", self._on_submit, bg=GOOD, hover=GOOD_HOVER).pack(
            pady=18
        )

        self.jalali_var = tk.BooleanVar(value=False)
        jalali_chk = tk.Checkbutton(
            row,
            text="ورود تاریخ شمسی",
            variable=self.jalali_var,
            command=self._on_jalali_toggle,
            bg=PANEL,
            fg=TEXT,
            selectcolor=BG,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=FONT,
        )
        jalali_chk.pack(side="right", padx=12, pady=20)

        code_box, self.code_entry, _ = self._field(row, "کد پرسنلی (۶ رقم)")
        code_box.pack(side="right", padx=8)
        self._bind_code_entry(self.code_entry)

        date_box, self.date_entry, self.date_label = self._field(row, "تاریخ میلادی (yyyy-mm-dd)")
        date_box.pack(side="right", padx=8)
        self._bind_date_entry(self.date_entry)

        time_box = tk.Frame(row, bg=PANEL)
        time_box.pack(side="right", padx=8)
        self._button(time_box, "ورود", self._on_entry_time, bg=ACCENT, hover=ACCENT_HOVER).pack(
            pady=(0, 4)
        )
        tk.Label(time_box, text="ساعت (hh:mm:ss)", bg=PANEL, fg=MUTED, font=FONT).pack(anchor="e")
        self.time_entry = self._styled_entry(time_box)
        self.time_entry.pack(pady=(6, 0), ipady=6)
        self._bind_time_entry(self.time_entry)
        self._button(
            time_box, "خروج", self._on_exit_time, bg=PURPLE, hover=PURPLE_HOVER
        ).pack(pady=(4, 0))

        self.date_hint = tk.Label(form_body, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 9))
        self.date_hint.pack(anchor="e", pady=(4, 0))
        self._update_date_hint()

        self.code_entry.bind("<Return>", lambda e: self._on_submit())
        self.date_entry.bind("<Return>", lambda e: self._on_submit())
        self.time_entry.bind("<Return>", lambda e: self._on_submit())

        # ── موارد اضافه‌شده ────────────────────────────────────────────────
        _, added_body = self._card(self.container, "موارد اضافه‌شده در این نشست")
        self.added_tree = self._make_tree(added_body, height=3)
        self.added_tree.pack(fill="x")

        # ── همهٔ رکوردها ─────────────────────────────────────────────────
        _, list_body = self._card(self.container, "همهٔ رکوردها", expand=True)
        tree_wrap = tk.Frame(list_body, bg=PANEL)
        tree_wrap.pack(fill="both", expand=True)

        self.tree = self._make_tree(tree_wrap, height=14)
        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="left", fill="y")
        self.tree.pack(side="right", fill="both", expand=True)

        # ── فوتر ─────────────────────────────────────────────────────────
        footer = tk.Frame(self.container, bg=BG)
        footer.pack(fill="x", padx=20, pady=(4, 14))

        self._button(footer, "خروج", self._on_exit, bg=DANGER, hover=DANGER_HOVER).pack(
            side="right"
        )
        self.status_lbl = tk.Label(footer, text="", bg=BG, fg=MUTED, font=FONT)
        self.status_lbl.pack(side="left")

        self._render_all()
        self.code_entry.focus_set()

    def _make_tree(self, parent, height):
        cols = ("row", "code", "date", "jalali", "time", "info")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        tree.heading("row", text="#")
        tree.heading("code", text="کد پرسنلی")
        tree.heading("date", text="تاریخ میلادی")
        tree.heading("jalali", text="تاریخ شمسی")
        tree.heading("time", text="ساعت")
        tree.heading("info", text="ستون‌های اضافی")
        tree.column("row", width=44, anchor="center", stretch=False)
        tree.column("code", width=100, anchor="center", stretch=False)
        tree.column("date", width=110, anchor="center", stretch=False)
        tree.column("jalali", width=110, anchor="center", stretch=False)
        tree.column("time", width=90, anchor="center", stretch=False)
        tree.column("info", width=140, anchor="center", stretch=True)
        tree.tag_configure("added", background=ADDED_BG, foreground=ADDED_FG)
        tree.tag_configure("odd", background=ROW_ALT)
        tree.tag_configure("even", background=PANEL)
        return tree

    def _update_date_hint(self):
        if self.jalali_var.get():
            self.date_label.config(text="تاریخ شمسی (yyyy/mm/dd)")
            self.date_hint.config(
                text="قالب پیش‌فرض شمسی: yyyy/mm/dd  (مثال: 1405/04/01)  ← هنگام ذخیره به میلادی تبدیل می‌شود"
            )
        else:
            self.date_label.config(text="تاریخ میلادی (yyyy-mm-dd)")
            self.date_hint.config(text="قالب پیش‌فرض میلادی: yyyy-mm-dd  (مثال: 2026-06-22)")

    # ---------------------------------------------------------------- rendering
    def _render_all(self):
        """بازسازی جدول اصلی به صورت مرتب‌شده بر اساس تاریخ/ساعت."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_of_record.clear()

        ordered = sorted(self.records, key=lambda r: r.sort_key)
        for idx, rec in enumerate(ordered, start=1):
            item = self._insert_row(self.tree, idx, rec)
            self._row_of_record[id(rec)] = item
        self._update_status()

    def _insert_row(self, tree, idx, rec: ac.Record):
        jalali = ac.gregorian_str_to_jalali_str(rec.date)
        values = (idx, rec.code, rec.date, jalali, rec.time, " ".join(rec.extra))
        if rec.added:
            tags = ("added",)
        else:
            tags = ("odd",) if idx % 2 else ("even",)
        return tree.insert("", "end", values=values, tags=tags)

    def _append_added_row(self, rec: ac.Record):
        idx = len(self.added_tree.get_children()) + 1
        item = self._insert_row(self.added_tree, idx, rec)
        self.added_tree.see(item)

    def _update_status(self):
        total = len(self.records)
        added = sum(1 for r in self.records if r.added)
        star = " *" if self.dirty else ""
        self.status_lbl.config(
            text=f"مجموع رکوردها: {total}   |   اضافه‌شده: {added}{star}"
        )

    def _set_time_value(self, time_str: str):
        """قرار دادن ساعت در فیلد بدون تداخل با قالب‌بندی خودکار."""
        self._updating_entry = True
        try:
            self.time_entry.delete(0, tk.END)
            self.time_entry.insert(0, time_str)
        finally:
            self._updating_entry = False

    def _on_entry_time(self):
        self._set_time_value(ac.random_entry_time())

    def _on_exit_time(self):
        self._set_time_value(ac.random_exit_time())

    # ------------------------------------------------------------------ actions
    def _on_submit(self):
        code_text = self.code_entry.get()
        date_text = self.date_entry.get()
        time_text = self.time_entry.get()

        if len(code_text) != 6:
            messagebox.showwarning(APP_TITLE, "کد پرسنلی باید دقیقاً ۶ رقم باشد (نه کمتر و نه بیشتر).")
            return
        if not ac.is_complete_date(date_text):
            messagebox.showwarning(
                APP_TITLE,
                f"تاریخ باید کامل باشد (مثال: {'1405/04/01' if self.jalali_var.get() else '2026-06-22'}).",
            )
            return
        if not ac.is_complete_time(time_text):
            messagebox.showwarning(APP_TITLE, "ساعت باید کامل باشد (مثال: 07:39:23).")
            return

        try:
            code = ac.normalize_code(code_text)
            date = ac.normalize_date(date_text, jalali=self.jalali_var.get())
            time = ac.normalize_time(time_text)
        except ValueError as exc:
            messagebox.showwarning(APP_TITLE, str(exc))
            return

        rec = ac.Record(
            code=code,
            date=date,
            time=time,
            extra=list(self.default_extra),
            added=True,
        )
        self.records.append(rec)
        self.dirty = True

        # بازسازی لیست اصلی و افزودن به لیست موارد اضافه‌شده
        self._render_all()
        self._append_added_row(rec)

        # اسکرول ریل‌تایم به محل رکورد تازه در لیست اصلی + انتخاب و برجسته‌سازی
        item = self._row_of_record.get(id(rec))
        if item:
            self.tree.selection_set(item)
            self.tree.focus(item)
            self.tree.see(item)

        # پاک کردن فیلدها برای ورودی بعدی (کد و تاریخ نگه داشته می‌شوند برای سرعت)
        self.time_entry.delete(0, "end")
        self.code_entry.focus_set()

    def _write_records_to(self, path: str) -> bool:
        """ذخیرهٔ رکوردها در مسیر مشخص. در صورت موفقیت True برمی‌گرداند."""
        if not self.records:
            messagebox.showinfo(APP_TITLE, "رکوردی برای ذخیره وجود ندارد.")
            return False
        if self.source_path and os.path.abspath(path) == os.path.abspath(self.source_path):
            if not messagebox.askyesno(
                APP_TITLE,
                "این همان فایل اصلی است. برای جلوگیری از بازنویسی، نامی متفاوت انتخاب کنید.\n"
                "آیا مطمئن هستید که می‌خواهید فایل اصلی بازنویسی شود؟",
            ):
                return False
        ordered = sorted(self.records, key=lambda r: r.sort_key)
        try:
            ac.write_records(path, ordered)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror(APP_TITLE, f"خطا در ذخیره:\n{exc}")
            return False
        self.dirty = False
        self._update_status()
        messagebox.showinfo(APP_TITLE, f"با موفقیت ذخیره شد:\n{path}")
        return True

    def _on_save_as(self):
        if not self.records:
            messagebox.showinfo(APP_TITLE, "رکوردی برای ذخیره وجود ندارد.")
            return
        initial_dir = (
            os.path.dirname(os.path.abspath(self.source_path))
            if self.source_path
            else os.getcwd()
        )
        initial_file = os.path.basename(ac.suggested_save_path(self.source_path or ""))
        default_ext = ac.default_save_extension(self.source_path or "")
        path = filedialog.asksaveasfilename(
            title="ذخیره",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=default_ext,
            filetypes=ac.RECORD_FILETYPES,
        )
        if path:
            self._write_records_to(path)

    def _on_exit(self):
        """بازگشت به حالت اولیه (کادر کشیدن و رها کردن)."""
        if self.dirty:
            answer = messagebox.askyesnocancel(
                APP_TITLE,
                "تغییرات ذخیره‌نشده دارید.\nقبل از خروج ذخیره شود؟\n"
                "(بله = ذخیره، خیر = خروج بدون ذخیره، لغو = ماندن)",
            )
            if answer is None:
                return
            if answer:
                self._on_save_as()
                if self.dirty:  # کاربر ذخیره را لغو کرد
                    return
        self.show_drop_screen()


def main():
    # در ویندوز از tk.Tk معمولی + win32_dnd استفاده می‌شود (پایدارتر)
    if dnd.DND_BACKEND == "tkinterdnd2":
        root = dnd.TkinterDnD.Tk()  # type: ignore[union-attr]
    else:
        root = tk.Tk()
    app = AttendanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
