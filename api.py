"""Open-Meteo Air Quality API (bepul, kalit talab qilinmaydi)."""
import aiohttp

URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


async def get_air(lat: float, lon: float) -> dict:
    """Hozirgi holat va 3 kunlik soatlik prognozni qaytaradi."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "pm10,pm2_5,dust,aerosol_optical_depth",
        "hourly": "pm10,pm2_5,dust",
        "timezone": "Asia/Tashkent",
        "forecast_days": 3,
    }
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as s:
        async with s.get(URL, params=params) as r:
            r.raise_for_status()
            return await r.json()


def daily_summary(data: dict) -> list[dict]:
    """Soatlik prognozni kunlarga bo'lib, har kun uchun maksimumni hisoblaydi."""
    h = data["hourly"]
    days: dict[str, dict] = {}
    for i, t in enumerate(h["time"]):
        day, hour = t.split("T")
        d = days.setdefault(day, {"date": day, "pm10": 0, "pm2_5": 0, "dust": 0, "peak": hour})
        pm10 = h["pm10"][i] or 0
        if pm10 > d["pm10"]:
            d["pm10"], d["peak"] = pm10, hour
        d["pm2_5"] = max(d["pm2_5"], h["pm2_5"][i] or 0)
        d["dust"] = max(d["dust"], h["dust"][i] or 0)
    return list(days.values())


def next_hours_max(data: dict, hours: int = 24) -> dict:
    """Hozirdan keyingi N soat ichidagi eng yuqori qiymatlar."""
    h = data["hourly"]
    now = data["current"]["time"]
    start = next((i for i, t in enumerate(h["time"]) if t >= now), 0)
    sl = slice(start, start + hours)
    pm10 = [v or 0 for v in h["pm10"][sl]]
    dust = [v or 0 for v in h["dust"][sl]]
    if not pm10:
        return {"pm10": 0, "dust": 0, "time": now}
    i = max(range(len(pm10)), key=pm10.__getitem__)
    return {"pm10": max(pm10), "dust": max(dust), "time": h["time"][start + i]}
