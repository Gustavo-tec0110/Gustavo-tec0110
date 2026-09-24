#!/usr/bin/env python3
"""Render a custom SVG using GitHub's public contribution calendar."""

from __future__ import annotations

import argparse
import html
import re
import urllib.request
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path

DEFAULT_USERNAME = "Gustavo-tec0110"
DEFAULT_OUTPUT = Path("assets/profile/contributions.svg")
PALETTE = {0: "#1b2332", 1: "#245f55", 2: "#25806c", 3: "#37a77c", 4: "#65d89b"}


class ContributionParser(HTMLParser):
    """Extract date and level attributes from GitHub's calendar table."""

    def __init__(self) -> None:
        super().__init__()
        self.days: dict[date, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "td":
            return
        values = dict(attrs)
        classes = values.get("class", "") or ""
        if "ContributionCalendar-day" not in classes or "data-date" not in values:
            return
        try:
            self.days[date.fromisoformat(values["data-date"] or "")] = int(
                values.get("data-level", "0") or "0"
            )
        except ValueError:
            return


def download_calendar(username: str) -> str:
    request = urllib.request.Request(
        f"https://github.com/users/{username}/contributions",
        headers={
            "Accept": "text/html",
            "User-Agent": "gustavo-profile-contribution-graph",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def public_contributions(page: str) -> tuple[dict[date, int], str]:
    parser = ContributionParser()
    parser.feed(page)
    if not parser.days:
        raise RuntimeError("GitHub returned no contribution calendar data")

    match = re.search(r"([\d,]+)\s+contributions(?:\s+in\s+(\d{4}))?", page)
    if match:
        label = f"{match.group(1)} public contributions"
        if match.group(2):
            label += f" in {match.group(2)}"
    else:
        label = "Public contribution activity"
    return parser.days, label


def week_start(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def render(days: dict[date, int], label: str, username: str) -> str:
    today = date.today()
    visible_days = {day: level for day, level in days.items() if day <= today}
    if not visible_days:
        raise RuntimeError("GitHub returned no completed contribution days")

    first_day = min(visible_days)
    last_day = max(visible_days)
    first_week = week_start(first_day)
    weeks = ((last_day - first_week).days // 7) + 1
    grid_x, grid_y, cell, gap = 178, 128, 13, 5

    month_labels: list[str] = []
    for day in sorted(visible_days):
        if day.day != 1:
            continue
        column = (day - first_week).days // 7
        month_labels.append(
            f'<text x="{grid_x + column * (cell + gap)}" y="106" fill="#94a3b8" '
            f'font-family="Arial, Helvetica, sans-serif" font-size="14">{day.strftime("%b")}</text>'
        )

    cells: list[str] = []
    for column in range(weeks):
        for row in range(7):
            day = first_week + timedelta(days=column * 7 + row)
            if day > today:
                cells.append(
                    f'<rect x="{grid_x + column * (cell + gap)}" y="{grid_y + row * (cell + gap)}" '
                    f'width="{cell}" height="{cell}" rx="3" fill="#111827" opacity=".5"><title>{day.isoformat()} · future date</title></rect>'
                )
                continue
            level = visible_days.get(day, 0)
            x = grid_x + column * (cell + gap)
            y = grid_y + row * (cell + gap)
            color = PALETTE.get(level, PALETTE[0])
            if level:
                delay = min(0.18 + (column + row) * 0.018, 1.05)
                animation = (
                    f'<animate attributeName="opacity" values="0;1" begin="{delay:.2f}s" '
                    'dur=".42s" fill="freeze"/>'
                )
                cells.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" '
                    f'fill="{color}" opacity="0"><title>{day.isoformat()} · contribution level {level}</title>{animation}</rect>'
                )
            else:
                cells.append(
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}"><title>{day.isoformat()} · no public contributions</title></rect>'
                )

    legend_x = 112
    legend = "".join(
        f'<rect x="{legend_x + level * 20}" y="316" width="13" height="13" rx="3" fill="{PALETTE[level]}"/>'
        for level in range(5)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="370" viewBox="0 0 1200 370" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(label)}</title>
  <desc id="desc">A custom graph of public GitHub contribution levels for {html.escape(username)}.</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#090d18"/><stop offset="1" stop-color="#17112c"/></linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#38bdf8"/><stop offset="1" stop-color="#a855f7"/></linearGradient>
  </defs>
  <rect width="1200" height="370" rx="20" fill="url(#background)"/>
  <rect x="24" y="24" width="1152" height="322" rx="14" fill="none" stroke="#64748b" stroke-opacity=".34"/>
  <path d="M68 86h290" stroke="url(#accent)" stroke-width="3" stroke-linecap="round"/>
  <text x="68" y="65" fill="#f8fafc" font-family="Arial, Helvetica, sans-serif" font-size="27" font-weight="700">Contribution activity</text>
  <text x="1130" y="65" fill="#a5b4fc" font-family="ui-monospace, monospace" font-size="15" text-anchor="end">{html.escape(label)}</text>
  {''.join(month_labels)}
  <text x="112" y="141" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="13">Sun</text>
  <text x="112" y="177" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="13">Tue</text>
  <text x="112" y="213" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="13">Thu</text>
  <text x="112" y="249" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="13">Sat</text>
  {''.join(cells)}
  <text x="68" y="327" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="14">Less</text>
  {legend}
  <text x="{legend_x + 112}" y="327" fill="#94a3b8" font-family="Arial, Helvetica, sans-serif" font-size="14">More</text>
  <text x="1130" y="327" fill="#94a3b8" font-family="ui-monospace, monospace" font-size="13" text-anchor="end">source: github.com/{html.escape(username)}</text>
</svg>'''


def main() -> None:
    arguments = argparse.ArgumentParser()
    arguments.add_argument("--username", default=DEFAULT_USERNAME)
    arguments.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    options = arguments.parse_args()
    days, label = public_contributions(download_calendar(options.username))
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(render(days, label, options.username), encoding="utf-8")


if __name__ == "__main__":
    main()
