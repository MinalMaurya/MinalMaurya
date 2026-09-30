import os
import json
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

WIDTH = 1400
HEIGHT = 560

GH_TOKEN = os.environ.get("GH_TOKEN")
GH_USER = os.environ.get("GH_USER", "MinalMaurya")

OUTPUT_FILE = "assets/pixel-universe.svg"

random.seed(2026)


# ============================================================
# GITHUB CONTRIBUTION DATA
# ============================================================

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
          }
        }
      }
    }
  }
}
"""


def get_contributions():
    if not GH_TOKEN:
        raise RuntimeError("GH_TOKEN environment variable is missing.")

    payload = json.dumps({
        "query": QUERY,
        "variables": {
            "login": GH_USER
        }
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "pixel-universe-generator"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"GitHub API request failed: {error.code}\n{body}"
        )

    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))

    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

    contributions = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            contributions.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })

    return contributions, calendar["totalContributions"]


# ============================================================
# SVG HELPERS
# ============================================================

def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def star_points(cx, cy, outer, inner, points=4, rotation=-90):
    values = []

    for i in range(points * 2):
        angle = rotation + (360 / (points * 2)) * i
        radius = outer if i % 2 == 0 else inner

        import math

        x = cx + math.cos(math.radians(angle)) * radius
        y = cy + math.sin(math.radians(angle)) * radius

        values.append(f"{x:.2f},{y:.2f}")

    return " ".join(values)


def diamond_star(cx, cy, size):
    return (
        f"M {cx:.2f},{cy-size:.2f} "
        f"L {cx+size*0.34:.2f},{cy-size*0.34:.2f} "
        f"L {cx+size:.2f},{cy:.2f} "
        f"L {cx+size*0.34:.2f},{cy+size*0.34:.2f} "
        f"L {cx:.2f},{cy+size:.2f} "
        f"L {cx-size*0.34:.2f},{cy+size*0.34:.2f} "
        f"L {cx-size:.2f},{cy:.2f} "
        f"L {cx-size*0.34:.2f},{cy-size*0.34:.2f} Z"
    )


def glow_circle(cx, cy, r, color, opacity=0.3):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{color}" opacity="{opacity}" filter="url(#softGlow)"/>'
    )


# ============================================================
# COSMIC BACKGROUND
# ============================================================

def background_elements():
    parts = []

    # --------------------------------------------------------
    # Deep space base
    # --------------------------------------------------------

    parts.append(
        '<rect width="1400" height="560" fill="url(#spaceGradient)"/>'
    )

    # --------------------------------------------------------
    # Large nebula clouds
    # --------------------------------------------------------

    nebulae = [
        (230, 260, 360, 150, "#193b86", 0.24),
        (560, 170, 420, 190, "#392b8f", 0.20),
        (900, 245, 460, 190, "#254d9f", 0.20),
        (1180, 180, 330, 180, "#552c9d", 0.17),
        (700, 470, 600, 170, "#352879", 0.22),
        (180, 470, 360, 130, "#214c9c", 0.18),
    ]

    for cx, cy, rx, ry, color, opacity in nebulae:
        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
            f'fill="{color}" opacity="{opacity}" '
            f'filter="url(#nebulaBlur)"/>'
        )

    # --------------------------------------------------------
    # Milky Way band
    # --------------------------------------------------------

    parts.append(
        '<path d="M -100 400 '
        'C 250 190, 480 130, 760 250 '
        'C 1000 350, 1190 230, 1500 60" '
        'fill="none" stroke="url(#milkyGradient)" '
        'stroke-width="125" opacity="0.13" '
        'filter="url(#milkyBlur)"/>'
    )

    parts.append(
        '<path d="M -80 385 '
        'C 260 190, 500 155, 770 255 '
        'C 1010 335, 1210 215, 1490 55" '
        'fill="none" stroke="url(#milkyGradient2)" '
        'stroke-width="48" opacity="0.14" '
        'filter="url(#milkyBlur)"/>'
    )

    # --------------------------------------------------------
    # Tiny background stars
    # --------------------------------------------------------

    for _ in range(145):
        x = random.uniform(20, WIDTH - 20)
        y = random.uniform(15, 480)

        # Keep background stars away from the contribution grid.
        if 175 < x < 1270 and 215 < y < 415:
            continue

        radius = random.choice([
            0.45, 0.55, 0.65, 0.8, 1.0
        ])

        opacity = random.uniform(0.25, 0.75)

        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" '
            f'r="{radius}" fill="#dce9ff" opacity="{opacity:.2f}"/>'
        )

    # --------------------------------------------------------
    # A few brighter stars
    # --------------------------------------------------------

    bright_stars = [
        (110, 90, 1.7),
        (205, 160, 1.3),
        (690, 80, 1.6),
        (820, 145, 1.4),
        (1060, 95, 1.8),
        (1290, 145, 1.5),
        (1330, 290, 1.3),
        (90, 315, 1.2),
    ]

    for x, y, r in bright_stars:
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r}" '
            f'fill="#ffffff" opacity="0.85"/>'
        )

        parts.append(
            f'<circle cx="{x}" cy="{y}" r="{r*3.2}" '
            f'fill="#9dbaff" opacity="0.12" filter="url(#softGlow)"/>'
        )

    return parts


# ============================================================
# PLANETS
# ============================================================

def planet_elements():
    parts = []

    # Large planet - top right
    parts.append(
        '<circle cx="1280" cy="78" r="72" fill="url(#planetGradient)" '
        'opacity="0.92"/>'
    )

    parts.append(
        '<ellipse cx="1280" cy="78" rx="112" ry="28" '
        'fill="none" stroke="#7088ff" stroke-width="2" '
        'opacity="0.50" transform="rotate(-12 1280 78)"/>'
    )

    parts.append(
        '<ellipse cx="1280" cy="78" rx="105" ry="24" '
        'fill="none" stroke="#a58cff" stroke-width="1" '
        'opacity="0.35" transform="rotate(-12 1280 78)"/>'
    )

    # Small planet - left
    parts.append(
        '<circle cx="90" cy="205" r="25" fill="url(#smallPlanet)" '
        'opacity="0.90"/>'
    )

    parts.append(
        '<ellipse cx="90" cy="205" rx="39" ry="9" '
        'fill="none" stroke="#668cff" stroke-width="1" '
        'opacity="0.35" transform="rotate(-15 90 205)"/>'
    )

    # Small distant planet
    parts.append(
        '<circle cx="1360" cy="170" r="14" '
        'fill="url(#tinyPlanet)" opacity="0.75"/>'
    )

    return parts


# ============================================================
# SHOOTING STARS
# ============================================================

def shooting_stars():
    parts = []

    stars = [
        (1110, 92, 1025, 52),
        (470, 470, 560, 420),
        (1360, 320, 1290, 375),
        (760, 120, 700, 86),
    ]

    for x1, y1, x2, y2 in stars:
        parts.append(
            f'<line x1="{x1}" y1="{y1}" '
            f'x2="{x2}" y2="{y2}" '
            f'stroke="url(#shootGradient)" '
            f'stroke-width="2" opacity="0.65"/>'
        )

        parts.append(
            f'<circle cx="{x1}" cy="{y1}" r="2.2" '
            f'fill="#ffffff" opacity="0.95" '
            f'filter="url(#softGlow)"/>'
        )

    return parts


# ============================================================
# COSMIC CLOUDS
# ============================================================

def cloud_cluster(x, y, scale=1.0):
    parts = []

    circles = [
        (-55, 10, 32),
        (-30, -12, 38),
        (0, -20, 44),
        (35, -5, 35),
        (65, 12, 30),
        (25, 22, 48),
        (-15, 25, 42),
    ]

    for dx, dy, r in circles:
        parts.append(
            f'<circle cx="{x + dx*scale:.1f}" '
            f'cy="{y + dy*scale:.1f}" '
            f'r="{r*scale:.1f}" '
            f'fill="url(#cloudGradient)" '
            f'opacity="0.55" '
            f'filter="url(#cloudBlur)"/>'
        )

    return parts


def cloud_elements():
    parts = []

    parts.extend(cloud_cluster(70, 475, 1.0))
    parts.extend(cloud_cluster(270, 495, 0.85))
    parts.extend(cloud_cluster(1120, 490, 1.0))
    parts.extend(cloud_cluster(1320, 470, 0.85))

    return parts


# ============================================================
# MOUNTAIN LANDSCAPE
# ============================================================

def mountain_elements():
    parts = []

    # Far mountains
    parts.append(
        '<path d="M 0 525 '
        'L 80 465 L 145 510 '
        'L 225 440 L 310 510 '
        'L 390 455 L 470 520 '
        'L 555 445 L 640 515 '
        'L 720 455 L 800 515 '
        'L 890 450 L 980 520 '
        'L 1080 440 L 1160 510 '
        'L 1250 455 L 1320 505 '
        'L 1400 445 L 1400 560 L 0 560 Z" '
        'fill="url(#farMountain)" opacity="0.72"/>'
    )

    # Main mountain range
    parts.append(
        '<path d="M 0 555 '
        'L 90 505 '
        'L 145 530 '
        'L 225 455 '
        'L 300 535 '
        'L 385 485 '
        'L 465 545 '
        'L 560 470 '
        'L 640 540 '
        'L 725 480 '
        'L 810 545 '
        'L 900 475 '
        'L 990 535 '
        'L 1080 465 '
        'L 1170 540 '
        'L 1260 480 '
        'L 1330 530 '
        'L 1400 470 '
        'L 1400 560 L 0 560 Z" '
        'fill="url(#mountainGradient)"/>'
    )

    # Mountain highlights
    parts.append(
        '<path d="M 90 505 L 145 530 L 225 455 '
        'L 185 505 L 145 495 Z" '
        'fill="#7d91db" opacity="0.16"/>'
    )

    parts.append(
        '<path d="M 560 470 L 640 540 L 610 500 '
        'L 585 500 Z" '
        'fill="#8a9de8" opacity="0.14"/>'
    )

    parts.append(
        '<path d="M 1080 465 L 1170 540 L 1125 495 '
        'L 1098 500 Z" '
        'fill="#8b9df0" opacity="0.13"/>'
    )

    return parts


# ============================================================
# CONTRIBUTION GRID
# ============================================================

GRID_X = 185
GRID_Y = 255

CELL_W = 21
CELL_H = 25

GRID_WEEKS = 53
GRID_DAYS = 7


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def contribution_star(cx, cy, count):
    elements = []

    # --------------------------------------------------------
    # 1 contribution
    # --------------------------------------------------------

    if count == 1:
        size = 4.2

        elements.append(
            f'<polygon points="{star_points(cx, cy, size, 1.3, 4)}" '
            f'fill="#9ec5ff" opacity="0.92"/>'
        )

        return elements

    # --------------------------------------------------------
    # 2–3 contributions
    # --------------------------------------------------------

    if 2 <= count <= 3:
        size = 5.2

        elements.append(
            f'<path d="{diamond_star(cx, cy, size)}" '
            f'fill="#8bb9ff" opacity="0.96"/>'
        )

        elements.append(
            glow_circle(cx, cy, 10, "#6da4ff", 0.16)
        )

        return elements

    # --------------------------------------------------------
    # 4–6 contributions
    # --------------------------------------------------------

    if 4 <= count <= 6:
        size = 6.5

        elements.append(
            f'<polygon points="{star_points(cx, cy, size, 2.2, 6)}" '
            f'fill="#8fb9ff" opacity="0.98"/>'
        )

        elements.append(
            glow_circle(cx, cy, 13, "#709eff", 0.20)
        )

        return elements

    # --------------------------------------------------------
    # 7–9 contributions
    # --------------------------------------------------------

    if 7 <= count <= 9:
        size = 8.5

        elements.append(
            f'<polygon points="{star_points(cx, cy, size, 2.4, 8)}" '
            f'fill="#c4b3ff" opacity="1"/>'
        )

        elements.append(
            glow_circle(cx, cy, 17, "#8d75ff", 0.24)
        )

        return elements

    # --------------------------------------------------------
    # 10+ contributions
    # --------------------------------------------------------

    size = min(12.5, 8.5 + (count - 10) * 0.25)

    elements.append(
        f'<polygon points="{star_points(cx, cy, size, size*0.28, 4)}" '
        f'fill="#ffe1a0" opacity="1"/>'
    )

    elements.append(
        glow_circle(cx, cy, size * 2.0, "#ffc85a", 0.28)
    )

    # central bright point
    elements.append(
        f'<circle cx="{cx}" cy="{cy}" r="1.5" '
        f'fill="#ffffff" opacity="0.98"/>'
    )

    return elements


def grid_elements(contributions):
    parts = []

    # --------------------------------------------------------
    # Contribution data indexed by date
    # --------------------------------------------------------

    data = {
        item["date"]: item["count"]
        for item in contributions
    }

    dates = sorted(parse_date(item["date"]) for item in contributions)

    if not dates:
        return parts

    first_date = dates[0]

    # Align to Sunday.
    start_date = first_date - timedelta(days=(first_date.weekday() + 1) % 7)

    # --------------------------------------------------------
    # Calendar labels
    # --------------------------------------------------------

    month_seen = set()

    for week in range(GRID_WEEKS):
        current = start_date + timedelta(days=week * 7)

        for day_index in range(7):
            day = current + timedelta(days=day_index)

            if day.day <= 7:
                month_name = day.strftime("%b")

                if month_name not in month_seen:
                    month_seen.add(month_name)

                    x = GRID_X + week * CELL_W

                    parts.append(
                        f'<text x="{x}" y="{GRID_Y - 28}" '
                        f'fill="#8fa8d6" font-size="13" '
                        f'font-family="Arial, sans-serif" '
                        f'text-anchor="middle" opacity="0.90">'
                        f'{month_name}</text>'
                    )

    # --------------------------------------------------------
    # Weekday labels
    # --------------------------------------------------------

    weekdays = [
        ("Mon", 1),
        ("Wed", 3),
        ("Fri", 5),
        ("Sun", 0),
    ]

    for label, sunday_index in weekdays:
        if label == "Sun":
            row = 0
        else:
            row = sunday_index

        y = GRID_Y + row * CELL_H + 4

        parts.append(
            f'<text x="{GRID_X - 25}" y="{y}" '
            f'fill="#7f98c5" font-size="11" '
            f'font-family="Arial, sans-serif" '
            f'text-anchor="end" opacity="0.85">'
            f'{label}</text>'
        )

    # --------------------------------------------------------
    # Every calendar day gets a tiny dot
    # --------------------------------------------------------

    active_points = []

    for week in range(GRID_WEEKS):
        for day_index in range(GRID_DAYS):
            current = start_date + timedelta(
                days=week * 7 + day_index
            )

            date_string = current.isoformat()

            x = GRID_X + week * CELL_W
            y = GRID_Y + day_index * CELL_H

            count = data.get(date_string, 0)

            # Don't draw days outside GitHub's returned year.
            if date_string not in data:
                parts.append(
                    f'<circle cx="{x}" cy="{y}" r="1.15" '
                    f'fill="#6883b8" opacity="0.22"/>'
                )

                continue

            # ------------------------------------------------
            # Zero contribution
            # ------------------------------------------------

            if count == 0:
                parts.append(
                    f'<circle cx="{x}" cy="{y}" r="1.25" '
                    f'fill="#718bbd" opacity="0.26"/>'
                )

                # A few atmospheric zero-day highlights.
                if random.random() < 0.08:
                    parts.append(
                        f'<circle cx="{x}" cy="{y}" r="3.8" '
                        f'fill="#668fff" opacity="0.07" '
                        f'filter="url(#softGlow)"/>'
                    )

                continue

            # ------------------------------------------------
            # Active contribution star
            # ------------------------------------------------

            active_points.append((x, y, count))

            parts.append(
                f'<g aria-label="{esc(date_string)}: '
                f'{count} contribution(s)">'
            )

            parts.extend(
                contribution_star(x, y, count)
            )

            # SVG title is retained for renderers that support it.
            parts.append(
                f'<title>{esc(date_string)} — '
                f'{count} contribution'
                f'{"s" if count != 1 else ""}</title>'
            )

            parts.append("</g>")

    # --------------------------------------------------------
    # Constellation lines
    # --------------------------------------------------------

    for i in range(len(active_points)):
        x1, y1, count1 = active_points[i]

        for j in range(i + 1, len(active_points)):
            x2, y2, count2 = active_points[j]

            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            # Only connect nearby stars.
            if dx <= CELL_W * 2.2 and dy <= CELL_H * 1.7:
                opacity = 0.10

                if count1 >= 4 or count2 >= 4:
                    opacity = 0.15

                parts.append(
                    f'<line x1="{x1}" y1="{y1}" '
                    f'x2="{x2}" y2="{y2}" '
                    f'stroke="#7e9fe5" '
                    f'stroke-width="0.65" '
                    f'opacity="{opacity}"/>'
                )

    return parts


# ============================================================
# SVG DOCUMENT
# ============================================================

def build_svg(contributions, total):
    parts = []

    parts.append(
        f'''<svg xmlns="http://www.w3.org/2000/svg"
             width="{WIDTH}"
             height="{HEIGHT}"
             viewBox="0 0 {WIDTH} {HEIGHT}">
'''
    )

    # --------------------------------------------------------
    # DEFINITIONS
    # --------------------------------------------------------

    parts.append("""
<defs>

  <!-- Deep space -->
  <linearGradient id="spaceGradient"
                   x1="0" y1="0"
                   x2="0" y2="1">
    <stop offset="0%" stop-color="#020817"/>
    <stop offset="42%" stop-color="#061536"/>
    <stop offset="75%" stop-color="#0b1742"/>
    <stop offset="100%" stop-color="#090b25"/>
  </linearGradient>

  <!-- Nebula -->
  <linearGradient id="milkyGradient"
                  x1="0" y1="0"
                  x2="1" y2="0">
    <stop offset="0%" stop-color="#1d5dff"/>
    <stop offset="40%" stop-color="#7666ff"/>
    <stop offset="75%" stop-color="#b27dff"/>
    <stop offset="100%" stop-color="#234dff"/>
  </linearGradient>

  <linearGradient id="milkyGradient2"
                  x1="0" y1="0"
                  x2="1" y2="0">
    <stop offset="0%" stop-color="#6a9bff"/>
    <stop offset="50%" stop-color="#a58cff"/>
    <stop offset="100%" stop-color="#4e7dff"/>
  </linearGradient>

  <!-- Shooting stars -->
  <linearGradient id="shootGradient"
                  x1="0" y1="0"
                  x2="1" y2="0">
    <stop offset="0%" stop-color="#8d7cff" stop-opacity="0"/>
    <stop offset="75%" stop-color="#a8a5ff" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="#ffffff" stop-opacity="1"/>
  </linearGradient>

  <!-- Planets -->
  <radialGradient id="planetGradient"
                  cx="35%" cy="30%">
    <stop offset="0%" stop-color="#819eff"/>
    <stop offset="38%" stop-color="#314aab"/>
    <stop offset="75%" stop-color="#101b58"/>
    <stop offset="100%" stop-color="#050a2b"/>
  </radialGradient>

  <radialGradient id="smallPlanet"
                  cx="35%" cy="30%">
    <stop offset="0%" stop-color="#668cff"/>
    <stop offset="50%" stop-color="#1d438d"/>
    <stop offset="100%" stop-color="#08183f"/>
  </radialGradient>

  <radialGradient id="tinyPlanet">
    <stop offset="0%" stop-color="#7d91ff"/>
    <stop offset="100%" stop-color="#172b78"/>
  </radialGradient>

  <!-- Clouds -->
  <radialGradient id="cloudGradient"
                  cx="50%" cy="40%">
    <stop offset="0%" stop-color="#bca4ff"/>
    <stop offset="45%" stop-color="#675bc7"/>
    <stop offset="100%" stop-color="#25255f"/>
  </radialGradient>

  <!-- Mountains -->
  <linearGradient id="farMountain"
                  x1="0" y1="0"
                  x2="0" y2="1">
    <stop offset="0%" stop-color="#243d83"/>
    <stop offset="100%" stop-color="#070d29"/>
  </linearGradient>

  <linearGradient id="mountainGradient"
                  x1="0" y1="0"
                  x2="0" y2="1">
    <stop offset="0%" stop-color="#101b4a"/>
    <stop offset="50%" stop-color="#080d2b"/>
    <stop offset="100%" stop-color="#020511"/>
  </linearGradient>

  <!-- Glow -->
  <filter id="softGlow"
          x="-100%"
          y="-100%"
          width="300%"
          height="300%">
    <feGaussianBlur stdDeviation="4"/>
  </filter>

  <filter id="nebulaBlur"
          x="-30%"
          y="-30%"
          width="160%"
          height="160%">
    <feGaussianBlur stdDeviation="55"/>
  </filter>

  <filter id="milkyBlur"
          x="-20%"
          y="-20%"
          width="140%"
          height="140%">
    <feGaussianBlur stdDeviation="25"/>
  </filter>

  <filter id="cloudBlur"
          x="-50%"
          y="-50%"
          width="200%"
          height="200%">
    <feGaussianBlur stdDeviation="8"/>
  </filter>

</defs>
""")

    # --------------------------------------------------------
    # Background
    # --------------------------------------------------------

    parts.extend(background_elements())
    parts.extend(planet_elements())
    parts.extend(shooting_stars())

    # --------------------------------------------------------
    # Contribution grid
    # --------------------------------------------------------

    parts.extend(grid_elements(contributions))

    # --------------------------------------------------------
    # Cosmic clouds + mountains
    # --------------------------------------------------------

    parts.extend(cloud_elements())
    parts.extend(mountain_elements())

    # --------------------------------------------------------
    # Bottom message
    # --------------------------------------------------------

    parts.append(
        '<text x="700" y="495" '
        'fill="#aab9ef" '
        'font-size="14" '
        'font-family="Arial, sans-serif" '
        'letter-spacing="4" '
        'text-anchor="middle" '
        'opacity="0.82">'
        'EVERY LITTLE CONTRIBUTION BECOMES A STAR'
        '</text>'
    )

    parts.append(
        '<line x1="620" y1="512" '
        'x2="780" y2="512" '
        'stroke="#8297e8" '
        'stroke-width="1" '
        'opacity="0.35"/>'
    )

    # Small star below message
    parts.append(
        f'<polygon points="{star_points(700, 512, 5, 1.5, 4)}" '
        'fill="#a8bcff" opacity="0.75"/>'
    )

    # --------------------------------------------------------
    # Total contribution count
    # --------------------------------------------------------

    parts.append(
        f'<text x="700" y="538" '
        'fill="#7387b8" '
        'font-size="11" '
        'font-family="Arial, sans-serif" '
        'text-anchor="middle" '
        'opacity="0.85">'
        f'{total} contributions in the last year'
        '</text>'
    )

    parts.append("</svg>")

    return "\n".join(parts)


# ============================================================
# MAIN
# ============================================================

def main():
    print("Fetching GitHub contribution data...")

    contributions, total = get_contributions()

    print(
        f"Found {len(contributions)} contribution days "
        f"and {total} total contributions."
    )

    svg = build_svg(contributions, total)

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(svg)

    print(f"Generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()