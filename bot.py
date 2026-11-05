"""Chang Monitor: chang va qum bo'ronlari bo'yicha Telegram bot (o'zbek / rus)."""
import asyncio
import html
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.types import (BufferedInputFile, CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardMarkup)


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
from chart import make_chart  # noqa: E402
from texts import (ALERT_DUST, ALERT_PM10, BUTTONS, CITIES, LANGS, WEEKDAYS,  # noqa: E402
                   WIND_GUST_WARN, bar, city_name, level, t, weather_desc, wind_dir,
                   wind_level)

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID") or 0)
DAILY_HOUR = int(os.getenv("DAILY_HOUR") or 7)
TZ = ZoneInfo("Asia/Tashkent")

REPORT_LIMIT = 5        # bir kishi 24 soatda nechta rasm yubora oladi
REPORT_RADIUS = 100     # tasdiqlangan rasm necha km radiusdagilarga yuboriladi
FEED_RADIUS = 150       # "Xabarlar" tugmasi necha km radiusda qidiradi

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("chang_bot")
dp = Dispatcher()


def btn(key: str):
    """Tugma matni ikkala tilda ham ishlashi uchun filtr."""
    return F.text.in_(BUTTONS[key])


def lang_of(uid: int) -> str:
    return db.get_lang(uid)


def place_of(row, lang: str) -> str:
    """Foydalanuvchi yoki xabar joyining nomi tanlangan tilda."""
    city = row["city"]
    if city in CITIES:
        return city_name(city, lang)
    if row["lat"] is not None and (city == "loc" or not city):
        return f"{t(lang, 'my_location')} ({row['lat']:.2f}, {row['lon']:.2f})"
    return city or t(lang, "not_set")


# ---------------- Klaviaturalar ----------------
def main_kb(lang: str) -> ReplyKeyboardMarkup:
    b = lambda k, **kw: KeyboardButton(text=t(lang, k), **kw)  # noqa: E731
    return ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [b("btn_now"), b("btn_fc")],
        [b("btn_chart"), b("btn_city")],
        [b("btn_report"), b("btn_feed")],
        [b("btn_loc", request_location=True), b("btn_sub")],
        [b("btn_tips"), b("btn_info"), b("btn_lang")],
    ])


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
    ]])


def cities_kb(lang: str) -> InlineKeyboardMarkup:
    items = [InlineKeyboardButton(text=city_name(key, lang), callback_data=f"city:{key}")
             for key in CITIES]
    return InlineKeyboardMarkup(inline_keyboard=[items[i:i + 3] for i in range(0, len(items), 3)])


def sub_kb(user, lang: str) -> InlineKeyboardMarkup:
    on = lambda v: "✅" if v else "❌"  # noqa: E731
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{on(user['alerts'])} {t(lang, 'sub_alerts')}",
                              callback_data="sub:alerts")],
        [InlineKeyboardButton(text=f"{on(user['daily'])} {t(lang, 'sub_daily', hour=DAILY_HOUR)}",
                              callback_data="sub:daily")],
    ])


def refresh_kb(kind: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_refresh"), callback_data=f"refresh:{kind}")]])


def moderation_kb(rid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"rep:ok:{rid}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rep:no:{rid}"),
    ]])


# ---------------- Matn formatlash ----------------
def fmt(v) -> str:
    return "—" if v is None else f"{v:.0f}"


def weather_block(weather: dict | None, lang: str) -> str:
    """Hozirgi ob-havo: harorat, yog'in, shamol."""
    if not weather or "current" not in weather:
        return ""
    w = weather["current"]
    wemoji, wdesc = weather_desc(w.get("weather_code"), lang)
    arrow, wdir = wind_dir(w.get("wind_direction_10m"), lang)
    ms = t(lang, "ms")
    return (
        f"\n{wemoji} <b>{t(lang, 'weather')}:</b> {wdesc}\n"
        f"🌡 {t(lang, 'temp')}: <b>{fmt(w.get('temperature_2m'))}°C</b> "
        f"({t(lang, 'feels')} {fmt(w.get('apparent_temperature'))}°C)\n"
        f"💧 {t(lang, 'humidity')}: {fmt(w.get('relative_humidity_2m'))}%  •  "
        f"☔ {t(lang, 'precip')}: {w.get('precipitation') or 0:.1f} {t(lang, 'mm')}\n"
        f"💨 {t(lang, 'wind')}: <b>{w.get('wind_speed_10m') or 0:.1f} {ms}</b> "
        f"({wind_level(w.get('wind_speed_10m'), lang)}), {t(lang, 'gusts')} "
        f"{w.get('wind_gusts_10m') or 0:.0f} {ms}\n"
        f"🧭 {arrow} {wdir} ({fmt(w.get('wind_direction_10m'))}°)\n"
    )


def now_text(place: str, data: dict, lang: str, weather: dict | None = None) -> str:
    c = data["current"]
    emoji, name, advice = level(c.get("pm10"), lang)
    nxt = api.next_hours_max(data, 24)
    text = (
        f"📍 <b>{place}</b>  •  {c['time'].replace('T', ' ')}\n\n"
        f"{emoji} <b>{name}</b>\n\n"
        f"🌫 PM10:   <b>{fmt(c.get('pm10'))}</b> µg/m³  {bar(c.get('pm10'))}\n"
        f"💨 PM2.5:  <b>{fmt(c.get('pm2_5'))}</b> µg/m³\n"
        f"🏜 {t(lang, 'dust')}:  <b>{fmt(c.get('dust'))}</b> µg/m³\n"
    )
    aod = c.get("aerosol_optical_depth")
    if aod is not None:
        text += f"🌁 {t(lang, 'aod')}: <b>{aod:.2f}</b>\n"
    text += weather_block(weather, lang)
    text += f"\n💡 {advice}"
    if nxt["pm10"] >= ALERT_PM10 or nxt["dust"] >= ALERT_DUST:
        text += "\n\n" + t(lang, "warn24", time=nxt["time"].split("T")[1], pm10=f"{nxt['pm10']:.0f}")
    gust = api.max_gust_24h(weather)
    if gust and gust["gust"] >= WIND_GUST_WARN:
        day, hour = gust["time"].split("T")
        when = t(lang, "today") if day == datetime.now(TZ).strftime("%Y-%m-%d") else t(lang, "tomorrow")
        text += "\n\n" + t(lang, "wind_warn", gust=f"{gust['gust']:.0f}", when=when, hour=hour)
    return text


def forecast_text(place: str, data: dict, lang: str, weather: dict | None = None) -> str:
    lines = [t(lang, "fc_title", place=place)]
    days = WEEKDAYS.get(lang, WEEKDAYS["uz"])
    for d in api.daily_summary(data):
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        emoji, name, _ = level(d["pm10"], lang)
        day_text = (
            f"<b>{days[dt.weekday()]}, {dt:%d.%m}</b>\n"
            f"{emoji} {name}  {bar(d['pm10'])}\n"
            + t(lang, "fc_line", pm10=f"{d['pm10']:.0f}", peak=d["peak"],
                dust=f"{d['dust']:.0f}", pm25=f"{d['pm2_5']:.0f}")
        )
        w = api.weather_day(weather, d["date"])
        if w:
            wemoji, wdesc = weather_desc(w.get("weather_code"), lang)
            arrow, wdir = wind_dir(w.get("wind_direction_10m_dominant"), lang)
            day_text += t(lang, "fc_weather",
                          tmin=fmt(w.get("temperature_2m_min")), tmax=fmt(w.get("temperature_2m_max")),
                          wemoji=wemoji, wdesc=wdesc,
                          psum=f"{w.get('precipitation_sum') or 0:.1f}",
                          pprob=fmt(w.get("precipitation_probability_max")),
                          wmax=fmt(w.get("wind_speed_10m_max")), gmax=fmt(w.get("wind_gusts_10m_max")),
                          arrow=arrow, wdir=wdir)
        lines.append(day_text)
    if weather is None:
        lines.append(t(lang, "no_weather"))
    lines.append(t(lang, "fc_note"))
    return "\n".join(lines)


def alert_text(place: str, nxt: dict, lang: str) -> str:
    emoji, name, advice = level(nxt["pm10"], lang)
    day, hour = nxt["time"].split("T")
    when = t(lang, "today") if day == datetime.now(TZ).strftime("%Y-%m-%d") else t(lang, "tomorrow")
    return t(lang, "alert", place=place, when=when, hour=hour, emoji=emoji,
             pm10=f"{nxt['pm10']:.0f}", level=name, dust=f"{nxt['dust']:.0f}", advice=advice)


def report_caption(lang: str, header_key: str, r, km: float) -> str:
    time = r["created"][11:16]
    text = t(lang, header_key, km=f"{km:.0f}", place=place_of(r, lang), time=time)
    if r["caption"]:
        text += f"\n💬 {html.escape(r['caption'], quote=False)}"
    return text


# ---------------- Yordamchi ----------------
async def fetch_all(lat: float, lon: float):
    """Chang va ob-havo ma'lumotini bir vaqtda oladi. Ob-havo xatosi botni to'xtatmaydi."""
    air, weather = await asyncio.gather(api.get_air(lat, lon), api.get_weather(lat, lon),
                                        return_exceptions=True)
    if isinstance(air, Exception):
        log.warning("Chang API xatosi: %s", air)
        air = None
    if isinstance(weather, Exception):
        log.warning("Ob-havo API xatosi: %s", weather)
        weather = None
    return air, weather


async def located_user(m: Message, uid: int):
    """Joyi tanlangan foydalanuvchini qaytaradi, aks holda shahar tanlashni so'raydi."""
    u = db.get_user(uid)
    if not u or u["lat"] is None:
        lang = lang_of(uid)
        await m.answer(t(lang, "need_city"), reply_markup=cities_kb(lang))
        return None
    return u


async def send_air(target: Message, uid: int, kind: str, edit: bool = False):
    u = await located_user(target, uid)
    if not u:
        return
    lang = u["lang"] or "uz"
    data, weather = await fetch_all(u["lat"], u["lon"])
    if not data:
        await target.answer(t(lang, "api_error"))
        return
    place = place_of(u, lang)
    if kind == "now":
        text = now_text(place, data, lang, weather)
    else:
        text = forecast_text(place, data, lang, weather)
    if edit:
        try:
            await target.edit_text(text, reply_markup=refresh_kb(kind, lang))
        except Exception:  # matn o'zgarmagan bo'lsa
            pass
    else:
        await target.answer(text, reply_markup=refresh_kb(kind, lang))


# ---------------- Asosiy handlerlar ----------------
@dp.message(CommandStart())
async def cmd_start(m: Message):
    guess = "ru" if (m.from_user.language_code or "").startswith("ru") else "uz"
    db.ensure_user(m.from_user.id, guess)
    await m.answer(t("uz", "choose_lang"), reply_markup=lang_kb())


@dp.message(Command("til", "lang", "language"))
@dp.message(btn("btn_lang"))
async def cmd_lang(m: Message):
    await m.answer(t("uz", "choose_lang"), reply_markup=lang_kb())


@dp.callback_query(F.data.startswith("lang:"))
async def on_lang(c: CallbackQuery):
    lang = c.data.split(":", 1)[1]
    if lang not in LANGS:
        return await c.answer()
    db.set_lang(c.from_user.id, lang)
    await c.answer()
    await c.message.edit_text(t(lang, "lang_set"))
    u = db.get_user(c.from_user.id)
    if u["lat"] is None:  # yangi foydalanuvchi: salomlashish va shahar tanlash
        await c.message.answer(t(lang, "start", name=html.escape(c.from_user.first_name or "")),
                               reply_markup=main_kb(lang))
        await c.message.answer(t(lang, "choose_city"), reply_markup=cities_kb(lang))
    else:
        await c.message.answer("👇", reply_markup=main_kb(lang))


@dp.message(Command("help", "yordam"))
async def cmd_help(m: Message):
    lang = lang_of(m.from_user.id)
    await m.answer(t(lang, "help"), reply_markup=main_kb(lang))


@dp.message(Command("havo"))
@dp.message(btn("btn_now"))
async def cmd_now(m: Message):
    await send_air(m, m.from_user.id, "now")


@dp.message(Command("prognoz"))
@dp.message(btn("btn_fc"))
async def cmd_forecast(m: Message):
    await send_air(m, m.from_user.id, "fc")


@dp.message(Command("grafik"))
@dp.message(btn("btn_chart"))
async def cmd_chart(m: Message, bot: Bot):
    u = await located_user(m, m.from_user.id)
    if not u:
        return
    lang = u["lang"] or "uz"
    await bot.send_chat_action(m.chat.id, ChatAction.UPLOAD_PHOTO)
    try:
        data = await api.get_air(u["lat"], u["lon"])
        place = place_of(u, lang)
        png = await asyncio.to_thread(make_chart, data, place, lang)
    except Exception as e:  # noqa: BLE001
        log.warning("Grafik xatosi: %s", e)
        return await m.answer(t(lang, "api_error"))
    await m.answer_photo(BufferedInputFile(png, "chang.png"),
                         caption=t(lang, "chart_caption", place=place))


@dp.message(Command("shahar"))
@dp.message(btn("btn_city"))
async def cmd_city(m: Message):
    lang = lang_of(m.from_user.id)
    await m.answer(t(lang, "choose_city"), reply_markup=cities_kb(lang))


@dp.message(Command("obuna"))
@dp.message(btn("btn_sub"))
async def cmd_sub(m: Message):
    db.ensure_user(m.from_user.id)
    u = db.get_user(m.from_user.id)
    lang = u["lang"] or "uz"
    place = place_of(u, lang) if u["lat"] is not None else t(lang, "not_set")
    await m.answer(t(lang, "sub_text", place=place, pm10=ALERT_PM10, dust=ALERT_DUST, hour=DAILY_HOUR),
                   reply_markup=sub_kb(u, lang))


@dp.message(Command("maslahat"))
@dp.message(btn("btn_tips"))
async def cmd_tips(m: Message):
    await m.answer(t(lang_of(m.from_user.id), "tips"))


@dp.message(Command("malumot"))
@dp.message(btn("btn_info"))
async def cmd_info(m: Message):
    await m.answer(t(lang_of(m.from_user.id), "info"))


@dp.message(Command("stop"))
async def cmd_stop(m: Message):
    lang = lang_of(m.from_user.id)
    db.delete_user(m.from_user.id)
    await m.answer(t(lang, "stop_done"))


@dp.message(Command("stat"))
async def cmd_stat(m: Message):
    if ADMIN_ID and m.from_user.id == ADMIN_ID:
        s = db.stats()
        await m.answer(
            f"👥 Jami foydalanuvchilar: {s['jami']} (rus tilida: {s['ru']})\n"
            f"🔔 Ogohlantirish: {s['ogohlantirish']}\n🗓 Kunlik: {s['kunlik']}\n"
            f"📸 Bo'ron xabarlari: {s['xabarlar']} (tekshiruvda: {s['kutilmoqda']})")


@dp.message(F.location)
async def on_location(m: Message):
    lat, lon = m.location.latitude, m.location.longitude
    db.set_location(m.from_user.id, "loc", lat, lon)
    lang = lang_of(m.from_user.id)
    await m.answer(t(lang, "loc_saved"), reply_markup=main_kb(lang))
    await send_air(m, m.from_user.id, "now")


@dp.callback_query(F.data.startswith("city:"))
async def on_city(c: CallbackQuery):
    key = c.data.split(":", 1)[1]
    if key not in CITIES:
        return await c.answer()
    _, _, lat, lon = CITIES[key]
    db.set_location(c.from_user.id, key, lat, lon)
    lang = lang_of(c.from_user.id)
    name = city_name(key, lang)
    await c.answer(t(lang, "city_selected", name=name))
    await c.message.edit_text(t(lang, "city_set", name=name))
    await send_air(c.message, c.from_user.id, "now")


@dp.callback_query(F.data.startswith("sub:"))
async def on_sub(c: CallbackQuery):
    field = c.data.split(":", 1)[1]
    if field not in ("alerts", "daily"):
        return await c.answer()
    val = db.toggle(c.from_user.id, field)
    lang = lang_of(c.from_user.id)
    await c.answer(t(lang, "enabled") if val else t(lang, "disabled"))
    await c.message.edit_reply_markup(reply_markup=sub_kb(db.get_user(c.from_user.id), lang))


@dp.callback_query(F.data.startswith("refresh:"))
async def on_refresh(c: CallbackQuery):
    await c.answer(t(lang_of(c.from_user.id), "updating"))
    await send_air(c.message, c.from_user.id, c.data.split(":", 1)[1], edit=True)


# ---------------- Bo'ron xabarlari (foydalanuvchi rasmlari) ----------------
@dp.message(Command("xabar"))
@dp.message(btn("btn_report"))
async def cmd_report(m: Message):
    u = await located_user(m, m.from_user.id)
    if u:
        lang = u["lang"] or "uz"
        await m.answer(t(lang, "report_prompt", place=place_of(u, lang)))


@dp.message(F.photo)
async def on_photo(m: Message, bot: Bot):
    u = await located_user(m, m.from_user.id)
    if not u:
        return
    lang = u["lang"] or "uz"
    if db.reports_today(u["user_id"]) >= REPORT_LIMIT:
        return await m.answer(t(lang, "report_limit", n=REPORT_LIMIT))

    status = "pending" if ADMIN_ID else "approved"
    caption = (m.caption or "").strip()[:300]
    rid = db.add_report(u["user_id"], u["city"], u["lat"], u["lon"],
                        m.photo[-1].file_id, caption, status)

    if status == "approved":
        return await m.answer(t(lang, "report_saved"))

    await m.answer(t(lang, "report_pending"))
    who = html.escape(m.from_user.full_name or "")
    if m.from_user.username:
        who += f" (@{m.from_user.username})"
    admin_caption = (f"🆕 <b>Bo'ron xabari #{rid}</b>\n👤 {who}\n"
                     f"📍 {place_of(u, 'uz')}")
    if caption:
        admin_caption += f"\n💬 {html.escape(caption, quote=False)}"
    try:
        await bot.send_photo(ADMIN_ID, m.photo[-1].file_id, caption=admin_caption,
                             reply_markup=moderation_kb(rid))
    except Exception as e:  # noqa: BLE001
        log.warning("Adminga yuborilmadi: %s", e)


@dp.callback_query(F.data.startswith("rep:"))
async def on_moderate(c: CallbackQuery, bot: Bot):
    if c.from_user.id != ADMIN_ID:
        return await c.answer("⛔")
    _, action, rid = c.data.split(":")
    r = db.get_report(int(rid))
    if not r or r["status"] != "pending":
        await c.answer("Allaqachon ko'rib chiqilgan")
        return await c.message.edit_reply_markup(reply_markup=None)

    approved = action == "ok"
    db.set_report_status(r["id"], "approved" if approved else "rejected")
    await c.answer("Tasdiqlandi ✅" if approved else "Rad etildi ❌")
    mark = "\n\n✅ <b>Tasdiqlandi</b>" if approved else "\n\n❌ <b>Rad etildi</b>"
    await c.message.edit_caption(caption=(c.message.html_text or "") + mark, reply_markup=None)

    author_lang = lang_of(r["user_id"])
    await safe_send(bot, r["user_id"], t(author_lang, "report_approved" if approved else "report_rejected"))

    if approved:  # yaqin atrofdagi obunachilarga rasmni yuborish
        sent = 0
        for km, u in db.users_near(r["lat"], r["lon"], REPORT_RADIUS, exclude=r["user_id"]):
            lang = u["lang"] or "uz"
            try:
                await bot.send_photo(u["user_id"], r["file_id"],
                                     caption=report_caption(lang, "report_nearby", r, km))
                sent += 1
                await asyncio.sleep(0.05)
            except TelegramForbiddenError:
                db.delete_user(u["user_id"])
            except Exception as e:  # noqa: BLE001
                log.warning("Rasm yuborilmadi %s: %s", u["user_id"], e)
        await c.message.answer(f"📤 #{r['id']} xabar {sent} ta foydalanuvchiga yuborildi.")


@dp.message(Command("xabarlar"))
@dp.message(btn("btn_feed"))
async def cmd_feed(m: Message):
    u = await located_user(m, m.from_user.id)
    if not u:
        return
    lang = u["lang"] or "uz"
    found = db.nearby_reports(u["lat"], u["lon"], FEED_RADIUS)
    if not found:
        return await m.answer(t(lang, "feed_empty"))
    await m.answer(t(lang, "feed_title", km=FEED_RADIUS))
    for km, r in found:
        await m.answer_photo(r["file_id"], caption=report_caption(lang, "feed_item", r, km))


# ---------------- Boshqa xabarlar ----------------
@dp.message()
async def fallback(m: Message):
    lang = lang_of(m.from_user.id)
    text = (m.text or "").lower().replace("'", "").replace("‘", "").replace("ʻ", "").strip()
    if len(text) >= 4:  # foydalanuvchi shahar nomini yozgan bo'lsa
        for key, (uz, ru, lat, lon) in CITIES.items():
            names = (key, uz.lower().replace("'", ""), ru.lower())
            if any(text in n or n in text for n in names):
                db.set_location(m.from_user.id, key, lat, lon)
                await m.answer(t(lang, "city_set", name=city_name(key, lang)),
                               reply_markup=main_kb(lang))
                return await send_air(m, m.from_user.id, "now")
    await m.answer(t(lang, "unknown"), reply_markup=main_kb(lang))


# ---------------- Avtomatik xabarlar ----------------
async def fetch_grouped(users, with_weather: bool = False):
    """Bir xil koordinatadagi foydalanuvchilar uchun API'ga bir marta murojaat qilamiz."""
    cache = {}
    for u in users:
        key = (round(u["lat"], 2), round(u["lon"], 2))
        if key not in cache:
            if with_weather:
                cache[key] = await fetch_all(u["lat"], u["lon"])
            else:
                try:
                    cache[key] = (await api.get_air(u["lat"], u["lon"]), None)
                except Exception as e:  # noqa: BLE001
                    log.warning("API xatosi %s: %s", key, e)
                    cache[key] = (None, None)
            await asyncio.sleep(0.3)
        data, weather = cache[key]
        yield u, data, weather


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
    async for u, data, _ in fetch_grouped(db.users_with("alerts")):
        if not data:
            continue
        nxt = api.next_hours_max(data, 24)
        if nxt["pm10"] < ALERT_PM10 and nxt["dust"] < ALERT_DUST:
            continue
        # bir foydalanuvchiga 12 soatda ko'pi bilan 1 marta
        if u["last_alert"] and now - datetime.fromisoformat(u["last_alert"]) < timedelta(hours=12):
            continue
        lang = u["lang"] or "uz"
        await safe_send(bot, u["user_id"], alert_text(place_of(u, lang), nxt, lang))
        db.set_last_alert(u["user_id"], now.isoformat())


async def send_daily(bot: Bot):
    async for u, data, weather in fetch_grouped(db.users_with("daily"), with_weather=True):
        if data:
            lang = u["lang"] or "uz"
            await safe_send(bot, u["user_id"],
                            t(lang, "morning") + now_text(place_of(u, lang), data, lang, weather))


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
