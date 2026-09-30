import os
import json
import random
import math
import urllib.request
import urllib.error
from datetime import datetime, timedelta


# ============================================================
# PIXEL UNIVERSE
# Cinematic cosmic GitHub contribution calendar
# ============================================================

WIDTH = 1400
HEIGHT = 560

GH_TOKEN = os.environ.get("GH_TOKEN")
GH_USER = os.environ.get("GH_USER", "MinalMaurya")

OUTPUT_FILE = "assets/pixel-universe.svg"

random.seed(42)


# ============================================================
# GITHUB API
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
        raise RuntimeError("GH_TOKEN is missing.")

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
            "User-Agent": "MinalMaurya-PixelUniverse"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )
    except urllib.error.HTTPError as error:
        body = error.read().decode(
            "utf-8",
            errors="ignore"
        )
        raise RuntimeError(
            f"GitHub API error {error.code}: {body}"
        )

    if "errors" in result:
        raise RuntimeError(
            json.dumps(result["errors"], indent=2)
        )

    calendar = (
        result["data"]
        ["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
    )

    days = []

    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            days.append({
                "date": day["date"],
                "count": day["contributionCount"]
            })

    return days, calendar["totalContributions"]


# ============================================================
# HELPERS
# ============================================================

def esc(value):

    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def star_points(
    cx,
    cy,
    outer,
    inner,
    points=4,
    rotation=-90
):

    result = []

    for i in range(points * 2):

        angle = math.radians(
            rotation +
            (360 / (points * 2)) * i
        )

        radius = (
            outer
            if i % 2 == 0
            else inner
        )

        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius

        result.append(
            f"{x:.2f},{y:.2f}"
        )

    return " ".join(result)


def diamond(cx, cy, size):

    return (
        f"M {cx},{cy-size} "
        f"L {cx+size*0.35},{cy-size*0.35} "
        f"L {cx+size},{cy} "
        f"L {cx+size*0.35},{cy+size*0.35} "
        f"L {cx},{cy+size} "
        f"L {cx-size*0.35},{cy+size*0.35} "
        f"L {cx-size},{cy} "
        f"L {cx-size*0.35},{cy-size*0.35} Z"
    )


# ============================================================
# COSMIC BACKGROUND
# ============================================================

def cosmic_background():

    p = []

    # Deep space base
    p.append(
        '<rect width="1400" height="560" fill="url(#space)"/>'
    )

    # Large soft nebula clouds
    nebulae = [
        (160, 140, 360, 190, "#1749b7", .25),
        (430, 100, 360, 170, "#4523a7", .22),
        (700, 150, 470, 210, "#174bcb", .20),
        (980, 160, 420, 180, "#5528b8", .20),
        (1210, 320, 350, 220, "#3e218f", .24),
        (690, 390, 520, 150, "#351c91", .23),
        (300, 400, 450, 160, "#193e9c", .18),
    ]

    for cx, cy, rx, ry, color, opacity in nebulae:

        p.append(
            f'<ellipse cx="{cx}" cy="{cy}" '
            f'rx="{rx}" ry="{ry}" '
            f'fill="{color}" '
            f'opacity="{opacity}" '
            f'filter="url(#nebula)"/>'
        )

    # Milky Way
    p.append(
        '<path '
        'd="M-100 380 '
        'C250 120 500 110 760 260 '
        'C1010 420 1190 220 1500 40" '
        'fill="none" '
        'stroke="url(#milky)" '
        'stroke-width="150" '
        'opacity=".18" '
        'filter="url(#milkyBlur)"/>'
    )

    p.append(
        '<path '
        'd="M-100 380 '
        'C250 120 500 110 760 260 '
        'C1010 420 1190 220 1500 40" '
        'fill="none" '
        'stroke="url(#milky2)" '
        'stroke-width="55" '
        'opacity=".17" '
        'filter="url(#milkyBlur)"/>'
    )

    # Atmospheric background stars
    for _ in range(240):

        x = random.uniform(15, WIDTH - 15)
        y = random.uniform(10, 470)

        # Keep decorative stars away from contribution grid
        if (
            180 < x < 1320
            and
            205 < y < 410
        ):
            continue

        r = random.choice([
            .35,
            .45,
            .55,
            .65,
            .8,
            1.0
        ])

        opacity = random.uniform(.20, .75)

        p.append(
            f'<circle cx="{x:.1f}" '
            f'cy="{y:.1f}" '
            f'r="{r}" '
            f'fill="#dce7ff" '
            f'opacity="{opacity:.2f}"/>'
        )

    # A few brighter distant stars
    for x, y, r in [
        (90, 100, 1.5),
        (210, 155, 1.2),
        (690, 75, 1.5),
        (825, 105, 1.7),
        (1030, 120, 1.4),
        (1160, 75, 1.5),
        (1340, 260, 1.2),
    ]:

        p.append(
            f'<circle cx="{x}" cy="{y}" '
            f'r="{r}" fill="#ffffff" opacity=".9"/>'
        )

    return p


# ============================================================
# PLANETS
# ============================================================

def planets():

    p = []

    # Large ringed planet
    p.append(
        '<circle cx="1295" cy="70" r="82" fill="url(#planet)"/>'
    )

    p.append(
        '<ellipse '
        'cx="1295" cy="70" '
        'rx="130" ry="31" '
        'fill="none" '
        'stroke="#786cff" '
        'stroke-width="3" '
        'opacity=".65" '
        'transform="rotate(-13 1295 70)"/>'
    )

    p.append(
        '<ellipse '
        'cx="1295" cy="70" '
        'rx="112" ry="24" '
        'fill="none" '
        'stroke="#9c86ff" '
        'stroke-width="1.5" '
        'opacity=".55" '
        'transform="rotate(-13 1295 70)"/>'
    )

    # Small moon
    p.append(
        '<circle cx="1360" cy="155" r="19" fill="url(#moon)"/>'
    )

    # Planetary horizon
    p.append(
        '<path '
        'd="M-80 500 '
        'C80 420 230 420 390 500 '
        'C530 560 720 570 860 520 '
        'C1040 455 1220 425 1480 500 '
        'L1480 570 L-80 570 Z" '
        'fill="url(#horizon)"/>'
    )

    p.append(
        '<path '
        'd="M-80 500 '
        'C80 420 230 420 390 500" '
        'fill="none" '
        'stroke="#6b9cff" '
        'stroke-width="3" '
        'opacity=".55" '
        'filter="url(#glow)"/>'
    )

    return p


# ============================================================
# SHOOTING STARS
# ============================================================

def shooting_stars():

    p = []

    trails = [
        (1130, 90, 1030, 42),
        (550, 465, 630, 410),
        (1380, 305, 1310, 350),
        (750, 105, 690, 70),
        (450, 180, 390, 215),
    ]

    for x1, y1, x2, y2 in trails:

        p.append(
            f'<line x1="{x1}" y1="{y1}" '
            f'x2="{x2}" y2="{y2}" '
            f'stroke="url(#shoot)" '
            f'stroke-width="2" opacity=".7"/>'
        )

        p.append(
            f'<circle cx="{x1}" cy="{y1}" '
            f'r="2.4" fill="#ffffff" '
            f'filter="url(#glow)"/>'
        )

    return p


# ============================================================
# CLOUDS
# ============================================================

def clouds():

    p = []

    clusters = [
        (30, 490, 1.0),
        (190, 510, .85),
        (350, 520, .75),
        (1050, 505, .95),
        (1220, 500, .9),
        (1370, 475, 1.0),
    ]

    for x, y, scale in clusters:

        circles = [
            (-50, 10, 35),
            (-28, -10, 43),
            (0, -20, 48),
            (35, -5, 40),
            (62, 12, 32),
            (20, 25, 46),
        ]

        for dx, dy, radius in circles:

            p.append(
                f'<circle '
                f'cx="{x + dx*scale:.1f}" '
                f'cy="{y + dy*scale:.1f}" '
                f'r="{radius*scale:.1f}" '
                f'fill="url(#cloud)" '
                f'opacity=".65" '
                f'filter="url(#cloudBlur)"/>'
            )

    return p


# ============================================================
# MOUNTAINS
# ============================================================

def mountains():

    p = []

    # Far mountains
    p.append(
        '<path '
        'd="M0 560 '
        'L0 525 '
        'L90 480 '
        'L155 520 '
        'L235 450 '
        'L315 520 '
        'L400 470 '
        'L480 530 '
        'L570 455 '
        'L650 525 '
        'L735 465 '
        'L820 530 '
        'L910 455 '
        'L1000 525 '
        'L1090 465 '
        'L1180 530 '
        'L1260 460 '
        'L1340 520 '
        'L1400 465 '
        'L1400 560 Z" '
        'fill="url(#farMountains)"/>'
    )

    # Foreground mountains
    p.append(
        '<path '
        'd="M0 560 '
        'L0 545 '
        'L110 495 '
        'L180 550 '
        'L275 475 '
        'L360 550 '
        'L455 500 '
        'L535 555 '
        'L630 485 '
        'L715 550 '
        'L810 495 '
        'L900 555 '
        'L1000 490 '
        'L1090 550 '
        'L1190 480 '
        'L1280 550 '
        'L1370 495 '
        'L1400 520 '
        'L1400 560 Z" '
        'fill="url(#mountains)"/>'
    )

    return p


# ============================================================
# CONTRIBUTION GRID
# ============================================================

GRID_X = 190
GRID_Y = 265

CELL_W = 21
CELL_H = 26

WEEKS = 53
DAYS = 7


def parse_date(value):

    return datetime.strptime(
        value,
        "%Y-%m-%d"
    ).date()


# ============================================================
# THE IMPORTANT BLINKING DOT EFFECT
# ============================================================

def animated_dot(x, y, delay):

    return f"""
<circle
    cx="{x}"
    cy="{y}"
    r="1.25"
    fill="#789cff"
    opacity=".20">

    <animate
        attributeName="opacity"
        values=".15;.85;.15"
        dur="2.6s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

    <animate
        attributeName="r"
        values="1.10;2.05;1.10"
        dur="2.6s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</circle>
"""


# ============================================================
# CONTRIBUTION STARS
# ============================================================

def animated_star(
    x,
    y,
    count,
    delay
):

    elements = []

    # 1 contribution
    if count == 1:

        size = 4.2

        points = star_points(
            x,
            y,
            size,
            1.25,
            4
        )

        elements.append(
            f"""
<polygon
    points="{points}"
    fill="#9fc8ff">

    <animate
        attributeName="opacity"
        values=".45;1;.45"
        dur="2.8s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

    <animateTransform
        attributeName="transform"
        type="scale"
        values="1;1.25;1"
        dur="2.8s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"
        additive="sum"/>

</polygon>
"""
        )

    # 2–3 contributions
    elif count <= 3:

        size = 5.3

        elements.append(
            f"""
<path
    d="{diamond(x,y,size)}"
    fill="#8dbdff">

    <animate
        attributeName="opacity"
        values=".45;1;.45"
        dur="2.5s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</path>
"""
        )

    # 4–6 contributions
    elif count <= 6:

        size = 6.8

        points = star_points(
            x,
            y,
            size,
            2.1,
            6
        )

        elements.append(
            f"""
<polygon
    points="{points}"
    fill="#7eb4ff">

    <animate
        attributeName="opacity"
        values=".45;1;.45"
        dur="2.3s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</polygon>
"""
        )

        elements.append(
            f"""
<circle
    cx="{x}"
    cy="{y}"
    r="10"
    fill="#5e9cff"
    opacity=".06">

    <animate
        attributeName="opacity"
        values=".03;.30;.03"
        dur="2.3s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</circle>
"""
        )

    # 7–9 contributions
    elif count <= 9:

        size = 9

        points = star_points(
            x,
            y,
            size,
            2.5,
            8
        )

        elements.append(
            f"""
<polygon
    points="{points}"
    fill="#c2aaff">

    <animate
        attributeName="opacity"
        values=".50;1;.50"
        dur="2.1s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</polygon>
"""
        )

        elements.append(
            f"""
<circle
    cx="{x}"
    cy="{y}"
    r="15"
    fill="#8d6fff"
    opacity=".07">

    <animate
        attributeName="opacity"
        values=".03;.32;.03"
        dur="2.1s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</circle>
"""
        )

    # 10+ contributions
    else:

        size = min(
            13,
            9 + (count - 10) * .25
        )

        points = star_points(
            x,
            y,
            size,
            size * .25,
            4
        )

        elements.append(
            f"""
<polygon
    points="{points}"
    fill="#ffe2a1">

    <animate
        attributeName="opacity"
        values=".55;1;.55"
        dur="1.9s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</polygon>
"""
        )

        elements.append(
            f"""
<circle
    cx="{x}"
    cy="{y}"
    r="{size * 1.8}"
    fill="#ffc95b"
    opacity=".06">

    <animate
        attributeName="opacity"
        values=".03;.38;.03"
        dur="1.9s"
        begin="{delay:.2f}s"
        repeatCount="indefinite"/>

</circle>
"""
        )

    return elements


# ============================================================
# CONTRIBUTION CALENDAR
# ============================================================

def contribution_grid(contributions):

    p = []

    data = {
        item["date"]: item["count"]
        for item in contributions
    }

    dates = sorted(
        parse_date(item["date"])
        for item in contributions
    )

    if not dates:
        return p

    first = dates[0]

    start = first - timedelta(
        days=(first.weekday() + 1) % 7
    )

    # --------------------------------------------------------
    # Month labels
    # --------------------------------------------------------

    seen_months = set()

    for week in range(WEEKS):

        for day_index in range(DAYS):

            current = start + timedelta(
                days=week * 7 + day_index
            )

            if current.day <= 7:

                month = current.strftime("%b")

                if month not in seen_months:

                    seen_months.add(month)

                    x = (
                        GRID_X +
                        week * CELL_W
                    )

                    p.append(
                        f"""
<text
    x="{x}"
    y="{GRID_Y - 31}"
    text-anchor="middle"
    fill="#91a8db"
    font-size="13"
    font-family="Arial, sans-serif"
    opacity=".90">

    {month}

</text>
"""
                    )

    # --------------------------------------------------------
    # Weekday labels
    # --------------------------------------------------------

    labels = [
        ("Mon", 1),
        ("Tue", 2),
        ("Wed", 3),
        ("Thu", 4),
        ("Fri", 5),
        ("Sat", 6),
        ("Sun", 0),
    ]

    for label, row in labels:

        y = (
            GRID_Y +
            row * CELL_H +
            4
        )

        p.append(
            f"""
<text
    x="{GRID_X - 28}"
    y="{y}"
    text-anchor="end"
    fill="#8199cc"
    font-size="11"
    font-family="Arial, sans-serif"
    opacity=".88">

    {label}

</text>
"""
        )

    active = []

    # --------------------------------------------------------
    # Every calendar day
    # --------------------------------------------------------

    for week in range(WEEKS):

        for day_index in range(DAYS):

            current = start + timedelta(
                days=week * 7 + day_index
            )

            date_string = current.isoformat()

            x = (
                GRID_X +
                week * CELL_W
            )

            y = (
                GRID_Y +
                day_index * CELL_H
            )

            count = data.get(
                date_string,
                0
            )

            # ------------------------------------------------
            # EMPTY DAY
            # Noticeably twinkling dot
            # ------------------------------------------------

            if count == 0:

                delay = random.uniform(
                    0,
                    5.0
                )

                p.append(
                    animated_dot(
                        x,
                        y,
                        delay
                    )
                )

                continue

            # ------------------------------------------------
            # ACTIVE CONTRIBUTION
            # ------------------------------------------------

            active.append(
                (x, y, count)
            )

            delay = random.uniform(
                0,
                3.0
            )

            p.append(
                f"""
<g>

<title>
{esc(date_string)} — {count}
contribution{"s" if count != 1 else ""}
</title>
"""
            )

            p.extend(
                animated_star(
                    x,
                    y,
                    count,
                    delay
                )
            )

            p.append("</g>")

    # --------------------------------------------------------
    # Subtle constellation connections
    # --------------------------------------------------------

    for i in range(len(active)):

        x1, y1, c1 = active[i]

        for j in range(
            i + 1,
            len(active)
        ):

            x2, y2, c2 = active[j]

            dx = abs(x2 - x1)
            dy = abs(y2 - y1)

            if (
                dx <= CELL_W * 2.3
                and
                dy <= CELL_H * 1.8
            ):

                opacity = (
                    .10
                    if c1 < 4 and c2 < 4
                    else .17
                )

                p.append(
                    f"""
<line
    x1="{x1}"
    y1="{y1}"
    x2="{x2}"
    y2="{y2}"
    stroke="#7e9eff"
    stroke-width=".7"
    opacity="{opacity}"/>
"""
                )

    return p


# ============================================================
# BUILD SVG
# ============================================================

def build_svg(
    contributions,
    total
):

    p = []

    p.append(
        f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}"
    preserveAspectRatio="xMidYMid meet">

<defs>

<!-- SPACE -->

<linearGradient
    id="space"
    x1="0"
    y1="0"
    x2="0"
    y2="1">

    <stop
        offset="0%"
        stop-color="#020617"/>

    <stop
        offset="45%"
        stop-color="#061438"/>

    <stop
        offset="75%"
        stop-color="#0b1542"/>

    <stop
        offset="100%"
        stop-color="#08091f"/>

</linearGradient>


<!-- MILKY WAY -->

<linearGradient
    id="milky"
    x1="0"
    y1="0"
    x2="1"
    y2="0">

    <stop
        offset="0%"
        stop-color="#1c62ff"/>

    <stop
        offset="40%"
        stop-color="#674eff"/>

    <stop
        offset="70%"
        stop-color="#a46cff"/>

    <stop
        offset="100%"
        stop-color="#2861ff"/>

</linearGradient>


<linearGradient
    id="milky2"
    x1="0"
    y1="0"
    x2="1"
    y2="0">

    <stop
        offset="0%"
        stop-color="#4c8dff"/>

    <stop
        offset="50%"
        stop-color="#b18cff"/>

    <stop
        offset="100%"
        stop-color="#5b82ff"/>

</linearGradient>


<!-- SHOOTING STARS -->

<linearGradient
    id="shoot"
    x1="0"
    y1="0"
    x2="1"
    y2="0">

    <stop
        offset="0%"
        stop-color="#786cff"
        stop-opacity="0"/>

    <stop
        offset="75%"
        stop-color="#9f9cff"
        stop-opacity=".55"/>

    <stop
        offset="100%"
        stop-color="#ffffff"
        stop-opacity="1"/>

</linearGradient>


<!-- PLANET -->

<radialGradient
    id="planet"
    cx="32%"
    cy="28%">

    <stop
        offset="0%"
        stop-color="#9baaff"/>

    <stop
        offset="35%"
        stop-color="#465bd0"/>

    <stop
        offset="72%"
        stop-color="#151e67"/>

    <stop
        offset="100%"
        stop-color="#050921"/>

</radialGradient>


<radialGradient id="moon">

    <stop
        offset="0%"
        stop-color="#8d8fff"/>

    <stop
        offset="100%"
        stop-color="#24216e"/>

</radialGradient>


<linearGradient
    id="horizon"
    x1="0"
    y1="0"
    x2="0"
    y2="1">

    <stop
        offset="0%"
        stop-color="#173f9e"
        stop-opacity=".8"/>

    <stop
        offset="100%"
        stop-color="#040716"/>

</linearGradient>


<!-- CLOUD -->

<radialGradient
    id="cloud"
    cx="50%"
    cy="40%">

    <stop
        offset="0%"
        stop-color="#c4a9ff"/>

    <stop
        offset="45%"
        stop-color="#725ad2"/>

    <stop
        offset="100%"
        stop-color="#20205b"/>

</radialGradient>


<!-- FAR MOUNTAINS -->

<linearGradient
    id="farMountains"
    x1="0"
    y1="0"
    x2="0"
    y2="1">

    <stop
        offset="0%"
        stop-color="#263f88"/>

    <stop
        offset="100%"
        stop-color="#080d27"/>

</linearGradient>


<!-- MOUNTAINS -->

<linearGradient
    id="mountains"
    x1="0"
    y1="0"
    x2="0"
    y2="1">

    <stop
        offset="0%"
        stop-color="#101c4d"/>

    <stop
        offset="100%"
        stop-color="#02040f"/>

</linearGradient>


<!-- NEBULA FILTER -->

<filter
    id="nebula"
    x="-40%"
    y="-40%"
    width="180%"
    height="180%">

    <feGaussianBlur
        stdDeviation="55"/>

</filter>


<!-- MILKY WAY FILTER -->

<filter
    id="milkyBlur"
    x="-30%"
    y="-30%"
    width="160%"
    height="160%">

    <feGaussianBlur
        stdDeviation="24"/>

</filter>


<!-- CLOUD FILTER -->

<filter
    id="cloudBlur"
    x="-60%"
    y="-60%"
    width="220%"
    height="220%">

    <feGaussianBlur
        stdDeviation="9"/>

</filter>


<!-- GLOW -->

<filter
    id="glow"
    x="-100%"
    y="-100%"
    width="300%"
    height="300%">

    <feGaussianBlur
        stdDeviation="4"/>

</filter>

</defs>
"""
    )

    # Cosmic scene
    p.extend(
        cosmic_background()
    )

    p.extend(
        planets()
    )

    p.extend(
        shooting_stars()
    )

    # Real contribution data
    p.extend(
        contribution_grid(
            contributions
        )
    )

    # Clouds and mountains
    p.extend(
        clouds()
    )

    p.extend(
        mountains()
    )

    # --------------------------------------------------------
    # Bottom message
    # --------------------------------------------------------

    p.append(
        """
<text
    x="700"
    y="500"
    text-anchor="middle"
    fill="#b8c6ff"
    font-size="15"
    font-family="Arial, sans-serif"
    letter-spacing="4"
    opacity=".88">

    EVERY LITTLE CONTRIBUTION BECOMES A STAR

</text>
"""
    )

    p.append(
        """
<line
    x1="600"
    y1="520"
    x2="800"
    y2="520"
    stroke="#91a7ff"
    stroke-width="1"
    opacity=".42"/>
"""
    )

    p.append(
        f"""
<polygon
    points="{star_points(700,520,5,1.4,4)}"
    fill="#d4ddff"
    opacity=".9"/>
"""
    )

    p.append(
        f"""
<text
    x="700"
    y="545"
    text-anchor="middle"
    fill="#7187bb"
    font-size="11"
    font-family="Arial, sans-serif"
    opacity=".85">

    {total} contributions in the last year

</text>
"""
    )

    p.append("</svg>")

    return "\n".join(p)


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Fetching GitHub contribution data..."
    )

    contributions, total = (
        get_contributions()
    )

    print(
        f"Total contributions: {total}"
    )

    svg = build_svg(
        contributions,
        total
    )

    os.makedirs(
        os.path.dirname(
            OUTPUT_FILE
        ),
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg)

    print(
        f"Generated {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()