from io import BytesIO
import os
from pathlib import Path

cache_dir = Path(__file__).resolve().parent / ".cache" / "matplotlib"
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(cache_dir))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_dir.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def build_progress_text(title, records, value_key, unit):
    if not records:
        return f"<b>{title}</b>\nПока нет сохраненных записей для статистики."

    latest = records[-1][value_key]
    unit_text = f" {unit}" if unit else ""
    text = [
        f"<b>{title}</b>",
        f"Записей: <b>{len(records)}</b>",
        f"Последнее значение: <b>{latest:.2f}{unit_text}</b>",
    ]

    if len(records) >= 2:
        previous = records[-2][value_key]
        total_delta = latest - records[0][value_key]
        previous_delta = latest - previous
        text.append(f"Изменение с прошлой записи: <b>{format_delta(previous_delta)}{unit_text}</b>")
        text.append(f"Общий прогресс: <b>{format_delta(total_delta)}{unit_text}</b>")
    else:
        text.append("Для прогресса нужно минимум 2 записи.")

    return "\n".join(text)


def format_delta(value):
    if value > 0:
        return f"+{value:.2f}"
    return f"{value:.2f}"


def build_line_chart_png(title, records, label_key, value_key, unit):
    values = [float(record[value_key]) for record in records]
    labels = [str(record[label_key])[:10] for record in records]
    indexes = list(range(1, len(values) + 1))

    fig, ax = plt.subplots(figsize=(10, 6), dpi=160)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(
        indexes,
        values,
        color="#0f766e",
        linewidth=2.8,
        marker="o",
        markersize=7,
        markerfacecolor="#ffffff",
        markeredgecolor="#0f766e",
        markeredgewidth=2,
    )

    for x, y in zip(indexes, values):
        ax.annotate(
            f"{y:.2f}",
            (x, y),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
            fontsize=9,
            color="#111827",
        )

    ax.set_title(title, fontsize=16, fontweight="bold", pad=18)
    ax.set_ylabel(unit, fontsize=11)
    ax.set_xticks(indexes)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=9)
    ax.grid(True, axis="y", color="#e5e7eb", linewidth=1)
    ax.grid(False, axis="x")

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#94a3b8")
    ax.spines["bottom"].set_color("#94a3b8")

    min_value = min(values)
    max_value = max(values)
    padding = (max_value - min_value) * 0.18 or 1
    ax.set_ylim(min_value - padding, max_value + padding)

    fig.tight_layout()
    output = BytesIO()
    fig.savefig(output, format="png", bbox_inches="tight")
    plt.close(fig)
    output.seek(0)
    return output.getvalue()
