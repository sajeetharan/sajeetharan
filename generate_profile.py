from __future__ import annotations

import os
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageEnhance, ImageOps

USERNAME = os.getenv("GITHUB_USERNAME", "sajeetharan")
TOKEN = os.getenv("GITHUB_TOKEN")
ROOT = Path(__file__).parent
API = "https://api.github.com"
CHARACTERS = "@%#*+=-:. "

DETAILS = [
    ("Role", "Principal Product Manager"),
    ("Company", "Microsoft / Azure Cosmos DB"),
    ("Focus", "AI agents, databases, developer tools"),
    ("Cloud", "Azure, Cosmos DB, Kubernetes, Docker"),
    ("Languages", "TypeScript, JavaScript, Python, C#"),
    ("Frameworks", "Angular, React, Node.js, GraphQL"),
    ("Community", "GDE, Microsoft MVP, speaker"),
]

CONTACT = [
    ("Website", "sajeetharan.dev"),
    ("LinkedIn", "linkedin.com/in/sajeetharan"),
    ("X", "@kokkisajee"),
    ("YouTube", "@coffeewithazurecosmosdb"),
]

THEMES = {
    "dark_mode.svg": {
        "background": "#0d1117",
        "border": "#30363d",
        "text": "#c9d1d9",
        "muted": "#8b949e",
        "accent": "#58a6ff",
        "highlight": "#7ee787",
        "portrait": "#c9d1d9",
    },
    "light_mode.svg": {
        "background": "#ffffff",
        "border": "#d0d7de",
        "text": "#24292f",
        "muted": "#57606a",
        "accent": "#0969da",
        "highlight": "#1a7f37",
        "portrait": "#24292f",
    },
}


def headers() -> dict[str, str]:
    result = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{USERNAME}-profile-readme",
    }
    if TOKEN:
        result["Authorization"] = f"Bearer {TOKEN}"
    return result


def github_get(path: str, **params: object) -> requests.Response:
    response = requests.get(
        f"{API}{path}", headers=headers(), params=params, timeout=30
    )
    response.raise_for_status()
    return response


def fetch_stats() -> dict[str, object]:
    user = github_get(f"/users/{USERNAME}").json()
    repos: list[dict[str, object]] = []
    page = 1
    while True:
        batch = github_get(
            f"/users/{USERNAME}/repos",
            type="owner",
            sort="updated",
            per_page=100,
            page=page,
        ).json()
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    contributions = "public activity"
    if TOKEN:
        query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar { totalContributions }
            }
          }
        }
        """
        response = requests.post(
            f"{API}/graphql",
            headers=headers(),
            json={"query": query, "variables": {"login": USERNAME}},
            timeout=30,
        )
        response.raise_for_status()
        contributions = response.json()["data"]["user"]["contributionsCollection"][
            "contributionCalendar"
        ]["totalContributions"]

    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    years = now.year - created.year - ((now.month, now.day) < (created.month, created.day))
    months = (now.month - created.month) % 12

    return {
        "name": user.get("name") or USERNAME,
        "account_age": f"{years} years, {months} months",
        "repos": user["public_repos"],
        "stars": sum(int(repo["stargazers_count"]) for repo in repos),
        "followers": user["followers"],
        "contributions": contributions,
    }


def avatar_ascii() -> list[str]:
    response = requests.get(
        f"https://github.com/{USERNAME}.png?size=460", headers=headers(), timeout=30
    )
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("L")
    image = ImageOps.fit(image, (46, 31))
    image = ImageEnhance.Contrast(image).enhance(1.35)

    pixels = list(image.tobytes())
    return [
        "".join(CHARACTERS[pixel * (len(CHARACTERS) - 1) // 255] for pixel in pixels[row * 46 : (row + 1) * 46]).rstrip()
        for row in range(31)
    ]


def info_line(label: str, value: object, y: int) -> str:
    label_text = f"{label}:"
    dots = "." * max(2, 23 - len(label_text))
    return (
        f'<text x="392" y="{y}" class="line">'
        f'<tspan class="label">{escape(label_text)}</tspan>'
        f'<tspan class="muted"> {dots} </tspan>'
        f'<tspan class="value">{escape(str(value))}</tspan>'
        "</text>"
    )


def render_svg(stats: dict[str, object], portrait: list[str], colors: dict[str, str]) -> str:
    portrait_lines = "\n".join(
        f'<text x="34" y="{78 + index * 13}" class="portrait" xml:space="preserve">{escape(line)}</text>'
        for index, line in enumerate(portrait)
    )

    lines: list[str] = []
    y = 62
    for label, value in [
        (USERNAME, stats["name"]),
        ("Account", stats["account_age"]),
        *DETAILS,
    ]:
        lines.append(info_line(label, value, y))
        y += 20

    y += 10
    lines.append(f'<text x="392" y="{y}" class="section">Contact</text>')
    y += 21
    for label, value in CONTACT:
        lines.append(info_line(label, value, y))
        y += 20

    y += 10
    lines.append(f'<text x="392" y="{y}" class="section">GitHub Stats</text>')
    y += 21
    for label, value in [
        ("Repos", stats["repos"]),
        ("Stars", stats["stars"]),
        ("Followers", stats["followers"]),
        ("Contributions/year", stats["contributions"]),
    ]:
        lines.append(info_line(label, f"{int(value):,}" if isinstance(value, int) else value, y))
        y += 20

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="940" height="520" viewBox="0 0 940 520" role="img" aria-labelledby="title description">
  <title id="title">{escape(stats['name'])}'s GitHub profile</title>
  <desc id="description">ASCII portrait, professional details, contact links, and GitHub statistics for {escape(USERNAME)}.</desc>
  <style>
    .line, .portrait, .section {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    .portrait {{ fill: {colors['portrait']}; font-size: 11px; }}
    .label {{ fill: {colors['accent']}; }}
    .muted {{ fill: {colors['muted']}; }}
    .value {{ fill: {colors['text']}; }}
    .section {{ fill: {colors['highlight']}; font-weight: 700; }}
  </style>
  <rect x="1" y="1" width="938" height="518" rx="6" fill="{colors['background']}" stroke="{colors['border']}" stroke-width="2"/>
  <circle cx="22" cy="22" r="5" fill="#ff5f56"/>
  <circle cx="40" cy="22" r="5" fill="#ffbd2e"/>
  <circle cx="58" cy="22" r="5" fill="#27c93f"/>
  <text x="470" y="27" text-anchor="middle" class="line muted">{escape(USERNAME)}@github: ~</text>
  <line x1="375" y1="48" x2="375" y2="488" stroke="{colors['border']}"/>
  {portrait_lines}
  {''.join(lines)}
  <text x="34" y="493" class="line"><tspan class="highlight" fill="{colors['highlight']}">$</tspan><tspan class="value"> building tools that help developers grow + thrive</tspan><tspan class="label">_</tspan></text>
</svg>
'''


def main() -> None:
    stats = fetch_stats()
    portrait = avatar_ascii()
    for filename, colors in THEMES.items():
        (ROOT / filename).write_text(render_svg(stats, portrait, colors), encoding="utf-8")
    print(
        f"Generated {', '.join(THEMES)} for {USERNAME}: "
        f"{stats['repos']} repos, {stats['stars']} stars, {stats['followers']} followers"
    )


if __name__ == "__main__":
    main()
