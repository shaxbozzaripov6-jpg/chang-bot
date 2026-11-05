"""72 soatlik chang (va shamol) prognozi grafigini PNG rasm qilib chizadi."""
import io
import math
import warnings
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # serverda ekransiz ishlash uchun
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from texts import LEVEL_COLORS, LEVEL_LIMITS, WEEKDAYS, WIND_GUST_WARN, t  # noqa: E402


def _nan(values):
    return [v if v is not None else float("nan") for v in values]


def _format_time_axis(ax, lang: str, show_labels: bool):
    days = WEEKDAYS.get(lang, WEEKDAYS["uz"])
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
    ax.grid(True, which="major", axis="x", color="#b0bec5", lw=0.8)
    ax.grid(True, which="major", axis="y", color="#eceff1", lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if show_labels:
        ax.xaxis.set_major_formatter(plt.FuncFormatter(
            lambda x, _: f"{days[mdates.num2date(x).weekday()][:3]} {mdates.num2date(x):%d.%m}"))
        ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H"))
        ax.tick_params(axis="x", which="minor", labelsize=8, colors="#78909c")
        ax.tick_params(axis="x", which="major", pad=14)
    else:
        ax.tick_params(axis="x", which="both", labelbottom=False)


def _draw_dust(ax, data: dict, place: str, lang: str, title_key: str = "chart_title"):
    h = data["hourly"]
    times = [datetime.fromisoformat(x) for x in h["time"]]
    pm10, dust = _nan(h["pm10"]), _nan(h["dust"])

    valid = [v for v in pm10 + dust if v == v]  # NaN'larni tashlab
    top = max(150, (max(valid) if valid else 0) * 1.15)

    # Rangli fon zonalari: yaxshi → xavfli
    lo = 0
    for limit, color in zip(LEVEL_LIMITS, LEVEL_COLORS):
        if lo < top:
            ax.axhspan(lo, min(limit, top), color=color, alpha=0.13, lw=0)
        lo = limit

    ax.plot(times, pm10, color="#d84315", lw=2.4, label="PM10")
    ax.plot(times, dust, color="#6d4c41", lw=1.8, ls="--", label=t(lang, "chart_dust"))

    # Eng yuqori nuqta
    if valid:
        i = max(range(len(pm10)), key=lambda k: pm10[k] if pm10[k] == pm10[k] else -1)
        ax.scatter([times[i]], [pm10[i]], color="#d84315", zorder=5)
        ax.annotate(f"{pm10[i]:.0f}", (times[i], pm10[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=10, fontweight="bold", color="#bf360c")

    ax.set_ylim(0, top)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel(t(lang, "chart_y"))
    ax.set_title(t(lang, title_key, place=place), fontsize=13, fontweight="bold", pad=12)
    ax.legend(loc="upper left", frameon=False)
    return top


def _draw_wind(ax, weather: dict, lang: str):
    h = weather["hourly"]
    times = [datetime.fromisoformat(x) for x in h["time"]]
    speed, gusts = _nan(h["wind_speed_10m"]), _nan(h["wind_gusts_10m"])
    dirs = h.get("wind_direction_10m") or [None] * len(times)

    valid = [v for v in speed + gusts if v == v]
    top = max(WIND_GUST_WARN + 3, (max(valid) if valid else 0) * 1.35)

    # Kuchli shamol zonasi
    ax.axhspan(WIND_GUST_WARN, top, color="#e53935", alpha=0.07, lw=0)
    ax.axhline(WIND_GUST_WARN, color="#e53935", lw=1, ls=":")
    ax.text(times[-1], WIND_GUST_WARN, f"{t(lang, 'chart_strong')} ≥ {WIND_GUST_WARN} ",
            color="#c62828", fontsize=8, ha="right", va="bottom")

    ax.fill_between(times, speed, color="#1e88e5", alpha=0.18, lw=0)
    ax.plot(times, speed, color="#1565c0", lw=2, label=t(lang, "chart_wind"))
    ax.plot(times, gusts, color="#64b5f6", lw=1.4, ls="--", label=t(lang, "chart_gusts"))

    # Yo'nalish strelkalari (har 3 soatda). Shamol "qayerdan" esishi beriladi,
    # strelka esa u "qayoqqa" esayotganini ko'rsatadi.
    xs, us, vs = [], [], []
    for i in range(0, len(times), 3):
        if dirs[i] is None:
            continue
        rad = math.radians(dirs[i])
        xs.append(mdates.date2num(times[i]))
        us.append(-math.sin(rad))
        vs.append(-math.cos(rad))
    if xs:
        ax.quiver(xs, [top * 0.86] * len(xs), us, vs, color="#37474f", width=0.0025,
                  scale=38, headwidth=4, headlength=4, pivot="middle", zorder=5)

    ax.set_ylim(0, top)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel(t(lang, "chart_wind_y"))
    ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=2, bbox_to_anchor=(0, 0.78))


def make_chart(data: dict, place: str, lang: str = "uz", weather: dict | None = None) -> bytes:
    has_wind = bool(weather and weather.get("hourly", {}).get("wind_speed_10m"))
    if has_wind:
        fig, (ax, axw) = plt.subplots(2, 1, figsize=(10, 7.2), dpi=120, sharex=True,
                                      gridspec_kw={"height_ratios": [2.6, 1.4], "hspace": 0.08})
    else:
        fig, ax = plt.subplots(figsize=(10, 5), dpi=120)
        axw = None

    top = _draw_dust(ax, data, place, lang, "chart_title_wind" if has_wind else "chart_title")
    if axw is not None:
        _draw_wind(axw, weather, lang)

    # "Hozir" chizig'i
    now = datetime.fromisoformat(data["current"]["time"])
    for a in (ax, axw):
        if a is not None:
            a.axvline(now, color="#37474f", lw=1, ls=":")
    ax.text(now, top * 0.97, " " + t(lang, "chart_now"), color="#37474f", fontsize=9, va="top")

    _format_time_axis(ax, lang, show_labels=axw is None)
    if axw is not None:
        _format_time_axis(axw, lang, show_labels=True)

    fig.text(0.99, 0.005, "Open-Meteo / Copernicus CAMS", ha="right", fontsize=7, color="#90a4ae")
    with warnings.catch_warnings():  # strelkalar tight_layout ogohlantirishini chiqaradi
        warnings.simplefilter("ignore")
        fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
