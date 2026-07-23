# -*- coding: utf-8 -*-
"""تست‌های ماژول کشیدن و رها کردن."""

import dnd_support as dnd


def test_parse_tkdnd_data():
    assert dnd._parse_tkdnd_manual(r"C:\data\file.dat") == [r"C:\data\file.dat"]
    assert dnd._parse_tkdnd_manual(r"{C:\my files\a.dat} {C:\b.dat}") == [
        r"C:\my files\a.dat",
        r"C:\b.dat",
    ]
    assert dnd.parse_tkdnd_data(None, "/home/user/file.txt") == ["/home/user/file.txt"]
    print("OK parse tkdnd data")


def test_normalize_dropped_path():
    assert dnd.normalize_dropped_path(' "abc.dat" ') == "abc.dat"
    assert dnd.normalize_dropped_path("file:///home/user/file.dat") == "/home/user/file.dat"
    print("OK normalize dropped path")


if __name__ == "__main__":
    test_parse_tkdnd_data()
    test_normalize_dropped_path()
    print("\nهمه‌ی تست‌های DnD با موفقیت اجرا شدند")
