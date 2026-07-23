# نرم‌افزار مدیریت رکوردهای ورود و خروج

یک برنامهٔ رومیزی سبک برای خواندن فایل رکوردهای ورود/خروج، افزودن رکورد جدید و
ذخیرهٔ آن‌ها در یک فایل جدید (بدون بازنویسی فایل اصلی).

## اجرای سریع (ویندوز)

| فایل | کار |
|------|-----|
| **`TimexEditor.exe`** | اجرای مستقیم — بدون نیاز به Python (پس از ساخت) |
| **`run.vbs`** | اجرای بدون CMD (نیاز به Python) |
| **`START.bat`** | اجرای جایگزین — خطا را نشان می‌دهد |
| **`run.bat`** | همان `run.vbs` بدون پنجره |

### ساخت فایل exe

روی ویندوز:

```bat
scripts\build_exe.bat
```

فایل `TimexEditor.exe` در پوشهٔ اصلی ساخته می‌شود.

یا از GitHub Actions: بخش **Actions → Build Windows EXE → Run workflow** و فایل exe را از Artifacts دانلود کنید.

## قابلیت‌ها

- **کشیدن و رها کردن** فایل `.dat` / `.txt` در وسط صفحه
- **فرم ثبت رکورد**: کد ۶ رقمی، تاریخ (شمسی/میلادی)، ساعت
- **دکمه‌های ورود/خروج** برای ساعت تصادفی
- **ذخیره Save As** — فایل اصلی بازنویسی نمی‌شود
- **حفظ قالب فایل** — فقط رکوردهای جدید اضافه می‌شوند

## اجرا با Python

```bash
pip install -r requirements.txt
python attendance_app.pyw
```

یا:

```bash
python -m app.attendance_app
```

## تست

```bash
python tests/test_core.py
python tests/test_dnd_support.py
```

## ساختار پوشه‌ها

```
Timex-Editor/
├── TimexEditor.exe       ← فایل اجرایی (پس از build)
├── run.vbs / START.bat   ← لانچرها
├── attendance_app.pyw    ← نقطهٔ ورود Python
├── requirements.txt
├── app/                  ← کد اصلی برنامه
│   ├── attendance_app.py
│   ├── attendance_core.py
│   ├── dnd_support.py
│   └── win32_dnd.py
├── tests/                ← تست‌ها
├── scripts/              ← build_exe.bat، create_shortcut.vbs
├── samples/              ← نمونه فایل
└── build/                ← تنظیمات PyInstaller
```

## ابزارها

- `scripts\create_shortcut.vbs` — ساخت میانبر روی دسکتاپ
- `scripts\build_exe.bat` — ساخت `TimexEditor.exe`

## قالب فایل رکورد

```
   308590	2026-06-22 07:12:45	1	0	1	0
```

نمونه: `samples/sample_records.txt`
