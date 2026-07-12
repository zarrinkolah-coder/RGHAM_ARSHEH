# نرم افزار رقم — نسخه سروری PWA 2.0

این مخزن نسخه GitHub-ready و PWABuilder-ready نرم افزار رقم است. رابط وب به‌صورت PWA نصب‌پذیر ارائه می‌شود و داده‌ها در SQLite سرور نگهداری می‌شوند.

## اجرای سریع

پیش‌نیاز: Python 3.10 یا جدیدتر.

```bash
python server.py
```

سپس:

```text
http://localhost:8080
```

اجرای Docker:

```bash
docker compose up -d --build
```

## فایل‌های مهم PWA

- `static/manifest.webmanifest`
- `static/service-worker.js`
- `static/icons/`
- `static/.well-known/`

راهنمای کامل فارسی:

- `GITHUB_PWABUILDER_GUIDE_FA.md`
- `PWA_REVIEW_REPORT_FA.md`
- `README_SERVER_FA.md`

## داده‌های حساس

فایل‌های پایگاه داده، بکاپ، `.env` و کلیدهای امضا توسط `.gitignore` حذف شده‌اند. این فایل‌ها را به GitHub اضافه نکنید.

## بررسی خودکار

GitHub Actions با نام `Validate Ragham PWA` ساختار PWA، JavaScript، Python، SQLite و پاسخ API را آزمایش می‌کند.
