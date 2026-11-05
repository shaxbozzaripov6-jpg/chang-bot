# 🌪 Chang Monitor: chang va qum bo'ronlari bo'yicha Telegram bot

Bu bot O'zbekiston shaharlarida chang darajasini (PM10, PM2.5, chang) ko'rsatadi. U 3 kunlik prognoz va grafik beradi, obunachilarni chang bo'ronidan oldin ogohlantiradi va har kuni ertalab hisobot yuboradi.

**Imkoniyatlar:**
- 🌐 **Uch til**: o'zbekcha, ruscha va inglizcha (/til)
- 🏙 **Shahar rasmlari**: har bir shaharning o'ziga xos manzarasi (Registon, Minorai Kalon, teleminora, Mo'ynoq kemalari va boshqalar) bot tomonidan chiziladi. Osmon hozirgi ob-havoga mos keladi: quyosh, oy va yulduzlar, bulut, yomg'ir, qor, tuman, momaqaldiroq yoki chang bo'roni
- 🌤 **Ob-havo**: harorat, namlik, yog'in, shamol tezligi va yo'nalishi; kuchli shamol (shiddati 15 m/s dan yuqori) haqida ogohlantirish
- 📊 **Grafik**: 72 soatlik chang prognozi va pastida shamol tezligi, shiddati va yo'nalishi strelkalari (/grafik)
- 📸 **Bo'ron xabarlari**: foydalanuvchilar bo'ron rasmini yuboradi, admin tasdiqlaydi va bot rasmni 100 km radiusdagi obunachilarga jo'natadi (/xabar, /xabarlar)
Chang va ob-havo ma'lumotlari bepul Open-Meteo / Copernicus CAMS xizmatidan olinadi, buning uchun API kalit kerak emas.

## Papkada nimalar bor

| Fayl | Vazifasi |
|---|---|
| `bot.py` | Asosiy dastur: tugmalar, buyruqlar, avtomatik ogohlantirishlar |
| `api.py` | Internetdan chang ma'lumotlarini oladi |
| `db.py` | Foydalanuvchilar va ularning sozlamalarini saqlaydi (SQLite bazasi) |
| `texts.py` | Barcha matnlar (o'zbek va rus), shaharlar, maslahatlar. **Bot gaplarini o'zgartirish uchun shu faylni tahrirlang** |
| `chart.py` | Chang va shamol grafigini chizadi |
| `scene.py` | Shahar manzarasi va ob-havoga mos osmonni chizadi |
| `requirements.txt` | Botga kerakli kutubxonalar ro'yxati |
| `Procfile` | Hosting xizmatiga botni qanday ishga tushirishni aytadi |
| `.env.example` | Sozlamalar fayli namunasi |

---

# Qadamma-qadam qo'llanma (tajriba talab qilinmaydi)

## 1-qadam: Telegramda bot yaratish (5 daqiqa)
1. Telegramni oching va **@BotFather**ni qidiring (yonida ko'k belgi bor).
2. `/newbot` deb yozing.
3. Botga **nom** bering, masalan: `Chang Monitor`.
4. **Username** bering. U `bot` bilan tugashi shart, masalan: `chang_monitor_uz_bot`.
5. BotFather sizga **token** yuboradi, masalan: `7123456789:AAH...xyz`.
   ⚠️ Token botingizning paroli. **Uni hech kimga bermang va internetga joylamang.**
6. Ixtiyoriy: buyruqlar menyusini qo'shish uchun BotFather'ga `/setcommands` deb yozing, botingizni tanlang va quyidagini yuboring:
   ```
   havo - Hozirgi chang holati
   prognoz - 3 kunlik prognoz
   grafik - Chang grafigi
   shahar - Shaharni tanlash
   xabar - Bo'ron rasmini yuborish
   xabarlar - Yaqin atrofdagi bo'ron xabarlari
   obuna - Ogohlantirishlar
   maslahat - Sog'liq maslahatlari
   malumot - Chang bo'ronlari haqida
   til - Til / Язык / Language
   help - Yordam
   ```

## 2-qadam: O'z kompyuteringizda sinab ko'rish (ixtiyoriy, 15 daqiqa)
Bu qadam botning qanday ishlashini tushunishga yordam beradi. Uni o'tkazib yuborib, to'g'ridan-to'g'ri 3-qadamga o'tishingiz ham mumkin.
1. https://python.org/downloads saytidan **Python 3.12+** ni o'rnating. Windows'da o'rnatish paytida **"Add Python to PATH"** belgisini qo'ying.
2. Loyiha arxivini (zip) oching.
3. `.env.example` faylidan nusxa olib, uni `.env` deb nomlang. `BOT_TOKEN=` dan keyin tokeningizni yozing.
4. **Shu papka ichida** terminal oching. Windows'da papkaning manzil satriga bosing, `cmd` deb yozing va Enter bosing.
5. Quyidagilarni yozing:
   ```
   pip install -r requirements.txt
   python bot.py
   ```
6. `Bot ishga tushdi` yozuvi chiqqach, Telegramda botingizni ochib **Start** tugmasini bosing. 🎉
   Bot faqat shu oyna ochiq turganda ishlaydi. To'xtatish uchun `Ctrl+C` bosing.

## 3-qadam: Kodni GitHub'ga joylash (10 daqiqa)
Hosting xizmati kodingizni GitHub'dan oladi.
1. https://github.com saytida ro'yxatdan o'ting.
2. Yuqori o'ngdagi **+** tugmasini, keyin **New repository** ni bosing. Nomini `chang-bot` qo'ying, **Private** ni tanlang va **Create** ni bosing.
3. **"uploading an existing file"** havolasini bosing. **`.env` dan tashqari** barcha fayllarni sudrab tashlang, keyin **Commit changes** ni bosing.
   ⚠️ `.env` faylini hech qachon yuklamang, chunki ichida tokeningiz bor.

## 4-qadam: Railway'da 24/7 ishga tushirish (10 daqiqa)
1. https://railway.com saytiga kiring va **GitHub orqali kiring** (Sign in with GitHub).
2. **New Project**, keyin **Deploy from GitHub repo** ni bosing va `chang-bot` ni tanlang.
3. Xizmatingizni bosing, **Variables** bo'limini oching va quyidagilarni qo'shing:
   - `BOT_TOKEN` = tokeningiz
   - `DB_PATH` = `/data/chang_bot.db`
4. Xizmat ustida o'ng tugmani bosing (yoki **+** tugmasi orqali) **Add Volume** ni tanlang va mount path'ga `/data` yozing.
   Busiz botni har safar yangilaganingizda obunachilar ro'yxati o'chib ketadi.
5. **Settings**, keyin **Deploy** bo'limida **Custom Start Command** ga `python bot.py` deb yozing.
6. **Deployments** bo'limida **View logs** ni bosing. `Bot ishga tushdi` yozuvini ko'rsangiz, bot 24/7 ishlayapti. ✅

💰 Railway bepul sinov muddati beradi. Undan keyin Hobby tarifi oyiga taxminan **5$** turadi, bu bot uchun bemalol yetadi.
Boshqa variantlar: kichik VPS server (Hetzner, DigitalOcean, oyiga taxminan 4–6$) yoki doim yoqilib turadigan ortiqcha kompyuter.

## 5-qadam: Keyinchalik botni yangilash
GitHub'da faylni tahrirlang: faylni bosing, ✏️ qalam belgisini bosing, keyin **Commit** qiling. Railway botni yangi kod bilan avtomatik qayta ishga tushiradi.

---

## Ogohlantirishlar qanday ishlaydi
- Bot har soatda har bir obunachining joyi uchun keyingi 24 soatlik prognozni tekshiradi.
- Agar **PM10 ≥ 250** yoki **chang ≥ 200 µg/m³** bo'lsa, 🚨 ogohlantirish yuboradi. Bitta odamga 12 soatda ko'pi bilan 1 marta yuboriladi.
- `DAILY_HOUR` soatida (sukut bo'yicha Toshkent vaqti bilan 07:00) kunlik hisobotni yoqqanlarga ertalabki hisobot yuboradi.
- Chegaralarni `texts.py` faylida (`ALERT_PM10`, `ALERT_DUST`) o'zgartirishingiz mumkin.

## Bo'ron xabarlari qanday ishlaydi
1. Foydalanuvchi botga rasm yuboradi (izoh bilan yoki izohsiz). Bir kishi 24 soatda ko'pi bilan 5 ta rasm yubora oladi.
2. **`ADMIN_ID` kiritilgan bo'lsa**: rasm sizga ✅ Tasdiqlash / ❌ Rad etish tugmalari bilan keladi. Tasdiqlasangiz, bot rasmni 100 km radiusdagi ogohlantirish yoqqan obunachilarga yuboradi.
3. **`ADMIN_ID` kiritilmagan bo'lsa**: rasm darhol saqlanadi, lekin hech kimga avtomatik yuborilmaydi. Uni faqat **👀 Xabarlar** tugmasi orqali ko'rish mumkin. Bu spamdan himoya qiladi.
4. **👀 Xabarlar** tugmasi so'nggi 24 soatdagi 150 km radiusdagi tasdiqlangan rasmlarni ko'rsatadi.

## Admin
`ADMIN_ID` ga o'z Telegram ID raqamingizni yozing (uni @userinfobot orqali bilib olasiz). Shunda:
- bo'ron rasmlarini tasdiqlash huquqi sizda bo'ladi;
- `/stat` buyrug'i foydalanuvchilar va xabarlar sonini ko'rsatadi.

## Muammolar bo'lsa
| Muammo | Yechim |
|---|---|
| `BOT_TOKEN topilmadi` | Token kiritilmagan. `.env` faylini yoki Railway'dagi Variables bo'limini tekshiring |
| `Unauthorized` | Token noto'g'ri. Uni @BotFather'dan qaytadan nusxalang |
| `Conflict: terminated by other getUpdates` | Bot ikki joyda ishlayapti (masalan, kompyuteringizda va Railway'da). Bittasini to'xtating |
| Bot javob bermayapti | Railway'dagi loglarni tekshiring |
