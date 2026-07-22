# -*- coding: utf-8 -*-
"""تست‌های ساده برای منطق اصلی (بدون نیاز به گرافیک)."""

import os
import tempfile

import attendance_core as ac


def test_jalali_roundtrip():
    # چند تاریخ مرجع شناخته‌شده
    assert ac.jalali_to_gregorian(1405, 4, 1) == (2026, 6, 22)
    assert ac.gregorian_to_jalali(2026, 6, 22) == (1405, 4, 1)
    # رفت و برگشت
    for gy, gm, gd in [(2026, 6, 22), (2000, 1, 1), (2024, 2, 29), (1990, 12, 31)]:
        jy, jm, jd = ac.gregorian_to_jalali(gy, gm, gd)
        assert ac.jalali_to_gregorian(jy, jm, jd) == (gy, gm, gd)
    print("OK jalali roundtrip")


def test_normalize_date():
    assert ac.normalize_date("2026-06-22", jalali=False) == "2026-06-22"
    assert ac.normalize_date("2026/06/22", jalali=False) == "2026-06-22"
    assert ac.normalize_date("1405/04/01", jalali=True) == "2026-06-22"
    assert ac.normalize_date("1405-4-1", jalali=True) == "2026-06-22"
    print("OK normalize date")


def test_date_string_conversions():
    # میلادی -> شمسی و برعکس با قالب‌های پیش‌فرض
    assert ac.gregorian_str_to_jalali_str("2026-06-22") == "1405/04/01"
    assert ac.jalali_str_to_gregorian_str("1405/04/01") == "2026-06-22"
    # پذیرش جداکننده‌های مختلف در ورودی، خروجی همیشه با قالب استاندارد
    assert ac.jalali_str_to_gregorian_str("1405-04-01") == "2026-06-22"
    assert ac.gregorian_str_to_jalali_str("2026/06/22") == "1405/04/01"
    # ورودی نامعتبر رشته خالی برمی‌گرداند
    assert ac.gregorian_str_to_jalali_str("نامعتبر") == ""
    assert ac.jalali_str_to_gregorian_str("") == ""
    print("OK date string conversions")


def test_default_formats():
    from datetime import datetime

    now = datetime(2026, 6, 22, 7, 39, 5)
    assert ac.today_gregorian_str(now) == "2026-06-22"
    assert ac.today_jalali_str(now) == "1405/04/01"
    assert ac.now_time_str(now) == "07:39:05"
    print("OK default formats")


def test_normalize_time_code():
    assert ac.normalize_time("7:39:23") == "07:39:23"
    assert ac.normalize_time("07:39") == "07:39:00"
    assert ac.normalize_code("308590") == "308590"
    for bad in ["30859", "3085900", "abcdef"]:
        try:
            ac.normalize_code(bad)
            assert False, "should have failed: " + bad
        except ValueError:
            pass
    print("OK time/code")


def test_parse_line():
    line = "   308590\t2026-06-22 07:12:45\t1\t0\t1\t0"
    rec = ac.parse_line(line)
    assert rec.code == "308590"
    assert rec.date == "2026-06-22"
    assert rec.time == "07:12:45"
    assert rec.extra == ["1", "0", "1", "0"]
    # قالب دو ستونه بدون ستون اضافی
    rec2 = ac.parse_line("308590\t2026-06-28 07:39:23")
    assert rec2.code == "308590"
    assert rec2.date == "2026-06-28"
    assert rec2.time == "07:39:23"
    assert rec2.extra == []
    # فاصله به جای تب
    rec3 = ac.parse_line("308590 2026-06-28 07:39:23")
    assert rec3.code == "308590" and rec3.date == "2026-06-28" and rec3.time == "07:39:23"
    print("OK parse line")


def test_to_line_roundtrip():
    rec = ac.Record(code="308590", date="2026-06-22", time="07:12:45", extra=["1", "0", "1", "0"])
    assert rec.to_line() == "308590\t2026-06-22 07:12:45\t1\t0\t1\t0"
    rec2 = ac.Record(code="123456", date="2026-06-28", time="07:39:23")
    assert rec2.to_line() == "123456\t2026-06-28 07:39:23"
    print("OK to_line")


def test_read_write():
    content = (
        "   308590\t2026-06-22 07:12:45\t1\t0\t1\t0\n"
        "   308234\t2026-06-22 07:38:52\t1\t0\t16\t0\n"
    )
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "records.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write(content)
        recs = ac.read_records(src)
        assert len(recs) == 2
        # افزودن رکورد جدید
        recs.append(ac.Record(code="999999", date="2026-06-28", time="08:00:00", added=True))
        out = os.path.join(d, "records_edited.txt")
        ac.write_records(out, recs)
        recs2 = ac.read_records(out)
        assert len(recs2) == 3
        assert recs2[2].code == "999999"
        # مسیر پیشنهادی
        sp = ac.suggested_save_path(src)
        assert sp.endswith("records_edited.txt")
    print("OK read/write")


if __name__ == "__main__":
    test_jalali_roundtrip()
    test_normalize_date()
    test_date_string_conversions()
    test_default_formats()
    test_normalize_time_code()
    test_parse_line()
    test_to_line_roundtrip()
    test_read_write()
    print("\nهمه‌ی تست‌ها با موفقیت اجرا شدند / All tests passed")
