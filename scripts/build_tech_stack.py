"""Build assets/tech-stack-{light,dark}.svg from the icons in assets/icons/.

Usage: python3 scripts/build_tech_stack.py
Icons come from devicon v2.16.0 (MIT). Edit ROWS to change the stack, then rerun.
"""

import base64
import os
from html import escape

from render_stats import FONT, THEMES

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ROWS = [
    ("Languages", [
        ("Go", "go-original-wordmark"), ("Python", "python-original"), ("Rust", "rust-original"),
        ("Java", "java-original"), ("C++", "cplusplus-original"), ("Bash", "bash-original"),
    ]),
    ("Backend & ML", [
        ("Linux", "linux-plain"), ("Docker", "docker-original"), ("Redis", "redis-original"),
        ("MySQL", "mysql-original"), ("Kafka", "apachekafka-original"), ("PyTorch", "pytorch-original"),
    ]),
]
LABEL_W, TILE, GAP, ROW_H, PAD = 120, 52, 20, 92, 24


def icon_uri(name):
    with open(os.path.join(ROOT, "assets", "icons", f"{name}.svg"), "rb") as f:
        return "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()


def render(theme):
    t = THEMES[theme]
    cols = max(len(items) for _, items in ROWS)
    width = PAD * 2 + LABEL_W + cols * TILE + (cols - 1) * GAP
    height = PAD * 2 + len(ROWS) * ROW_H - 12
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Tech stack">',
        f'  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="{t["bg"]}" stroke="{t["border"]}"/>',
    ]
    for r, (label, items) in enumerate(ROWS):
        y = PAD + r * ROW_H
        parts.append(
            f'  <text x="{PAD}" y="{y + TILE / 2 + 5}" font-family="{FONT}" font-size="13" font-weight="600" fill="{t["muted"]}">{escape(label)}</text>'
        )
        for c, (name, icon) in enumerate(items):
            x = PAD + LABEL_W + c * (TILE + GAP)
            parts.append(
                f'  <rect x="{x}" y="{y}" width="{TILE}" height="{TILE}" rx="12" fill="{t["tile"]}"/>\n'
                f'  <image x="{x + 10}" y="{y + 10}" width="{TILE - 20}" height="{TILE - 20}" href="{icon_uri(icon)}"/>\n'
                f'  <text x="{x + TILE / 2}" y="{y + TILE + 18}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="{t["text"]}">{escape(name)}</text>'
            )
    parts.append("</svg>\n")
    return "\n".join(parts)


def main():
    for theme in THEMES:
        with open(os.path.join(ROOT, "assets", f"tech-stack-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(theme))


if __name__ == "__main__":
    main()
