# -*- coding: utf-8 -*-
"""
منطق اصلی نرم‌افزار مدیریت رکوردهای ورود و خروج
Core logic for the attendance (check-in/out) records tool.

این ماژول هیچ وابستگی گرافیکی ندارد تا بتوان آن را جداگانه تست کرد.
This module has no GUI dependency so it can be unit tested on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ---------------------------------------------------------------------------
# تبدیل تاریخ شمسی <-> میلادی  (بدون هیچ کتابخانه خارجی)
# Jalali <-> Gregorian conversion (pure python, no external dependency)
# الگوریتم مرسوم jdf
# ---------------------------------------------------------------------------
def gregorian_to_jalali(gy: int, gm: int, gd: int):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
        + g_d_m[gm - 1]
    )
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int):
    if jy > 979:
        gy = 1600
        jy -= 979
    else:
        gy = 621
    days = (
        365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + 78
        + jd
        + ((jm - 1) * 31 if jm < 7 else (jm - 7) * 30 + 186)
    )
    gy += 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    is_leap = (gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)
    sal_a = [0, 31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


# ---------------------------------------------------------------------------
# کمکی‌های اعتبارسنجی و نرمال‌سازی ورودی‌ها
# Validation / normalization helpers
# ---------------------------------------------------------------------------
def _split_date(text: str):
    """جدا کردن اجزای تاریخ که با - یا / یا . نوشته شده باشد."""
    text = (text or "").strip()
    for sep in ("-", "/", "."):
        if sep in text:
            parts = text.split(sep)
            break
    else:
        parts = text.split()
    parts = [p for p in parts if p != ""]
    if len(parts) != 3:
        raise ValueError("قالب تاریخ باید سال-ماه-روز باشد (مثال: 2026-06-22)")
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError("اجزای تاریخ باید عددی باشند")
    return y, m, d


def normalize_date(text: str, jalali: bool) -> str:
    """
    ورودی تاریخ را (شمسی یا میلادی) گرفته و تاریخ میلادی به صورت YYYY-MM-DD برمی‌گرداند.
    Take a date string (Jalali or Gregorian) and return Gregorian YYYY-MM-DD.
    """
    y, m, d = _split_date(text)
    if jalali:
        gy, gm, gd = jalali_to_gregorian(y, m, d)
    else:
        gy, gm, gd = y, m, d
    # اعتبارسنجی نهایی با datetime
    dt = datetime(gy, gm, gd)
    return dt.strftime("%Y-%m-%d")


def gregorian_str_to_jalali_str(date_str: str) -> str:
    """YYYY-MM-DD میلادی -> رشته شمسی YYYY/MM/DD برای نمایش."""
    try:
        y, m, d = _split_date(date_str)
        jy, jm, jd = gregorian_to_jalali(y, m, d)
        return f"{jy:04d}/{jm:02d}/{jd:02d}"
    except Exception:
        return ""


def normalize_time(text: str) -> str:
    """زمان را به صورت HH:MM:SS استاندارد می‌کند. HH:MM هم پذیرفته می‌شود."""
    text = (text or "").strip()
    if not text:
        raise ValueError("ساعت را وارد کنید")
    parts = text.split(":")
    if len(parts) == 2:
        parts.append("0")
    if len(parts) != 3:
        raise ValueError("قالب ساعت باید HH:MM:SS باشد (مثال: 07:39:23)")
    try:
        h, mi, s = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        raise ValueError("اجزای ساعت باید عددی باشند")
    if not (0 <= h < 24 and 0 <= mi < 60 and 0 <= s < 60):
        raise ValueError("مقدار ساعت خارج از محدوده مجاز است")
    return f"{h:02d}:{mi:02d}:{s:02d}"


def normalize_partial_record(date: str, time: str) -> tuple[str, str]:
    """
    در صورت معتبر بودن، تاریخ/ساعت رکوردهای خوانده‌شده از فایل را به فرمت استاندارد
    برنامه تبدیل می‌کند. اگر بخشی نامعتبر یا خالی باشد، همان مقدار قبلی حفظ می‌شود.
    """
    normalized_date = date
    normalized_time = time

    if date:
        try:
            normalized_date = normalize_date(date, jalali=False)
        except ValueError:
            pass
    if time:
        try:
            normalized_time = normalize_time(time)
        except ValueError:
            pass
    return normalized_date, normalized_time


def normalize_code(text: str) -> str:
    """کد پرسنلی باید ۶ رقم باشد."""
    text = (text or "").strip()
    if not text.isdigit():
        raise ValueError("کد پرسنلی باید فقط عدد باشد")
    if len(text) != 6:
        raise ValueError("کد پرسنلی باید دقیقاً ۶ رقم باشد")
    return text


# ---------------------------------------------------------------------------
# مدل رکورد
# Record model
# ---------------------------------------------------------------------------
@dataclass
class Record:
    code: str
    date: str  # میلادی YYYY-MM-DD
    time: str  # HH:MM:SS
    extra: List[str] = field(default_factory=list)  # ستون‌های اضافیِ فایل اصلی
    added: bool = False  # آیا در این نشست اضافه شده است؟
    raw: Optional[str] = None  # خط خام فایل اصلی (برای حفظ عین قالب)

    @property
    def sort_key(self):
        return (self.date, self.time, self.code)

    def to_line(self) -> str:
        """
        تبدیل رکورد به یک خط برای ذخیره‌سازی.
        قالب: کد <TAB> «تاریخ ساعت» <TAB> ستون‌های اضافی ...
        """
        fields = [self.code, f"{self.date} {self.time}"]
        fields.extend(self.extra)
        return "\t".join(fields)


def parse_line(line: str) -> Optional[Record]:
    """
    یک خط از فایل را تجزیه می‌کند.
    قالب مورد انتظار: کد <جداکننده> تاریخ ساعت <جداکننده> ستون‌های اضافی...
    جداکننده معمولاً TAB است ولی فاصله هم پشتیبانی می‌شود.
    """
    if line is None:
        return None
    stripped = line.strip()
    if not stripped:
        return None

    # ابتدا تلاش با TAB (قالب استاندارد فایل)
    if "\t" in line:
        parts = [p.strip() for p in line.rstrip("\n").split("\t")]
        parts = [p for p in parts if p != ""]
    else:
        parts = stripped.split()

    if not parts:
        return None

    code = parts[0]

    # پیدا کردن تاریخ و ساعت
    date = ""
    time = ""
    extra: List[str] = []

    rest = parts[1:]
    # حالت ۱: تاریخ و ساعت داخل یک فیلد با فاصله ("2026-06-22 07:12:45")
    if rest and (" " in rest[0]) and ("-" in rest[0] or "/" in rest[0]):
        dt_parts = rest[0].split()
        date = dt_parts[0]
        time = dt_parts[1] if len(dt_parts) > 1 else ""
        extra = rest[1:]
    else:
        # حالت ۲: تاریخ و ساعت در دو فیلد جدا
        if len(rest) >= 2 and ("-" in rest[0] or "/" in rest[0]) and (":" in rest[1]):
            date = rest[0]
            time = rest[1]
            extra = rest[2:]
        elif len(rest) >= 1 and ("-" in rest[0] or "/" in rest[0]):
            date = rest[0]
            extra = rest[1:]
        else:
            extra = rest

    date = date.replace("/", "-")
    date, time = normalize_partial_record(date, time)
    return Record(code=code, date=date, time=time, extra=extra, added=False, raw=line.rstrip("\n"))


def read_records(path: str) -> List[Record]:
    """خواندن همه رکوردها از فایل."""
    records: List[Record] = []
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            rec = parse_line(line)
            if rec is not None:
                records.append(rec)
    return records


def write_records(path: str, records: List[Record]) -> None:
    """نوشتن همه رکوردها در فایل مقصد."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for rec in records:
            fh.write(rec.to_line() + "\n")


def suggested_save_path(source_path: str) -> str:
    """
    مسیر پیشنهادی برای ذخیره کنار فایل اصلی.
    Suggested save path right next to the original file.
    """
    if not source_path:
        return "attendance_records.txt"
    folder = os.path.dirname(os.path.abspath(source_path))
    base = os.path.basename(source_path)
    name, ext = os.path.splitext(base)
    if not ext:
        ext = ".txt"
    return os.path.join(folder, f"{name}_edited{ext}")
