پس از ساخت بسته Android در PWABuilder، فایل assetlinks.json تولیدشده توسط PWABuilder را دقیقاً در همین پوشه قرار دهید:

static/.well-known/assetlinks.json

پس از استقرار مجدد، فایل باید از آدرس زیر بدون ورود و بدون تغییر مسیر باز شود:

https://YOUR-DOMAIN/.well-known/assetlinks.json

از فایل نمونه به‌عنوان فایل نهایی استفاده نکنید؛ نام بسته و اثر انگشت گواهی باید دقیقاً از خروجی PWABuilder برداشته شود.
