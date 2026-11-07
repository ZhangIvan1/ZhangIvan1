"""Render the GitHub stats cards shown on the profile README.

Usage: GITHUB_TOKEN=... python3 scripts/render_stats.py <login> <output-dir>
Writes stats-overview-{light,dark}.svg and stats-languages-{light,dark}.svg.
"""

import datetime as dt
import json
import os
import sys
import urllib.request
from html import escape

THEMES = {
    "light": {
        "bg": "#ffffff", "border": "#d0d7de", "text": "#1f2328",
        "muted": "#59636e", "accent": "#0969da", "track": "#eff2f5", "tile": "#f6f8fa",
    },
    "dark": {
        "bg": "#0d1117", "border": "#30363d", "text": "#e6edf3",
        "muted": "#9198a1", "accent": "#4493f8", "track": "#21262d", "tile": "#e6edf3",
    },
}
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
CARD_W, CARD_H = 420, 190
# Markup and notebook languages inflate byte counts without saying much about the code itself.
EXCLUDED_LANGUAGES = {"HTML", "CSS", "TeX", "Jupyter Notebook", "Makefile", "Dockerfile", "CMake"}
# Course labs and study notes are excluded from language stats.
EXCLUDED_REPOS = {"CS144Learn", "Raft_KV", "Algorithm_learning", "GolangLearning", "2021ZhuanYeKe_review"}
TOP_LANGUAGES = 6

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

COMMITS_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) { totalCommitContributions }
  }
}
"""


def graphql(token, query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise RuntimeError(f"GraphQL error: {body['errors']}")
    return body["data"]


def fetch(token, login):
    user = graphql(token, PROFILE_QUERY, {"login": login})["user"]
    repos = user["repositories"]["nodes"]

    # contributionsCollection spans at most one year, so sum commits year by year.
    commits = 0
    start = dt.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    while start < now:
        end = min(start + dt.timedelta(days=365), now)
        data = graphql(token, COMMITS_QUERY, {
            "login": login,
            "from": start.isoformat(),
            "to": end.isoformat(),
        })
        commits += data["user"]["contributionsCollection"]["totalCommitContributions"]
        start = end

    sizes, colors = {}, {}
    for repo in repos:
        if repo["name"] in EXCLUDED_REPOS:
            continue
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in EXCLUDED_LANGUAGES:
                continue
            sizes[name] = sizes.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"] or "#8b949e"

    return {
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": commits,
        "pull_requests": user["pullRequests"]["totalCount"],
        "issues": user["issues"]["totalCount"],
        "contributed_to": user["repositoriesContributedTo"]["totalCount"],
        "contributions_last_year": user["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "languages": [{"name": n, "size": s, "color": colors[n]} for n, s in sizes.items()],
    }


def card(theme, title, body):
    t = THEMES[theme]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{CARD_H}" viewBox="0 0 {CARD_W} {CARD_H}" role="img" aria-label="{escape(title)}">
  <rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="10" fill="{t['bg']}" stroke="{t['border']}"/>
  <text x="24" y="38" font-family="{FONT}" font-size="15" font-weight="600" fill="{t['text']}">{escape(title)}</text>
{body}
</svg>
"""


def render_overview(data, theme):
    t = THEMES[theme]
    items = [
        ("Commits", data["commits"]),
        ("Stars earned", data["stars"]),
        ("Pull requests", data["pull_requests"]),
        ("Issues", data["issues"]),
        ("Contributed to", data["contributed_to"]),
        ("Contributions (1y)", data["contributions_last_year"]),
    ]
    cells = []
    for i, (label, value) in enumerate(items):
        x = 24 + (i % 2) * 196
        y = 76 + (i // 2) * 40
        cells.append(
            f'  <text x="{x}" y="{y}" font-family="{FONT}" font-size="12" fill="{t["muted"]}">{escape(label)}</text>\n'
            f'  <text x="{x + 172}" y="{y}" text-anchor="end" font-family="{FONT}" font-size="15" font-weight="600" fill="{t["text"]}">{value:,}</text>'
        )
    return card(theme, "Overview", "\n".join(cells))


def render_languages(data, theme):
    t = THEMES[theme]
    langs = sorted(data["languages"], key=lambda lang: lang["size"], reverse=True)[:TOP_LANGUAGES]
    total = sum(lang["size"] for lang in langs)
    bar_x, bar_y, bar_w = 24, 56, CARD_W - 48
    parts = [
        f'  <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4"/></clipPath>',
        f'  <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4" fill="{t["track"]}"/>',
        '  <g clip-path="url(#bar)">',
    ]
    x = bar_x
    for lang in langs:
        w = bar_w * lang["size"] / total
        parts.append(f'    <rect x="{x:.2f}" y="{bar_y}" width="{w + 0.5:.2f}" height="8" fill="{lang["color"]}"/>')
        x += w
    parts.append("  </g>")
    for i, lang in enumerate(langs):
        lx = 24 + (i % 2) * 196
        ly = 98 + (i // 2) * 30
        pct = 100 * lang["size"] / total
        parts.append(
            f'  <circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{lang["color"]}"/>\n'
            f'  <text x="{lx + 18}" y="{ly}" font-family="{FONT}" font-size="13" fill="{t["text"]}">{escape(lang["name"])}</text>\n'
            f'  <text x="{lx + 172}" y="{ly}" text-anchor="end" font-family="{FONT}" font-size="12" fill="{t["muted"]}">{pct:.1f}%</text>'
        )
    return card(theme, "Most Used Languages", "\n".join(parts))


def main():
    login, out_dir = sys.argv[1], sys.argv[2]
    data = fetch(os.environ["GITHUB_TOKEN"], login)
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        for name, render in (("overview", render_overview), ("languages", render_languages)):
            with open(os.path.join(out_dir, f"stats-{name}-{theme}.svg"), "w", encoding="utf-8") as f:
                f.write(render(data, theme))
    print(json.dumps({k: v for k, v in data.items() if k != "languages"}))


if __name__ == "__main__":
    main()
