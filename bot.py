"""Chang Monitor — chang va qum bo'ronlari bo'yicha Telegram bot."""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, Message, ReplyKeyboardMarkup)

from texts import (ALERT_DUST, ALERT_PM10, CITIES, HELP, INFO, START, TIPS, WEEKDAYS,
                   bar, level)


def load_env(path=".env"):
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


load_env()

import api  # noqa: E402
import db  # noqa: E402
TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
DAILY_HOUR = int(os.getenv("DAILY_HOUR") or 7)
TZ = ZoneInfo("Asia/Tashkent")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chang_bot")
dp = Dispatcher()

# ---------------- Klaviaturalar ----------------
B_NOW, B_FC, B_CITY = "🌫 Hozirgi holat", "📈 Prognoz", "🏙 Shahar"
B_LOC, B_SUB = "📍 Lokatsiya yuborish", "🔔 Obuna"
B_TIPS, B_INFO = "💊 Maslahatlar", "📚 Ma'lumot"

MAIN_KB = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text=B_NOW), KeyboardButton(text=B_FC)],
    [KeyboardButton(text=B_CITY), KeyboardButton(text=B_LOC, request_location=True)],
    [KeyboardButton(text=B_SUB), KeyboardButton(text=B_TIPS), KeyboardButton(text=B_INFO)],
])


def cities_kb() -> InlineKeyboardMarkup:
    items = [InlineKeyboardButton(text=name, callback_data=f"city:{key}")
             for key, (name, _, _) in CITIES.items()]
    return InlineKeyboardMarkup(inline_keyboard=[items[i:i + 3] for i in range(0, len(items), 3)])


def sub_kb(user) -> InlineKeyboardMarkup:
    on = lambda v: "✅" if v else "❌"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{on(user['alerts'])} Bo'ron ogohlantirishlari",
                              callback_data="sub:alerts")],
        [InlineKeyboardButton(text=f"{on(user['daily'])} Kunlik hisobot ({DAILY_HOUR:02d}:00)",
                              callback_data="sub:daily")],
    ])


def refresh_kb(kind: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"refresh:{kind}")]])


# ---------------- Matn formatlash ----------------
def fmt(v) -> str:
    return "—" if v is None else f"{v:.0f}"


def now_text(place: str, data: dict) -> str:
    c = data["current"]
    emoji, name, advice = level(c.get("pm10"))
    nxt = api.next_hours_max(data, 24)
    text = (
        f"📍 <b>{place}</b>  •  {c['time'].replace('T', ' ')}\n\n"
        f"{emoji} <b>{name}</b>\n\n"
        f"🌫 PM10:   <b>{fmt(c.get('pm10'))}</b> µg/m³  {bar(c.get('pm10'))}\n"
        f"💨 PM2.5:  <b>{fmt(c.get('pm2_5'))}</b> µg/m³\n"
        f"🏜 Chang:  <b>{fmt(c.get('dust'))}</b> µg/m³\n"
    )
    aod = c.get("aerosol_optical_depth")
    if aod is not None:
        text += f"🌁 Aerozol (AOD): <b>{aod:.2f}</b>\n"
    text += f"\n💡 {advice}"
    if nxt["pm10"] >= ALERT_PM10 or nxt["dust"] >= ALERT_DUST:
        t = nxt["time"].split("T")[1]
        text += (f"\n\n⚠️ <b>Diqqat!</b> Keyingi 24 soatda chang kuchayishi kutilmoqda: "
                 f"soat {t} atrofida PM10 ≈ {nxt['pm10']:.0f} µg/m³")
    return text


def forecast_text(place: str, data: dict) -> str:
    lines = [f"📈 <b>{place} — 3 kunlik chang prognozi</b>\n"]
    for d in api.daily_summary(data):
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        emoji, name, _ = level(d["pm10"])
        lines.append(
            f"<b>{WEEKDAYS[dt.weekday()]}, {dt:%d.%m}</b>\n"
            f"{emoji} {name}  {bar(d['pm10'])}\n"
            f"PM10 maks: <b>{d['pm10']:.0f}</b> (soat {d['peak']})  •  "
            f"Chang: {d['dust']:.0f}  •  PM2.5: {d['pm2_5']:.0f}\n"
        )
    lines.append("<i>Qiymatlar µg/m³ da, kunning eng yuqori ko'rsatkichi.</i>")
    return "\n".join(lines)


def alert_text(place: str, nxt: dict) -> str:
    emoji, name, advice = level(nxt["pm10"])
    day, hour = nxt["time"].split("T")
    when = "bugun" if day == datetime.now(TZ).strftime("%Y-%m-%d") else "ertaga"
    return (
        f"🚨 <b>CHANG BO'RONI OGOHLANTIRISHI</b>\n\n"
        f"📍 {place}\n"
        f"🕐 {when}, soat {hour} atrofida\n"
        f"{emoji} PM10 ≈ <b>{nxt['pm10']:.0f}</b> µg/m³ ({name})\n"
        f"🏜 Chang ≈ <b>{nxt['dust']:.0f}</b> µg/m³\n\n"
        f"💡 {advice}\n\nBatafsil: /maslahat"
    )


# ---------------- Yordamchi ----------------
async def get_place(m: Message):
    u = db.get_user(m.from_user.id)
    if not u or u["lat"] is None:
        await m.answer("Avval shaharni tanlang 👇", reply_markup=cities_kb())
        return None
    return u


async def send_air(target: Message, uid: int, kind: str, edit: bool = False):
    u = db.get_user(uid)
    if not u or u["lat"] is None:
        await target.answer("Avval shaharni tanlang 👇", reply_markup=cities_kb())
        return
    try:
        data = await api.get_air(u["lat"], u["lon"])
    except Exception as e:  # noqa: BLE001
        log.warning("API xatosi: %s", e)
        await target.answer("😔 Ma'lumot olishda xatolik. Birozdan keyin qayta urinib ko'ring.")
        return
    text = now_text(u["city"], data) if kind == "now" else forecast_text(u["city"], data)
    if edit:
        try:
            await target.edit_text(text, reply_markup=refresh_kb(kind))
        except Exception:  # matn o'zgarmagan bo'lsa
            pass
    else:
        await target.answer(text, reply_markup=refresh_kb(kind))


# ---------------- Handlerlar ----------------
@dp.message(CommandStart())
async def cmd_start(m: Message):
    db.ensure_user(m.from_user.id)
    await m.answer(START.format(name=m.from_user.first_name or ""), reply_markup=MAIN_KB)
    await m.answer("🏙 Shaharni tanlang:", reply_markup=cities_kb())


@dp.message(Command("help", "yordam"))
async def cmd_help(m: Message):
    await m.answer(HELP, reply_markup=MAIN_KB)


@dp.message(Command("havo"))
@dp.message(F.text == B_NOW)
async def cmd_now(m: Message):
    await send_air(m, m.from_user.id, "now")


@dp.message(Command("prognoz"))
@dp.message(F.text == B_FC)
async def cmd_forecast(m: Message):
    await send_air(m, m.from_user.id, "fc")


@dp.message(Command("shahar"))
@dp.message(F.text == B_CITY)
async def cmd_city(m: Message):
    await m.answer("🏙 Shaharni tanlang:", reply_markup=cities_kb())


@dp.message(Command("obuna"))
@dp.message(F.text == B_SUB)
async def cmd_sub(m: Message):
    db.ensure_user(m.from_user.id)
    u = db.get_user(m.from_user.id)
    place = u["city"] or "tanlanmagan"
    await m.answer(
        f"🔔 <b>Obuna sozlamalari</b>\n📍 Joy: <b>{place}</b>\n\n"
        f"• <b>Ogohlantirish</b> — keyingi 24 soatda PM10 {ALERT_PM10} dan yoki chang "
        f"{ALERT_DUST} µg/m³ dan oshsa xabar beraman.\n"
        f"• <b>Kunlik hisobot</b> — har kuni soat {DAILY_HOUR:02d}:00 da qisqa ma'lumot.",
        reply_markup=sub_kb(u))


@dp.message(Command("maslahat"))
@dp.message(F.text == B_TIPS)
async def cmd_tips(m: Message):
    await m.answer(TIPS)


@dp.message(Command("malumot"))
@dp.message(F.text == B_INFO)
async def cmd_info(m: Message):
    await m.answer(INFO)


@dp.message(Command("stop"))
async def cmd_stop(m: Message):
    db.delete_user(m.from_user.id)
    await m.answer("🗑 Ma'lumotlaringiz o'chirildi, xabarlar yuborilmaydi. Qaytish uchun /start")


@dp.message(Command("stat"))
async def cmd_stat(m: Message):
    if ADMIN_ID and m.from_user.id == ADMIN_ID:
        s = db.stats()
        await m.answer(f"👥 Jami: {s['jami']}\n🔔 Ogohlantirish: {s['ogohlantirish']}\n"
                       f"🗓 Kunlik: {s['kunlik']}")


@dp.message(F.location)
async def on_location(m: Message):
    lat, lon = m.location.latitude, m.location.longitude
    db.set_location(m.from_user.id, f"Joylashuvim ({lat:.2f}, {lon:.2f})", lat, lon)
    await m.answer("✅ Joylashuvingiz saqlandi.", reply_markup=MAIN_KB)
    await send_air(m, m.from_user.id, "now")


@dp.callback_query(F.data.startswith("city:"))
async def on_city(c: CallbackQuery):
    key = c.data.split(":", 1)[1]
    if key not in CITIES:
        return await c.answer()
    name, lat, lon = CITIES[key]
    db.set_location(c.from_user.id, name, lat, lon)
    await c.answer(f"{name} tanlandi")
    await c.message.edit_text(f"✅ Shahar: <b>{name}</b>")
    await send_air(c.message, c.from_user.id, "now")


@dp.callback_query(F.data.startswith("sub:"))
async def on_sub(c: CallbackQuery):
    field = c.data.split(":", 1)[1]
    if field not in ("alerts", "daily"):
        return await c.answer()
    val = db.toggle(c.from_user.id, field)
    await c.answer("Yoqildi ✅" if val else "O'chirildi ❌")
    await c.message.edit_reply_markup(reply_markup=sub_kb(db.get_user(c.from_user.id)))


@dp.callback_query(F.data.startswith("refresh:"))
async def on_refresh(c: CallbackQuery):
    await c.answer("Yangilanmoqda...")
    await send_air(c.message, c.from_user.id, c.data.split(":", 1)[1], edit=True)


@dp.message()
async def fallback(m: Message):
    # Foydalanuvchi shahar nomini yozsa
    text = (m.text or "").lower().replace("'", "").replace("‘", "").replace("ʻ", "")
    for key, (name, lat, lon) in CITIES.items():
        if len(text) >= 4 and (text in key or key in text):
            db.set_location(m.from_user.id, name, lat, lon)
            await m.answer(f"✅ Shahar: <b>{name}</b>", reply_markup=MAIN_KB)
            return await send_air(m, m.from_user.id, "now")
    await m.answer("Tushunmadim 🤔 Quyidagi tugmalardan foydalaning yoki /help", reply_markup=MAIN_KB)


# ---------------- Avtomatik xabarlar ----------------
async def fetch_grouped(users):
    """Bir xil koordinatadagi foydalanuvchilar uchun API'ga bir marta murojaat qilamiz."""
    cache = {}
    for u in users:
        key = (round(u["lat"], 2), round(u["lon"], 2))
        if key not in cache:
            try:
                cache[key] = await api.get_air(u["lat"], u["lon"])
            except Exception as e:  # noqa: BLE001
                log.warning("API xatosi %s: %s", key, e)
                cache[key] = None
            await asyncio.sleep(0.3)
        yield u, cache[key]


async def safe_send(bot: Bot, uid: int, text: str):
    try:
        await bot.send_message(uid, text)
        await asyncio.sleep(0.05)  # Telegram limitlari uchun
    except TelegramForbiddenError:
        db.delete_user(uid)  # botni bloklagan
    except Exception as e:  # noqa: BLE001
        log.warning("Xabar yuborilmadi %s: %s", uid, e)


async def check_alerts(bot: Bot):
    now = datetime.now(TZ)
    async for u, data in fetch_grouped(db.users_with("alerts")):
        if not data:
            continue
        nxt = api.next_hours_max(data, 24)
        if nxt["pm10"] < ALERT_PM10 and nxt["dust"] < ALERT_DUST:
            continue
        # bir foydalanuvchiga 12 soatda ko'pi bilan 1 marta
        if u["last_alert"] and now - datetime.fromisoformat(u["last_alert"]) < timedelta(hours=12):
            continue
        await safe_send(bot, u["user_id"], alert_text(u["city"], nxt))
        db.set_last_alert(u["user_id"], now.isoformat())


async def send_daily(bot: Bot):
    async for u, data in fetch_grouped(db.users_with("daily")):
        if data:
            await safe_send(bot, u["user_id"], "☀️ <b>Xayrli tong!</b>\n\n" + now_text(u["city"], data))


async def scheduler(bot: Bot):
    """Har soat boshida ogohlantirishlarni tekshiradi, DAILY_HOUR da hisobot yuboradi."""
    while True:
        now = datetime.now(TZ)
        nxt = (now + timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
        await asyncio.sleep((nxt - now).total_seconds())
        try:
            if nxt.hour == DAILY_HOUR:
                await send_daily(bot)
            await check_alerts(bot)
        except Exception:  # noqa: BLE001
            log.exception("Scheduler xatosi")


async def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN topilmadi! .env faylini yarating (.env.example ga qarang).")
    bot = Bot(TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    asyncio.create_task(scheduler(bot))
    log.info("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
