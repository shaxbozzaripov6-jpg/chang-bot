"""Shaharlar, darajalar, maslahatlar va matnlar."""

CITIES = {
    "toshkent":  ("Toshkent",   41.311, 69.240),
    "nukus":     ("Nukus",      42.460, 59.603),
    "moynoq":    ("Mo'ynoq",    43.768, 59.022),
    "urganch":   ("Urganch",    41.550, 60.631),
    "buxoro":    ("Buxoro",     39.768, 64.421),
    "navoiy":    ("Navoiy",     40.084, 65.379),
    "samarqand": ("Samarqand",  39.654, 66.959),
    "qarshi":    ("Qarshi",     38.861, 65.789),
    "termiz":    ("Termiz",     37.224, 67.278),
    "jizzax":    ("Jizzax",     40.116, 67.842),
    "guliston":  ("Guliston",   40.490, 68.784),
    "namangan":  ("Namangan",   40.998, 71.672),
    "andijon":   ("Andijon",    40.783, 72.344),
    "fargona":   ("Farg'ona",   40.384, 71.784),
}

# PM10 (µg/m³) bo'yicha darajalar
LEVELS = [
    (50,  "🟢", "Yaxshi",        "Havo toza. Bemalol sayr qilishingiz mumkin."),
    (100, "🟡", "O'rtacha",      "Sezgir odamlar (astma, allergiya) ehtiyot bo'lsin."),
    (250, "🟠", "Yomon",         "Uzoq vaqt tashqarida bo'lmang, sport bilan uyda shug'ullaning."),
    (430, "🔴", "Juda yomon",    "Niqob taqing (N95/FFP2), derazalarni yoping."),
    (10**9, "🟣", "Xavfli",      "Qum-chang bo'roni! Zarurat bo'lmasa tashqariga chiqmang."),
]

ALERT_PM10 = 250   # shu qiymatdan oshsa ogohlantirish yuboriladi
ALERT_DUST = 200


def level(pm10: float):
    for limit, emoji, name, advice in LEVELS:
        if (pm10 or 0) < limit:
            return emoji, name, advice
    return LEVELS[-1][1:]


def bar(value: float, maxv: float = 500, width: int = 10) -> str:
    n = min(width, round((value or 0) / maxv * width))
    return "█" * n + "░" * (width - n)


WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

START = (
    "Assalomu alaykum, {name}! 👋\n\n"
    "Men <b>Chang Monitor</b> botiman 🌪\n"
    "O'zbekiston shaharlari bo'yicha <b>chang va qum bo'ronlari</b> haqida "
    "ma'lumot, prognoz va ogohlantirishlar beraman.\n\n"
    "Boshlash uchun shahringizni tanlang yoki 📍 lokatsiya yuboring 👇"
)

HELP = (
    "<b>Buyruqlar:</b>\n"
    "/havo — hozirgi chang holati\n"
    "/prognoz — 3 kunlik prognoz\n"
    "/shahar — shaharni tanlash\n"
    "/obuna — ogohlantirish va kunlik hisobot sozlamalari\n"
    "/maslahat — sog'liq bo'yicha maslahatlar\n"
    "/malumot — chang bo'ronlari haqida\n"
    "/stop — barcha ma'lumotlarimni o'chirish\n\n"
    "Ma'lumot manbasi: Open-Meteo / Copernicus CAMS."
)

TIPS = (
    "💊 <b>Chang bo'ronida sog'likni saqlash</b>\n\n"
    "😷 <b>Niqob:</b> oddiy tibbiy niqob changdan yaxshi himoya qilmaydi — "
    "<b>N95 / FFP2</b> niqob taqing.\n"
    "🪟 <b>Uy:</b> deraza va eshiklarni yoping, ho'l latta bilan tirqishlarni bekiting. "
    "Havo tozalagich bo'lsa, yoqing.\n"
    "💧 <b>Suv:</b> ko'proq suv iching, burun va ko'zni toza suv bilan yuving.\n"
    "👓 <b>Ko'z:</b> ko'zoynak taqing, linza taqmaslikka harakat qiling.\n"
    "🏃 <b>Sport:</b> tashqarida yugurish va mashq qilishni to'xtating.\n"
    "🚗 <b>Mashina:</b> ko'rinish yomonlashadi — tezlikni kamaytiring, "
    "konditsionerni ichki aylanish rejimiga qo'ying.\n\n"
    "👶👴 <b>Xavf guruhi:</b> bolalar, keksalar, homiladorlar, astma, yurak va o'pka "
    "kasalligi borlar uyda qolishi kerak.\n"
    "🚑 Nafas qisishi, ko'krak og'rig'i yoki kuchli yo'tal bo'lsa — <b>103</b> ga qo'ng'iroq qiling."
)

INFO = (
    "📚 <b>Chang va qum bo'ronlari haqida</b>\n\n"
    "🌪 <b>Chang bo'roni</b> — kuchli shamol quruq tuproq va qumni havoga ko'tarib, "
    "yuzlab kilometrga olib ketishi. Ko'rinish 1 km dan kam bo'lishi mumkin.\n\n"
    "🏜 <b>O'zbekistonda nega ko'p?</b>\n"
    "• Orol dengizi qurishi natijasida <b>Orolqum</b> cho'li paydo bo'ldi — u tuz va "
    "chang manbai.\n"
    "• Qizilqum va Qoraqum cho'llari yaqinligi.\n"
    "• Qurg'oqchilik va yashil maydonlarning kamayishi.\n\n"
    "🔬 <b>Ko'rsatkichlar:</b>\n"
    "• <b>PM10</b> — diametri 10 mikrondan kichik zarrachalar (chang, qum).\n"
    "• <b>PM2.5</b> — 2.5 mikrondan kichik, o'pkaga chuqur kiradi, eng xavflisi.\n"
    "• <b>Dust</b> — havodagi mineral chang miqdori.\n\n"
    "📏 JSST (WHO) tavsiyasi: PM10 sutkalik o'rtacha <b>45 µg/m³</b> dan, "
    "PM2.5 esa <b>15 µg/m³</b> dan oshmasligi kerak.\n\n"
    "🌳 <b>Yechim:</b> daraxt ekish, Orol tubida saksovul o'rmonlari barpo etish "
    "chang bo'ronlarini kamaytiradi."
)
