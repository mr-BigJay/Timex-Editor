# -*- coding: utf-8 -*-
"""
نرم‌افزار مدیریت رکوردهای ورود و خروج
Attendance (check-in/out) records manager.

قابلیت‌ها:
- باز شدن با یک کادر «کشیدن و رها کردن» (Drag & Drop) در وسط صفحه برای گرفتن فایل.
- خواندن فایل رکوردها و نمایش آن‌ها در یک لیست.
- فرم ثبت رکورد در بالای صفحه (کد ۶ رقمی، تاریخ، ساعت) با دکمهٔ ثبت.
- امکان ورود تاریخ به صورت شمسی و ذخیرهٔ آن به صورت میلادی.
- نمایش قالب پیش‌فرض فیلدها: ساعت `HH:MM:SS`، تاریخ میلادی `YYYY-MM-DD`، تاریخ شمسی `YYYY/MM/DD`.
- نمایش «لیست موارد اضافه‌شده» بین فرم و لیست اصلی.
- اسکرول خودکار و ریل‌تایم لیست به محل رکورد تازه ثبت‌شده.
- دکمه‌های «ذخیره» و «ذخیره با نام...» با مسیر پیش‌فرض امن کنار فایل اصلی.
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
        self.root.title(APP_TITLE)
        self.root.geometry("1000x760")
        self.root.minsize(820, 620)
        self.root.configure(bg=BG)

        self.records: list[ac.Record] = []
        self.source_path: str | None = None
        self.save_path: str | None = None
        self.dirty = False
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
    def _button(self, parent, text, command, bg=ACCENT, fg="white", width=None):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=ACCENT_HOVER,
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

    def _clear_container(self):
        for child in self.container.winfo_children():
            child.destroy()

    def _entry_value(self, entry: tk.Entry) -> str:
        if getattr(entry, "_placeholder_active", False):
            return ""
        return entry.get().strip()

    def _set_placeholder(self, entry: tk.Entry, placeholder: str):
        entry._placeholder_text = placeholder
        entry.delete(0, "end")
        entry.insert(0, placeholder)
        entry.configure(fg=MUTED)
        entry._placeholder_active = True

    def _clear_placeholder(self, entry: tk.Entry):
        if getattr(entry, "_placeholder_active", False):
            entry.delete(0, "end")
            entry.configure(fg=TEXT)
            entry._placeholder_active = False

    def _restore_placeholder(self, entry: tk.Entry):
        if entry.get().strip():
            entry.configure(fg=TEXT)
            entry._placeholder_active = False
            return
        placeholder = getattr(entry, "_placeholder_text", "")
        if placeholder:
            self._set_placeholder(entry, placeholder)

    def _bind_placeholder(self, entry: tk.Entry, placeholder: str):
        entry.bind("<FocusIn>", lambda _event, e=entry: self._clear_placeholder(e))
        entry.bind("<FocusOut>", lambda _event, e=entry: self._restore_placeholder(e))
        self._set_placeholder(entry, placeholder)

    def _update_placeholder(self, entry: tk.Entry, placeholder: str):
        entry._placeholder_text = placeholder
        if getattr(entry, "_placeholder_active", False) or not entry.get().strip():
            self._set_placeholder(entry, placeholder)

    # ============================================================ DROP SCREEN
    def show_drop_screen(self):
        """حالت اولیه: کادر کشیدن و رها کردن در وسط صفحه."""
        self._clear_container()
        self.records = []
        self.source_path = None
        self.save_path = None
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
            filetypes=[("فایل متنی", "*.txt"), ("همهٔ فایل‌ها", "*.*")],
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
        self.save_path = ac.suggested_save_path(path)
        self.dirty = False
        self.show_editor_screen()

    # ========================================================== EDITOR SCREEN
    def show_editor_screen(self):
        self._clear_container()

        # نوار عنوان فایل
        header = tk.Frame(self.container, bg=BG)
        header.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(
            header,
            text="فایل باز شده:",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(side="right")
        tk.Label(
            header,
            text=self.source_path or "",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="right", padx=(0, 6))

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

        def field(parent, label, placeholder=None):
            box = tk.Frame(parent, bg=PANEL)
            tk.Label(box, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="e")
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
            if placeholder:
                self._bind_placeholder(entry, placeholder)
            return box, entry

        # از راست به چپ: کد، تاریخ، ساعت
        code_box, self.code_entry = field(row, "کد پرسنلی (۶ رقم)")
        code_box.pack(side="right", padx=8)

        date_box, self.date_entry = field(row, "تاریخ", "YYYY-MM-DD")
        date_box.pack(side="right", padx=8)

        time_box, self.time_entry = field(row, "ساعت", "HH:MM:SS")
        time_box.pack(side="right", padx=8)

        # گزینهٔ تاریخ شمسی
        self.jalali_var = tk.BooleanVar(value=False)
        jalali_chk = tk.Checkbutton(
            row,
            text="ورود تاریخ به صورت شمسی",
            variable=self.jalali_var,
            command=self._update_date_hint,
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

        self.status_lbl = tk.Label(
            footer,
            text="",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.status_lbl.pack(side="right")

        exit_btn = self._button(footer, "خروج", self._on_exit, bg=DANGER)
        exit_btn.pack(side="left", padx=(0, 8))

        save_as_btn = self._button(footer, "ذخیره با نام...", self._on_save_as, bg=ACCENT)
        save_as_btn.pack(side="left")

        save_btn = self._button(footer, "ذخیره", self._on_save, bg=GOOD)
        save_btn.pack(side="left")

        self._render_all()
        self.code_entry.focus_set()

    def _make_tree(self, parent, height, added_style=False):
        cols = ("row", "code", "date", "jalali", "time", "info")
        tree = ttk.Treeview(parent, columns=cols, show="headings", height=height)
        tree.heading("row", text="#")
        tree.heading("code", text="کد پرسنلی")
        tree.heading("date", text="تاریخ میلادی")
        tree.heading("jalali", text="تاریخ شمسی")
        tree.heading("time", text="ساعت")
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
            self.date_hint.config(text="نمونهٔ شمسی: 1405/04/01  ← هنگام ذخیره به میلادی تبدیل می‌شود")
            self._update_placeholder(self.date_entry, "YYYY/MM/DD")
        else:
            self.date_hint.config(text="نمونهٔ میلادی: 2026-06-22")
            self._update_placeholder(self.date_entry, "YYYY-MM-DD")

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
        target = f"   |   مقصد ذخیره: {os.path.basename(self.save_path)}" if self.save_path else ""
        self.status_lbl.config(
            text=f"مجموع رکوردها: {total}   |   اضافه‌شده: {added}{star}{target}"
        )

    # ------------------------------------------------------------------ actions
    def _on_submit(self):
        try:
            code = ac.normalize_code(self.code_entry.get())
            date = ac.normalize_date(self._entry_value(self.date_entry), jalali=self.jalali_var.get())
            time = ac.normalize_time(self._entry_value(self.time_entry))
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
        self._restore_placeholder(self.time_entry)
        self.code_entry.focus_set()

    def _save_to_path(self, path: str):
        if self.source_path and os.path.abspath(path) == os.path.abspath(self.source_path):
            if not messagebox.askyesno(
                APP_TITLE,
                "این همان فایل اصلی است و ذخیره، آن را بازنویسی می‌کند.\n"
                "آیا مطمئن هستید که می‌خواهید ادامه دهید؟",
            ):
                return False
        ordered = sorted(self.records, key=lambda r: r.sort_key)
        try:
            ac.write_records(path, ordered)
        except Exception as exc:  # pragma: no cover
            messagebox.showerror(APP_TITLE, f"خطا در ذخیره:\n{exc}")
            return False
        self.save_path = path
        self.dirty = False
        self._update_status()
        messagebox.showinfo(APP_TITLE, f"با موفقیت ذخیره شد:\n{path}")
        return True

    def _on_save(self):
        if not self.records:
            messagebox.showinfo(APP_TITLE, "رکوردی برای ذخیره وجود ندارد.")
            return
        path = self.save_path or ac.suggested_save_path(self.source_path or "")
        self._save_to_path(path)

    def _on_save_as(self):
        if not self.records:
            messagebox.showinfo(APP_TITLE, "رکوردی برای ذخیره وجود ندارد.")
            return
        initial_path = self.save_path or ac.suggested_save_path(self.source_path or "")
        initial_dir = os.path.dirname(os.path.abspath(initial_path))
        initial_file = os.path.basename(initial_path)
        path = filedialog.asksaveasfilename(
            title="ذخیره به صورت (Save As)",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".txt",
            filetypes=[("فایل متنی", "*.txt"), ("همهٔ فایل‌ها", "*.*")],
        )
        if not path:
            return
        self._save_to_path(path)

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
                self._on_save()
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
