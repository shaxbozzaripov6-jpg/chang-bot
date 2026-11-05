"""72 soatlik chang prognozi grafigini PNG rasm qilib chizadi."""
import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")  # serverda ekransiz ishlash uchun
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

from texts import LEVEL_COLORS, LEVEL_LIMITS, WEEKDAYS, t  # noqa: E402


def make_chart(data: dict, place: str, lang: str = "uz") -> bytes:
    h = data["hourly"]
    times = [datetime.fromisoformat(x) for x in h["time"]]
    pm10 = [v if v is not None else float("nan") for v in h["pm10"]]
    dust = [v if v is not None else float("nan") for v in h["dust"]]

    valid = [v for v in pm10 + dust if v == v]  # NaN'larni tashlab
    top = max(150, (max(valid) if valid else 0) * 1.15)

    fig, ax = plt.subplots(figsize=(10, 5), dpi=120)

    # Rangli fon zonalari: yaxshi → xavfli
    lo = 0
    for limit, color in zip(LEVEL_LIMITS, LEVEL_COLORS):
        hi = min(limit, top)
        if lo < top:
            ax.axhspan(lo, hi, color=color, alpha=0.13, lw=0)
        lo = limit

    ax.plot(times, pm10, color="#d84315", lw=2.4, label="PM10")
    ax.plot(times, dust, color="#6d4c41", lw=1.8, ls="--", label=t(lang, "chart_dust"))

    # "Hozir" chizig'i
    now = datetime.fromisoformat(data["current"]["time"])
    ax.axvline(now, color="#37474f", lw=1, ls=":")
    ax.text(now, top * 0.97, " " + t(lang, "chart_now"), color="#37474f", fontsize=9, va="top")

    # Eng yuqori nuqta
    if valid:
        i = max(range(len(pm10)), key=lambda k: pm10[k] if pm10[k] == pm10[k] else -1)
        ax.scatter([times[i]], [pm10[i]], color="#d84315", zorder=5)
        ax.annotate(f"{pm10[i]:.0f}", (times[i], pm10[i]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=10, fontweight="bold", color="#bf360c")

    ax.set_ylim(0, top)
    ax.set_xlim(times[0], times[-1])
    ax.set_ylabel(t(lang, "chart_y"))
    ax.set_title(t(lang, "chart_title", place=place), fontsize=13, fontweight="bold", pad=12)

    days = WEEKDAYS.get(lang, WEEKDAYS["uz"])
    ax.xaxis.set_major_locator(mdates.DayLocator())
    ax.xaxis.set_major_formatter(plt.FuncFormatter(
        lambda x, _: f"{days[mdates.num2date(x).weekday()][:3]} "
                     f"{mdates.num2date(x):%d.%m}"))
    ax.xaxis.set_minor_locator(mdates.HourLocator(byhour=[6, 12, 18]))
    ax.xaxis.set_minor_formatter(mdates.DateFormatter("%H"))
    ax.tick_params(axis="x", which="minor", labelsize=8, colors="#78909c")
    ax.tick_params(axis="x", which="major", pad=14)
    ax.grid(True, which="major", axis="x", color="#b0bec5", lw=0.8)
    ax.grid(True, which="major", axis="y", color="#eceff1", lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper left", frameon=False)
    fig.text(0.99, 0.01, "Open-Meteo / Copernicus CAMS", ha="right", fontsize=7, color="#90a4ae")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
