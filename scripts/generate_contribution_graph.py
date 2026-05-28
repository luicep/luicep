#!/usr/bin/env python3
"""
Generate a recruiter-friendly GitHub activity SVG for the profile README.

Output:
  assets/portfolio-build-activity.svg

Notes:
- Uses GitHub GraphQL with GITHUB_TOKEN.
- Uses America/New_York so the graph does not appear a day ahead.
- Uses a bar chart because daily contributions are counts, not performance trends.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo


USERNAME = os.getenv("GITHUB_USERNAME", "luicep")
TOKEN = os.getenv("GITHUB_TOKEN")
LOCAL_TZ = ZoneInfo("America/New_York")
OUTFILE = Path("assets/portfolio-build-activity.svg")


def get_date_range(days: int = 30) -> tuple:
    today = datetime.now(LOCAL_TZ).date()
    start = today - timedelta(days=days - 1)

    start_dt = datetime.combine(start, datetime.min.time(), LOCAL_TZ)
    end_dt = datetime.combine(today, datetime.max.time(), LOCAL_TZ)

    return start, today, start_dt.isoformat(), end_dt.isoformat()


def fetch_contributions(username: str, token: str, start_iso: str, end_iso: str) -> dict[str, int]:
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    payload = json.dumps(
        {
            "query": query,
            "variables": {
                "login": username,
                "from": start_iso,
                "to": end_iso,
            },
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-build-activity-generator",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if "errors" in data:
        raise RuntimeError(data["errors"])

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    counts: dict[str, int] = {}
    for week in weeks:
        for day in week["contributionDays"]:
            counts[day["date"]] = int(day["contributionCount"])

    return counts


def build_svg(labels: list[str], counts: list[int], title: str = "Portfolio Build Activity") -> str:
    width = 1100
    height = 360
    margin_left = 70
    margin_right = 35
    margin_top = 55
    margin_bottom = 70
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    max_count = max(counts) if counts else 0
    y_max = max(4, max_count)
    if y_max >= 10:
        y_max = ((y_max + 4) // 5) * 5

    bar_gap = 5
    bar_w = max(10, (plot_w / len(counts)) - bar_gap)

    bg = "#0D1117"
    grid = "#30363D"
    axis_text = "#F0F6FC"
    accent = "#caae7b"
    bar = "#d1c0a1"

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">',
        f'<rect width="100%" height="100%" fill="{bg}"/>',
        f'<text x="{width/2}" y="30" text-anchor="middle" fill="{accent}" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="700">{escape(title)}</text>',
    ]

    ticks = min(5, y_max)
    for i in range(ticks + 1):
        value = round(y_max * i / ticks)
        y = margin_top + plot_h - (value / y_max) * plot_h
        svg_parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width-margin_right}" y2="{y:.1f}" stroke="{grid}" stroke-dasharray="3,3" stroke-width="1"/>')
        svg_parts.append(f'<text x="{margin_left-15}" y="{y+4:.1f}" text-anchor="end" fill="{axis_text}" font-family="Segoe UI, Arial, sans-serif" font-size="12">{value}</text>')

    svg_parts.append(f'<text x="20" y="{margin_top + plot_h/2}" transform="rotate(-90 20 {margin_top + plot_h/2})" text-anchor="middle" fill="{axis_text}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="600">Contributions</text>')
    svg_parts.append(f'<text x="{margin_left + plot_w/2}" y="{height-18}" text-anchor="middle" fill="{axis_text}" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="600">Date</text>')

    for idx, count in enumerate(counts):
        x = margin_left + idx * (plot_w / len(counts)) + bar_gap / 2
        h = 0 if count == 0 else max(3, (count / y_max) * plot_h)
        y = margin_top + plot_h - h
        opacity = 0.35 if count == 0 else 1
        svg_parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="3" fill="{bar}" opacity="{opacity}">'
            f'<title>{escape(labels[idx])}: {count} contribution{"s" if count != 1 else ""}</title></rect>'
        )

    label_indexes = set(range(0, len(labels), 5))
    label_indexes.add(len(labels) - 1)
    for idx in sorted(label_indexes):
        x = margin_left + idx * (plot_w / len(counts)) + bar_w / 2
        svg_parts.append(f'<text x="{x:.1f}" y="{margin_top + plot_h + 24}" text-anchor="middle" fill="{axis_text}" font-family="Segoe UI, Arial, sans-serif" font-size="11">{escape(labels[idx])}</text>')

    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


def build_placeholder_svg(message: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="240" viewBox="0 0 1100 240" role="img" aria-label="Portfolio Build Activity">
  <rect width="100%" height="100%" rx="10" fill="#0D1117"/>
  <text x="550" y="90" text-anchor="middle" fill="#caae7b" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="700">Portfolio Build Activity</text>
  <text x="550" y="130" text-anchor="middle" fill="#F0F6FC" font-family="Segoe UI, Arial, sans-serif" font-size="14">{escape(message)}</text>
</svg>
"""


def main() -> None:
    OUTFILE.parent.mkdir(parents=True, exist_ok=True)

    if not TOKEN:
        OUTFILE.write_text(
            build_placeholder_svg("Waiting for GitHub Actions token to generate contribution data."),
            encoding="utf-8",
        )
        return

    start, today, start_iso, end_iso = get_date_range(30)
    contributions = fetch_contributions(USERNAME, TOKEN, start_iso, end_iso)

    dates = [start + timedelta(days=i) for i in range(30)]
    labels = [d.strftime("%b %d") for d in dates]
    counts = [contributions.get(d.isoformat(), 0) for d in dates]

    svg = build_svg(labels, counts)
    OUTFILE.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
