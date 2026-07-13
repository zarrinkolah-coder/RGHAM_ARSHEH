# راهنمای مبتدی: GitHub، استقرار HTTPS و ساخت فایل نصب با PWABuilder

## نکته اصلی

GitHub محل نگهداری کد است. چون نرم افزار رقم دارای Python، API و SQLite است، **GitHub Pages به‌تنهایی قادر به اجرای نسخه اصلی نیست**. ابتدا کد را در GitHub قرار دهید، سپس همان مخزن را روی یک سرویس یا سرور دارای Python/Docker و دیسک دائمی مستقر کنید. آدرس HTTPS حاصل را به PWABuilder بدهید.

## ۱) بارگذاری در GitHub

1. فایل ZIP را روی رایانه Extract کنید.
2. یک Repository جدید و ترجیحاً Private بسازید.
3. همه محتویات داخل پوشه استخراج‌شده را در ریشه مخزن بارگذاری کنید؛ خود ZIP را به‌تنهایی بارگذاری نکنید.
4. در صفحه اصلی مخزن باید `server.py`، `static`، `Dockerfile` و `.github` دیده شوند.
5. پوشه `data` فقط باید فایل `.gitkeep` داشته باشد. فایل `ragham.sqlite3` را هرگز Commit نکنید.
6. از تب Actions نتیجه گردش‌کار **Validate Ragham PWA** را بررسی کنید. علامت سبز یعنی ساختار و تست‌های پایه درست هستند.

## ۲) اجرای آزمایشی روی رایانه

ویندوز:

```bat
start_windows.bat
```

لینوکس:

```bash
chmod +x start_linux.sh
./start_linux.sh
```

مرورگر:

```text
http://localhost:8080
```

## ۳) استقرار روی سرور HTTPS

روی هر میزبان Docker می‌توانید از `Dockerfile` استفاده کنید. دیسک دائمی باید به مسیر `/app/data` متصل شود. متغیرهای لازم در `.env.example` آمده‌اند.

پس از استقرار، این آدرس‌ها را بررسی کنید:

```text
https://YOUR-DOMAIN/
https://YOUR-DOMAIN/manifest.webmanifest
https://YOUR-DOMAIN/service-worker.js
https://YOUR-DOMAIN/api/health
```

برای PWABuilder، دامنه باید گواهی HTTPS معتبر داشته باشد. استفاده از IP یا HTTP شبکه داخلی برای بسته نهایی مناسب نیست.

## ۴) ساخت بسته در PWABuilder

1. وارد PWABuilder شوید.
2. آدرس HTTPS صفحه اصلی برنامه را وارد کنید؛ نه آدرس GitHub و نه فایل ZIP.
3. بررسی Manifest و Service Worker را اجرا کنید.
4. بخش Package for stores و سپس Android را انتخاب کنید.
5. نام بسته پیشنهادی: `com.ragham.app`.
6. بسته را بسازید و ZIP خروجی PWABuilder را در محل امن نگهداری کنید. این خروجی معمولاً فایل آزمایشی APK و فایل AAB مخصوص فروشگاه را در اختیار شما قرار می‌دهد.
7. فایل امضا و اطلاعات کلید خروجی را حذف نکنید؛ برای بروزرسانی نسخه‌های بعدی لازم است.

## ۵) حذف نوار مرورگر با assetlinks.json

PWABuilder برای Android فایلی به نام `assetlinks.json` می‌دهد. آن را در مسیر زیر پروژه قرار دهید:

```text
static/.well-known/assetlinks.json
```

سپس Commit و Deploy مجدد کنید و مطمئن شوید این نشانی باز می‌شود:

```text
https://YOUR-DOMAIN/.well-known/assetlinks.json
```

فایل باید دقیقاً شامل نام بسته و اثر انگشت گواهی همان خروجی PWABuilder باشد. فایل نمونه موجود در پروژه را مستقیماً استفاده نکنید.

## ۶) بروزرسانی برنامه

برای تغییرات رابط و منطق وب، فایل‌ها را در GitHub بروزرسانی و سرور را مجدداً Deploy کنید. Service Worker نسخه جدید را دریافت کرده و داخل برنامه اعلان بروزرسانی نمایش می‌دهد. برای تغییر نام بسته، کلید امضا یا تنظیمات اصلی Android باید بسته جدید PWABuilder ساخته شود.

## خطاهای متداول

- PWABuilder آدرس را نمی‌پذیرد: HTTPS یا دسترسی عمومی دامنه را بررسی کنید.
- Manifest پیدا نمی‌شود: `https://YOUR-DOMAIN/manifest.webmanifest` را مستقیم باز کنید.
- Service Worker فعال نیست: سایت باید HTTPS باشد و `service-worker.js` با وضعیت ۲۰۰ باز شود.
- برنامه نوار مرورگر نشان می‌دهد: `assetlinks.json` اشتباه است، در ریشه دامنه نیست یا بسته با کلید دیگری امضا شده است.
- اطلاعات پس از Deploy پاک می‌شود: دیسک دائمی `/app/data` تنظیم نشده است.
