from __future__ import annotations

import os
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
    ("Experience", "15 years, 2 months"),
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

    return {
        "name": user.get("name") or USERNAME,
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
    image = Image.open(BytesIO(response.content)).convert("RGB")
    width, height = image.size
    image = image.crop((width * 0.1, height * 0.02, width * 0.9, height * 0.96))
    image = ImageOps.fit(image, (46, 27), method=Image.Resampling.LANCZOS)

    background_samples = [
        image.getpixel((0, 0)),
        image.getpixel((45, 0)),
        image.getpixel((0, 26)),
        image.getpixel((45, 26)),
    ]
    background = tuple(
        sum(sample[channel] for sample in background_samples) // len(background_samples)
        for channel in range(3)
    )
    grayscale = ImageEnhance.Contrast(image.convert("L")).enhance(1.5)
    pixels = list(grayscale.tobytes())
    color_pixels = list(image.getdata())

    def character(index: int) -> str:
        color = color_pixels[index]
        distance = sum((color[channel] - background[channel]) ** 2 for channel in range(3)) ** 0.5
        if distance < 24:
            return " "
        return CHARACTERS[pixels[index] * (len(CHARACTERS) - 1) // 255]

    return [
        "".join(character(row * 46 + column) for column in range(46)).rstrip()
        for row in range(27)
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
