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
    python3 attendance_app.py

برای فعال شدن کشیدن‌ورها کردن (اختیاری):
    pip install tkinterdnd2
در صورت نبود این کتابخانه، از دکمهٔ «انتخاب فایل» استفاده کنید.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import attendance_core as ac

# تلاش برای فعال‌سازی کشیدن و رها کردن (اختیاری)
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    DND_AVAILABLE = True
except Exception:  # pragma: no cover - بستگی به محیط دارد
    DND_AVAILABLE = False


APP_TITLE = "مدیریت رکوردهای ورود و خروج"
APP_VERSION = "1.1"

BG = "#0f172a"
PANEL = "#1e293b"
ACCENT = "#2563eb"
ACCENT_HOVER = "#1d4ed8"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
GOOD = "#16a34a"
DANGER = "#dc2626"
HILITE = "#374151"
ADDED_BG = "#14532d"


class AttendanceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.root.geometry("1000x760")
        self.root.minsize(820, 620)
        self.root.configure(bg=BG)

        self.records: list[ac.Record] = []
        self.source_path: str | None = None
        self.dirty = False
        self._updating_entry = False
        # نگاشت رکورد -> شناسهٔ ردیف در جدول اصلی
        self._row_of_record: dict[int, str] = {}

        self._setup_style()

        # کانتینری که بین «صفحهٔ کشیدن فایل» و «صفحهٔ ویرایش» جابه‌جا می‌شود
        self.container = tk.Frame(self.root, bg=BG)
        self.container.pack(fill="both", expand=True)

        self.show_drop_screen()

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
            rowheight=26,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=HILITE,
            foreground=TEXT,
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Treeview", background=[("selected", ACCENT)])

    # ---------------------------------------------------------- helper widgets
    def _button(self, parent, text, command, bg=ACCENT, fg="white", width=None, hover=None):
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
            padx=16,
            pady=8,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
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
        self.dirty = False

        wrap = tk.Frame(self.container, bg=BG)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        title = tk.Label(
            wrap,
            text=APP_TITLE,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(pady=(0, 6))

        subtitle = tk.Label(
            wrap,
            text="فایل رکوردهای ورود/خروج را در کادر زیر بیندازید",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 12),
        )
        subtitle.pack(pady=(0, 18))

        drop = tk.Frame(
            wrap,
            bg=PANEL,
            highlightbackground=ACCENT,
            highlightthickness=2,
            width=560,
            height=260,
        )
        drop.pack()
        drop.pack_propagate(False)

        icon = tk.Label(drop, text="⬇", bg=PANEL, fg=ACCENT, font=("Segoe UI", 46, "bold"))
        icon.pack(pady=(48, 4))

        hint = tk.Label(
            drop,
            text=(
                "فایل را اینجا رها کنید"
                if DND_AVAILABLE
                else "برای انتخاب فایل کلیک کنید"
            ),
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        )
        hint.pack()

        note = tk.Label(
            drop,
            text=(
                "یا روی دکمهٔ زیر کلیک کنید"
                if DND_AVAILABLE
                else "کشیدن‌ورها کردن نیازمند نصب tkinterdnd2 است"
            ),
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        note.pack(pady=(4, 0))

        browse = self._button(wrap, "انتخاب فایل", self._browse_open)
        browse.pack(pady=18)

        # کلیک روی کادر هم فایل را باز می‌کند
        for w in (drop, icon, hint, note):
            w.bind("<Button-1>", lambda e: self._browse_open())

        if DND_AVAILABLE:
            drop.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            drop.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]

    def _on_drop(self, event):
        path = event.data.strip()
        # tkdnd مسیرهای دارای فاصله را داخل {} می‌گذارد
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        # اگر چند فایل رها شد، اولی را بگیر
        path = path.split("} {")[0].strip("{}")
        self._load_file(path)

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
        self.dirty = False
        self.show_editor_screen()

    # ========================================================== EDITOR SCREEN
    def show_editor_screen(self):
        self._clear_container()

        # نوار عنوان فایل و دکمهٔ ذخیره
        header = tk.Frame(self.container, bg=BG)
        header.pack(fill="x", padx=16, pady=(12, 4))

        save_btn = self._button(
            header, "ذخیره", self._on_save_as, bg=GOOD, hover="#15803d"
        )
        save_btn.pack(side="right", padx=(8, 0))

        tk.Label(
            header,
            text="فایل باز شده:",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="left")
        tk.Label(
            header,
            text=self.source_path or "",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=(6, 0))

        self.root.bind("<Control-s>", lambda e: self._on_save_as())
        self.root.bind("<Control-S>", lambda e: self._on_save_as())

        # ---------------------------------------------------------- فرم ثبت
        form = tk.LabelFrame(
            self.container,
            text="  ثبت رکورد جدید  ",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            bd=1,
            relief="solid",
            labelanchor="ne",
        )
        form.pack(fill="x", padx=16, pady=6)

        row = tk.Frame(form, bg=PANEL)
        row.pack(fill="x", padx=12, pady=10)

        def field(parent, label):
            box = tk.Frame(parent, bg=PANEL)
            lbl = tk.Label(box, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
            lbl.pack(anchor="e")
            entry = tk.Entry(
                box,
                bg=BG,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                font=("Segoe UI", 12),
                justify="center",
                width=16,
            )
            entry.pack(pady=(4, 0), ipady=5)
            return box, entry, lbl

        # از راست به چپ: کد، تاریخ، ساعت
        code_box, self.code_entry, _ = field(row, "کد پرسنلی (۶ رقم)")
        code_box.pack(side="right", padx=8)
        self._bind_code_entry(self.code_entry)

        date_box, self.date_entry, self.date_label = field(row, "تاریخ میلادی (yyyy-mm-dd)")
        date_box.pack(side="right", padx=8)
        self._bind_date_entry(self.date_entry)

        # ستون ساعت با دکمه‌های میانبر ورود/خروج
        time_box = tk.Frame(row, bg=PANEL)
        time_box.pack(side="right", padx=8)

        entry_time_btn = self._button(
            time_box, "ورود", self._on_entry_time, bg=ACCENT, hover=ACCENT_HOVER
        )
        entry_time_btn.pack(pady=(0, 4))

        tk.Label(
            time_box,
            text="ساعت (hh:mm:ss)",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="e")

        self.time_entry = tk.Entry(
            time_box,
            bg=BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Segoe UI", 12),
            justify="center",
            width=16,
        )
        self.time_entry.pack(pady=(4, 0), ipady=5)
        self._bind_time_entry(self.time_entry)

        exit_time_btn = self._button(
            time_box, "خروج", self._on_exit_time, bg="#7c3aed", hover="#6d28d9"
        )
        exit_time_btn.pack(pady=(4, 0))

        # گزینهٔ تاریخ شمسی
        self.jalali_var = tk.BooleanVar(value=False)
        jalali_chk = tk.Checkbutton(
            row,
            text="ورود تاریخ به صورت شمسی",
            variable=self.jalali_var,
            command=self._on_jalali_toggle,
            bg=PANEL,
            fg=TEXT,
            selectcolor=BG,
            activebackground=PANEL,
            activeforeground=TEXT,
            font=("Segoe UI", 10),
        )
        jalali_chk.pack(side="right", padx=12)

        self.date_hint = tk.Label(
            form,
            text="",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.date_hint.pack(anchor="e", padx=14, pady=(0, 4))
        self._update_date_hint()

        # دکمهٔ ثبت (پایین فرم)
        submit = self._button(form, "ثبت رکورد", self._on_submit, bg=GOOD)
        submit.pack(pady=(0, 12))
        self.code_entry.bind("<Return>", lambda e: self._on_submit())
        self.date_entry.bind("<Return>", lambda e: self._on_submit())
        self.time_entry.bind("<Return>", lambda e: self._on_submit())

        # --------------------------------------------- لیست موارد اضافه‌شده
        added_frame = tk.LabelFrame(
            self.container,
            text="  موارد اضافه‌شده در این نشست  ",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            bd=1,
            relief="solid",
            labelanchor="ne",
        )
        added_frame.pack(fill="x", padx=16, pady=6)

        self.added_tree = self._make_tree(added_frame, height=4, added_style=True)
        self.added_tree.pack(fill="x", padx=8, pady=8)

        # ------------------------------------------------- لیست همهٔ رکوردها
        list_frame = tk.LabelFrame(
            self.container,
            text="  همهٔ رکوردها  ",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold"),
            bd=1,
            relief="solid",
            labelanchor="ne",
        )
        list_frame.pack(fill="both", expand=True, padx=16, pady=6)

        tree_wrap = tk.Frame(list_frame, bg=PANEL)
        tree_wrap.pack(fill="both", expand=True, padx=8, pady=8)

        self.tree = self._make_tree(tree_wrap, height=12)
        vsb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="left", fill="y")
        self.tree.pack(side="right", fill="both", expand=True)

        # ------------------------------------------------------- نوار پایین
        footer = tk.Frame(self.container, bg=BG)
        footer.pack(fill="x", padx=16, pady=(4, 14))

        exit_btn = self._button(footer, "خروج", self._on_exit, bg=DANGER)
        exit_btn.pack(side="right")

        self.status_lbl = tk.Label(
            footer,
            text="",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.status_lbl.pack(side="left")

        self._render_all()
        self.code_entry.focus_set()

    def _make_tree(self, parent, height, added_style=False):
        cols = ("row", "code", "date", "jalali", "time", "info")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        tree.heading("row", text="#")
        tree.heading("code", text="کد پرسنلی")
        tree.heading("date", text="تاریخ میلادی (yyyy-mm-dd)")
        tree.heading("jalali", text="تاریخ شمسی (yyyy/mm/dd)")
        tree.heading("time", text="ساعت (hh:mm:ss)")
        tree.heading("info", text="ستون‌های اضافی")
        tree.column("row", width=50, anchor="center", stretch=False)
        tree.column("code", width=110, anchor="center")
        tree.column("date", width=120, anchor="center")
        tree.column("jalali", width=120, anchor="center")
        tree.column("time", width=100, anchor="center")
        tree.column("info", width=160, anchor="center")
        tree.tag_configure("added", background=ADDED_BG, foreground="#dcfce7")
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
        tags = ("added",) if rec.added else ()
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

        rec = ac.Record(code=code, date=date, time=time, extra=[], added=True)
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
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    AttendanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
