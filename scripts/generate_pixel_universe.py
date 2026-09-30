#!/usr/bin/env python3

import os
import json
import math
import random
import urllib.request
import urllib.error
from datetime import date, timedelta
from xml.sax.saxutils import escape


# ============================================================
# CONFIG
# ============================================================

USERNAME = os.environ.get("GH_USER", "MinalMaurya")
TOKEN = os.environ.get("GH_TOKEN")

OUTPUT = "assets/pixel-universe.svg"

WIDTH = 1400
HEIGHT = 560

# Contribution calendar area
GRID_X = 135
GRID_Y = 185

CELL_W = 22
CELL_H = 25

WEEKS = 53
DAYS = 7

GRID_WIDTH = (WEEKS - 1) * CELL_W
GRID_HEIGHT = (DAYS - 1) * CELL_H

BG = "#030817"
BG2 = "#07152F"

BLUE = "#78A9FF"
LIGHT_BLUE = "#BBD7FF"
LAVENDER = "#A995FF"
GOLD = "#FFD27A"
WHITE = "#F5F8FF"

random.seed(42)


# ============================================================
# GITHUB API
# ============================================================

def github_graphql(query, variables):
    if not TOKEN:
        raise RuntimeError("GH_TOKEN is missing.")

    data = json.dumps({
        "query": query,
        "variables": variables
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "MinalMaurya-Pixel-Universe"
        }
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(json.dumps(result["errors"], indent=2))

    return result


def get_contributions():
    today = date.today()
    start = today - timedelta(days=364)

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(
          from: $from
          to: $to
        ) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
        }
      }
    }
    """

    result = github_graphql(
        query,
        {
            "login": USERNAME,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{today.isoformat()}T23:59:59Z"
        }
    )

    calendar = (
        result["data"]["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
    )

    days = []

    for week in calendar["weeks"]:
        for item in week["contributionDays"]:
            days.append({
                "date": item["date"],
                "count": item["contributionCount"],
                "level": item["contributionLevel"]
            })

    # Keep exactly the latest 365 days
    days = sorted(days, key=lambda x: x["date"])[-365:]

    return days, calendar["totalContributions"]


# ============================================================
# SVG HELPERS
# ============================================================

def svg_escape(value):
    return escape(str(value), {'"': "&quot;"})


def star_points(cx, cy, outer, inner, points=4, rotation=-90):
    result = []

    for i in range(points * 2):
        angle = math.radians(
            rotation + (360 / (points * 2)) * i
        )

        radius = outer if i % 2 == 0 else inner

        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius

        result.append(f"{x:.2f},{y:.2f}")

    return " ".join(result)


def four_point_star(cx, cy, size):
    """
    Elegant four-point sparkle.
    """
    return f"""
    <path
      d="
        M {cx:.2f} {cy-size:.2f}
        C {cx+size*0.16:.2f} {cy-size*0.16:.2f},
          {cx+size*0.16:.2f} {cy-size*0.16:.2f},
          {cx+size:.2f} {cy:.2f}
        C {cx+size*0.16:.2f} {cy+size*0.16:.2f},
          {cx+size*0.16:.2f} {cy+size*0.16:.2f},
          {cx:.2f} {cy+size:.2f}
        C {cx-size*0.16:.2f} {cy+size*0.16:.2f},
          {cx-size*0.16:.2f} {cy+size*0.16:.2f},
          {cx-size:.2f} {cy:.2f}
        C {cx-size*0.16:.2f} {cy-size*0.16:.2f},
          {cx-size*0.16:.2f} {cy-size*0.16:.2f},
          {cx:.2f} {cy-size:.2f}
        Z
      "
    />
    """


def diamond_star(cx, cy, size):
    return f"""
    <polygon
      points="{star_points(cx, cy, size, size * 0.25, 4)}"
    />
    """


def six_point_star(cx, cy, size):
    return f"""
    <polygon
      points="{star_points(cx, cy, size, size * 0.38, 6)}"
    />
    """


def eight_point_star(cx, cy, size):
    return f"""
    <polygon
      points="{star_points(cx, cy, size, size * 0.42, 8)}"
    />
    """


def glow_circle(cx, cy, radius, color, opacity):
    return f"""
    <circle
      cx="{cx:.2f}"
      cy="{cy:.2f}"
      r="{radius:.2f}"
      fill="{color}"
      opacity="{opacity}"
      filter="url(#glow)"
    />
    """


# ============================================================
# STAR DESIGN
# ============================================================

def contribution_star(cx, cy, count, day):
    """
    Returns the SVG for a contribution star.

    1       = tiny four-point star
    2-3     = diamond / four-point
    4-6     = six-point star
    7-9     = eight-point star
    10+     = large special gold star
    """

    if count <= 0:
        return ""

    title = f"{day} — {count} contribution"
    if count != 1:
        title += "s"

    # --------------------------------------------------------
    # 1 contribution
    # --------------------------------------------------------
    if count == 1:
        size = 4.2

        return f"""
        <g class="contribution-star">
          <title>{svg_escape(title)}</title>

          <circle
            cx="{cx:.2f}"
            cy="{cy:.2f}"
            r="1.8"
            fill="{LIGHT_BLUE}"
            opacity="0.28"
          />

          <g fill="{LIGHT_BLUE}" opacity="0.90">
            {four_point_star(cx, cy, size)}
          </g>
        </g>
        """

    # --------------------------------------------------------
    # 2-3 contributions
    # --------------------------------------------------------
    if count <= 3:
        size = 5.4

        return f"""
        <g class="contribution-star">
          <title>{svg_escape(title)}</title>

          {glow_circle(cx, cy, 7, BLUE, 0.12)}

          <g fill="{LIGHT_BLUE}" opacity="0.96">
            {diamond_star(cx, cy, size)}
          </g>
        </g>
        """

    # --------------------------------------------------------
    # 4-6 contributions
    # --------------------------------------------------------
    if count <= 6:
        size = 7.0

        return f"""
        <g class="contribution-star">
          <title>{svg_escape(title)}</title>

          {glow_circle(cx, cy, 11, BLUE, 0.15)}

          <g fill="{BLUE}" opacity="0.98">
            {six_point_star(cx, cy, size)}
          </g>

          <circle
            cx="{cx:.2f}"
            cy="{cy:.2f}"
            r="1.2"
            fill="{WHITE}"
          />
        </g>
        """

    # --------------------------------------------------------
    # 7-9 contributions
    # --------------------------------------------------------
    if count <= 9:
        size = 9.0

        return f"""
        <g class="contribution-star">
          <title>{svg_escape(title)}</title>

          {glow_circle(cx, cy, 16, LAVENDER, 0.18)}

          <g fill="{LAVENDER}" opacity="1">
            {eight_point_star(cx, cy, size)}
          </g>

          <circle
            cx="{cx:.2f}"
            cy="{cy:.2f}"
            r="1.7"
            fill="{WHITE}"
          />
        </g>
        """

    # --------------------------------------------------------
    # 10+ contributions
    # --------------------------------------------------------
    size = min(13.5, 9.5 + count * 0.25)

    return f"""
    <g class="contribution-star">
      <title>{svg_escape(title)}</title>

      {glow_circle(cx, cy, 23, GOLD, 0.20)}
      {glow_circle(cx, cy, 11, GOLD, 0.15)}

      <g fill="{GOLD}" opacity="1">
        {four_point_star(cx, cy, size)}
      </g>

      <circle
        cx="{cx:.2f}"
        cy="{cy:.2f}"
        r="2.2"
        fill="{WHITE}"
      />
    </g>
    """


# ============================================================
# BACKGROUND
# ============================================================

def create_background():
    parts = []

    parts.append(f"""
    <defs>

      <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="{BG}" />
        <stop offset="50%" stop-color="{BG2}" />
        <stop offset="100%" stop-color="#020611" />
      </linearGradient>

      <radialGradient id="nebulaBlue">
        <stop offset="0%" stop-color="#2457C5" stop-opacity="0.22" />
        <stop offset="100%" stop-color="#2457C5" stop-opacity="0" />
      </radialGradient>

      <radialGradient id="nebulaPurple">
        <stop offset="0%" stop-color="#6E4FCB" stop-opacity="0.18" />
        <stop offset="100%" stop-color="#6E4FCB" stop-opacity="0" />
      </radialGradient>

      <filter id="glow">
        <feGaussianBlur stdDeviation="3" />
      </filter>

      <filter id="softGlow">
        <feGaussianBlur stdDeviation="7" />
      </filter>

      <linearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#7EA9FF" stop-opacity="0.04" />
        <stop offset="50%" stop-color="#A995FF" stop-opacity="0.30" />
        <stop offset="100%" stop-color="#7EA9FF" stop-opacity="0.04" />
      </linearGradient>

    </defs>

    <rect
      width="{WIDTH}"
      height="{HEIGHT}"
      rx="22"
      fill="url(#background)"
    />

    <!-- Very subtle cosmic atmosphere -->
    <ellipse
      cx="260"
      cy="130"
      rx="390"
      ry="170"
      fill="url(#nebulaBlue)"
    />

    <ellipse
      cx="1120"
      cy="430"
      rx="420"
      ry="190"
      fill="url(#nebulaPurple)"
    />

    <ellipse
      cx="760"
      cy="250"
      rx="500"
      ry="180"
      fill="url(#nebulaBlue)"
      opacity="0.35"
    />
    """)

    # Decorative stars ONLY outside the contribution grid
    decorative = [
        (75, 110, 1.2),
        (110, 150, 0.8),
        (1210, 100, 1.0),
        (1280, 155, 1.3),
        (1335, 75, 0.7),
        (105, 430, 1.1),
        (1260, 430, 0.9),
        (1320, 365, 1.2),
        (520, 90, 0.7),
        (900, 90, 0.8),
        (1160, 500, 1.0),
    ]

    for x, y, r in decorative:
        parts.append(
            f"""
            <circle
              cx="{x}"
              cy="{y}"
              r="{r}"
              fill="{LIGHT_BLUE}"
              opacity="0.45"
            />
            """
        )

    # Shooting stars
    shooting = [
        (1040, 80, 95, 35),
        (1225, 290, 90, 35),
        (300, 470, 75, 30),
    ]

    for x, y, dx, dy in shooting:
        parts.append(
            f"""
            <line
              x1="{x}"
              y1="{y}"
              x2="{x+dx}"
              y2="{y+dy}"
              stroke="{LAVENDER}"
              stroke-width="1.5"
              stroke-linecap="round"
              opacity="0.55"
            />

            <circle
              cx="{x}"
              cy="{y}"
              r="2.2"
              fill="{WHITE}"
              opacity="0.9"
            />
            """
        )

    # Small planet in upper right
    parts.append("""
    <circle
      cx="1290"
      cy="80"
      r="35"
      fill="#142C64"
      opacity="0.8"
    />

    <ellipse
      cx="1290"
      cy="80"
      rx="58"
      ry="15"
      fill="none"
      stroke="#718DFF"
      stroke-width="1"
      opacity="0.30"
      transform="rotate(-15 1290 80)"
    />
    """)

    return "\n".join(parts)


# ============================================================
# MAIN SVG
# ============================================================

def create_svg(days, total_contributions):
    svg = []

    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}">'
    )

    svg.append(create_background())

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    svg.append(f"""
    <text
      x="55"
      y="58"
      fill="{WHITE}"
      font-family="Arial, Helvetica, sans-serif"
      font-size="24"
      font-weight="600"
    >
      Minal's Coding Universe
    </text>

    <text
      x="56"
      y="82"
      fill="{LIGHT_BLUE}"
      font-family="Arial, Helvetica, sans-serif"
      font-size="12"
      opacity="0.70"
    >
      Small steps ✦ Big dreams ✦ Endless code
    </text>
    """)

    # --------------------------------------------------------
    # Month labels
    # --------------------------------------------------------

    month_positions = [
        ("Jan", 0),
        ("Feb", 4),
        ("Mar", 8),
        ("Apr", 13),
        ("May", 17),
        ("Jun", 22),
        ("Jul", 26),
        ("Aug", 31),
        ("Sep", 35),
        ("Oct", 40),
        ("Nov", 44),
        ("Dec", 49),
    ]

    for month, week in month_positions:
        x = GRID_X + week * CELL_W

        svg.append(
            f"""
            <text
              x="{x}"
              y="{GRID_Y - 34}"
              fill="{LIGHT_BLUE}"
              font-family="Arial, Helvetica, sans-serif"
              font-size="11"
              opacity="0.70"
            >
              {month}
            </text>
            """
        )

    # --------------------------------------------------------
    # Day labels
    # --------------------------------------------------------

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for i, name in enumerate(day_names):
        y = GRID_Y + i * CELL_H + 4

        svg.append(
            f"""
            <text
              x="{GRID_X - 42}"
              y="{y}"
              fill="{LIGHT_BLUE}"
              font-family="Arial, Helvetica, sans-serif"
              font-size="10"
              opacity="0.48"
            >
              {name}
            </text>
            """
        )

    # --------------------------------------------------------
    # Create calendar coordinates
    # --------------------------------------------------------

    positions = {}

    # GitHub calendar weeks begin according to the returned data.
    # We map the 365 actual days sequentially into 53 columns x 7 rows.
    for index, item in enumerate(days):
        week = index // 7
        day = index % 7

        if week >= WEEKS:
            break

        x = GRID_X + week * CELL_W
        y = GRID_Y + day * CELL_H

        positions[item["date"]] = {
            "x": x,
            "y": y,
            "count": item["count"],
        }

    # --------------------------------------------------------
    # Subtle 365-day grid
    # --------------------------------------------------------

    for item in days:
        pos = positions.get(item["date"])

        if not pos:
            continue

        x = pos["x"]
        y = pos["y"]

        # ALL days have a tiny dot.
        # It is deliberately very faint.
        opacity = 0.14

        # Only a very small random subset receives a tiny
        # atmospheric highlight.
        special = (
            item["count"] == 0
            and random.random() < 0.10
        )

        if special:
            opacity = 0.23

        svg.append(
            f"""
            <circle
              cx="{x:.2f}"
              cy="{y:.2f}"
              r="1.15"
              fill="{LIGHT_BLUE}"
              opacity="{opacity}"
            />
            """
        )

    # --------------------------------------------------------
    # Contribution constellation lines
    # --------------------------------------------------------

    # Connect nearby ACTIVE contribution days.
    # We keep this intentionally sparse.
    active = [
        item for item in days
        if item["count"] > 0
    ]

    for i in range(len(active) - 1):
        current = active[i]
        nxt = active[i + 1]

        p1 = positions.get(current["date"])
        p2 = positions.get(nxt["date"])

        if not p1 or not p2:
            continue

        # Calculate distance.
        distance = math.sqrt(
            (p2["x"] - p1["x"]) ** 2 +
            (p2["y"] - p1["y"]) ** 2
        )

        # Only connect reasonably close contribution days.
        if distance <= CELL_W * 2.5:

            opacity = 0.18

            # Higher activity = slightly more visible line
            if current["count"] >= 4 and nxt["count"] >= 4:
                opacity = 0.25

            svg.append(
                f"""
                <line
                  x1="{p1['x']:.2f}"
                  y1="{p1['y']:.2f}"
                  x2="{p2['x']:.2f}"
                  y2="{p2['y']:.2f}"
                  stroke="url(#lineGradient)"
                  stroke-width="0.8"
                  opacity="{opacity}"
                />
                """
            )

    # --------------------------------------------------------
    # Contribution stars
    # --------------------------------------------------------

    for item in days:

        if item["count"] <= 0:
            continue

        pos = positions.get(item["date"])

        if not pos:
            continue

        svg.append(
            contribution_star(
                pos["x"],
                pos["y"],
                item["count"],
                item["date"]
            )
        )

    # --------------------------------------------------------
    # Bottom message
    # --------------------------------------------------------

    svg.append(f"""
    <text
      x="{WIDTH / 2}"
      y="500"
      text-anchor="middle"
      fill="{LIGHT_BLUE}"
      font-family="Arial, Helvetica, sans-serif"
      font-size="14"
      letter-spacing="4"
      opacity="0.82"
    >
      EVERY LITTLE CONTRIBUTION BECOMES A STAR
    </text>

    <line
      x1="590"
      y1="518"
      x2="810"
      y2="518"
      stroke="{LAVENDER}"
      stroke-width="1"
      opacity="0.30"
    />

    <text
      x="{WIDTH / 2}"
      y="542"
      text-anchor="middle"
      fill="{LIGHT_BLUE}"
      font-family="Arial, Helvetica, sans-serif"
      font-size="10"
      opacity="0.48"
    >
      {total_contributions} contributions in the last year
    </text>
    """)

    svg.append("</svg>")

    return "\n".join(svg)


# ============================================================
# WRITE FILE
# ============================================================

def main():
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    print(f"Fetching GitHub contributions for {USERNAME}...")

    days, total = get_contributions()

    print(f"Received {len(days)} days.")
    print(f"Total contributions: {total}")

    svg = create_svg(days, total)

    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)

    print(f"Generated: {OUTPUT}")


if __name__ == "__main__":
    main()