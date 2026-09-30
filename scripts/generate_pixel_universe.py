import os
import json
import base64
import math
import urllib.request
import urllib.error
from datetime import date, timedelta


# ============================================================
# CONFIGURATION
# ============================================================

GH_USER = os.environ.get("GH_USER", "MinalMaurya")
GH_TOKEN = os.environ.get("GH_TOKEN")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BACKGROUND_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "cosmic-background.png"
)

OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "pixel-universe.svg"
)


# ============================================================
# WIDE RECTANGULAR CANVAS
# ============================================================

SVG_WIDTH = 2048
SVG_HEIGHT = 900


# ============================================================
# CONTRIBUTION GRID
# ============================================================

GRID_X = 270
GRID_Y = 245

CELL_W = 28
CELL_H = 35

WEEKS = 53


# ============================================================
# COLORS
# ============================================================

DOT_COLOR = "#8aa8ff"

STAR_BLUE = "#8db7ff"
STAR_CYAN = "#7ee7ff"
STAR_PURPLE = "#c9a7ff"
STAR_GOLD = "#ffd66b"

LABEL_COLOR = "#b8c5ff"
LINE_COLOR = "#91a8ff"

WHITE = "#ffffff"


# ============================================================
# HELPERS
# ============================================================

def escape_xml(value):
    """Escape text so it is safe inside SVG/XML."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def load_background():
    """Load the existing PNG and embed it directly into the SVG."""
    if not os.path.exists(BACKGROUND_PATH):
        raise FileNotFoundError(
            f"Background image not found:\n{BACKGROUND_PATH}"
        )

    with open(BACKGROUND_PATH, "rb") as file:
        encoded = base64.b64encode(file.read()).decode("ascii")

    return encoded


# ============================================================
# GITHUB CONTRIBUTIONS
# ============================================================

def get_contributions():
    """
    Fetch the user's GitHub contribution calendar.

    GitHub Actions automatically provides GH_TOKEN.
    For local testing, set GH_TOKEN manually.
    """

    if not GH_TOKEN:
        raise RuntimeError(
            "GH_TOKEN is not set.\n"
            "GitHub Actions provides this automatically.\n"
            "For local testing use:\n"
            'export GH_TOKEN="YOUR_TOKEN_HERE"'
        )

    query = """
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

    payload = json.dumps({
        "query": query,
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
            "User-Agent": "MinalMaurya-Pixel-Universe"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:
            result = json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API error {error.code}:\n{body}"
        )

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to GitHub:\n{error}"
        )

    if "errors" in result:
        raise RuntimeError(
            "GitHub GraphQL error:\n"
            + json.dumps(result["errors"], indent=2)
        )

    calendar = (
        result
        .get("data", {})
        .get("user", {})
        .get("contributionsCollection", {})
        .get("contributionCalendar", {})
    )

    if not calendar:
        raise RuntimeError(
            f"Could not retrieve contribution calendar for {GH_USER}"
        )

    return calendar


# ============================================================
# STAR GEOMETRY
# ============================================================

def star_points(cx, cy, outer_radius, inner_radius, points):
    """
    Generate a star polygon.

    points = 4  -> small sparkle
    points = 6  -> six-point star
    points = 8  -> eight-point star
    """

    coordinates = []

    total_points = points * 2

    for index in range(total_points):
        angle = -math.pi / 2 + (
            index * math.pi / points
        )

        if index % 2 == 0:
            radius = outer_radius
        else:
            radius = inner_radius

        x = cx + math.cos(angle) * radius
        y = cy + math.sin(angle) * radius

        coordinates.append(
            f"{x:.2f},{y:.2f}"
        )

    return " ".join(coordinates)


# ============================================================
# CONTRIBUTION STAR STYLE
# ============================================================

def get_star_style(count):
    """
    Convert contribution count into a visual star.

    1       -> small blue sparkle
    2–3     -> cyan diamond
    4–6     -> six-point star
    7–9     -> eight-point purple star
    10+     -> large gold star
    """

    if count <= 0:
        return {
            "points": 4,
            "outer": 3.2,
            "inner": 1.1,
            "color": DOT_COLOR,
            "glow": 0.30,
            "duration": 4.5
        }

    if count == 1:
        return {
            "points": 4,
            "outer": 4.5,
            "inner": 1.5,
            "color": STAR_BLUE,
            "glow": 0.45,
            "duration": 4.2
        }

    if count <= 3:
        return {
            "points": 4,
            "outer": 5.5,
            "inner": 1.8,
            "color": STAR_CYAN,
            "glow": 0.55,
            "duration": 3.8
        }

    if count <= 6:
        return {
            "points": 6,
            "outer": 7.0,
            "inner": 2.4,
            "color": STAR_CYAN,
            "glow": 0.65,
            "duration": 3.4
        }

    if count <= 9:
        return {
            "points": 8,
            "outer": 8.5,
            "inner": 2.8,
            "color": STAR_PURPLE,
            "glow": 0.72,
            "duration": 3.0
        }

    return {
        "points": 8,
        "outer": 11.0,
        "inner": 3.4,
        "color": STAR_GOLD,
        "glow": 0.90,
        "duration": 2.7
    }


# ============================================================
# ANIMATION HELPERS
# ============================================================

def animation_delay(index, multiplier=0.37):
    """
    Generate deterministic asynchronous animation delays.

    No randomness is used, so every GitHub Action produces
    stable SVG output.
    """

    return f"{(index * multiplier) % 6:.2f}s"


# ============================================================
# EMPTY DAY
# ============================================================

def make_empty_day(cx, cy, index):
    """
    Empty contribution days become tiny softly twinkling stars/dots.
    """

    delay = animation_delay(index, 0.41)

    return f"""
    <circle
        cx="{cx:.2f}"
        cy="{cy:.2f}"
        r="1.7"
        fill="{DOT_COLOR}"
        opacity="0.20">

        <animate
            attributeName="opacity"
            values="0.16;0.72;0.16"
            dur="4.8s"
            begin="{delay}"
            repeatCount="indefinite" />

        <animate
            attributeName="r"
            values="1.5;2.4;1.5"
            dur="4.8s"
            begin="{delay}"
            repeatCount="indefinite" />

    </circle>
    """


# ============================================================
# CONTRIBUTION STAR
# ============================================================

def make_contribution_star(cx, cy, count, index, contribution_date):
    """
    Create a contribution star with:
    - different shape based on contribution count
    - glow
    - gentle pulse
    - accessible title
    """

    style = get_star_style(count)

    points = star_points(
        cx,
        cy,
        style["outer"],
        style["inner"],
        style["points"]
    )

    delay = animation_delay(index, 0.53)

    title = escape_xml(
        f"{contribution_date} — {count} contributions"
    )

    return f"""
    <g>

        <title>{title}</title>

        <circle
            cx="{cx:.2f}"
            cy="{cy:.2f}"
            r="{style["outer"] * 1.55:.2f}"
            fill="{style["color"]}"
            opacity="{style["glow"]:.2f}"
            filter="url(#softGlow)">

            <animate
                attributeName="opacity"
                values="0.12;0.34;0.12"
                dur="{style["duration"] + 1.0:.1f}s"
                begin="{delay}"
                repeatCount="indefinite" />

            <animate
                attributeName="r"
                values="{style["outer"] * 1.35:.2f};{style["outer"] * 1.75:.2f};{style["outer"] * 1.35:.2f}"
                dur="{style["duration"] + 1.0:.1f}s"
                begin="{delay}"
                repeatCount="indefinite" />

        </circle>


        <polygon
            points="{points}"
            fill="{style["color"]}"
            stroke="{WHITE}"
            stroke-width="0.35"
            opacity="0.95">

            <animate
                attributeName="opacity"
                values="0.72;1;0.72"
                dur="{style["duration"]:.1f}s"
                begin="{delay}"
                repeatCount="indefinite" />

            <animateTransform
                attributeName="transform"
                type="scale"
                values="0.92;1.08;0.92"
                dur="{style["duration"]:.1f}s"
                begin="{delay}"
                repeatCount="indefinite" />

        </polygon>

    </g>
    """


# ============================================================
# CONSTELLATION LINE
# ============================================================

def make_constellation_line(x1, y1, x2, y2):
    """
    Subtle line connecting nearby contribution stars.
    """

    return f"""
    <line
        x1="{x1:.2f}"
        y1="{y1:.2f}"
        x2="{x2:.2f}"
        y2="{y2:.2f}"
        stroke="{LINE_COLOR}"
        stroke-width="0.65"
        opacity="0.13" />
    """


# ============================================================
# MONTH LABELS
# ============================================================

def get_month_positions(weeks):
    """
    Find approximate x positions for Jan–Dec labels.
    """

    positions = []

    previous_month = None

    for week_index, week in enumerate(weeks):
        if not week:
            continue

        first_date = week[0].get("date", "")
        if not first_date:
            continue

        try:
            current_month = int(first_date[5:7])
        except (ValueError, IndexError):
            continue

        if current_month != previous_month:
            positions.append(
                (week_index, current_month)
            )
            previous_month = current_month

    return positions


# ============================================================
# BUILD SVG
# ============================================================

def generate_svg(calendar):
    background = load_background()

    weeks = calendar.get("weeks", [])
    total_contributions = calendar.get(
        "totalContributions",
        0
    )

    svg_parts = []

    # --------------------------------------------------------
    # SVG HEADER
    # --------------------------------------------------------

    svg_parts.append(
        f"""<svg
xmlns="http://www.w3.org/2000/svg"
xmlns:xlink="http://www.w3.org/1999/xlink"
width="{SVG_WIDTH}"
height="{SVG_HEIGHT}"
viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">

<defs>

    <filter
        id="softGlow"
        x="-100%"
        y="-100%"
        width="300%"
        height="300%">

        <feGaussianBlur
            stdDeviation="4"
            result="blur" />

    </filter>

</defs>
"""
    )

    # --------------------------------------------------------
    # EXISTING COSMIC BACKGROUND
    # --------------------------------------------------------

    svg_parts.append(
        f"""
<image
    x="0"
    y="0"
    width="{SVG_WIDTH}"
    height="{SVG_HEIGHT}"
    preserveAspectRatio="xMidYMid slice"
    href="data:image/png;base64,{background}" />
"""
    )

    # --------------------------------------------------------
    # VERY SUBTLE GRID BACKPLATE
    # --------------------------------------------------------
    # This is intentionally transparent so the background
    # remains visible.

    grid_width = WEEKS * CELL_W + 20
    grid_height = 7 * CELL_H + 20

    svg_parts.append(
        f"""
<rect
    x="{GRID_X - 10}"
    y="{GRID_Y - 10}"
    width="{grid_width}"
    height="{grid_height}"
    rx="12"
    fill="#07112d"
    opacity="0.12" />
"""
    )

    # --------------------------------------------------------
    # WEEKDAY LABELS
    # --------------------------------------------------------

    weekdays = [
        ("Mon", 0),
        ("Tue", 1),
        ("Wed", 2),
        ("Thu", 3),
        ("Fri", 4),
        ("Sat", 5),
        ("Sun", 6),
    ]

    for label, row in weekdays:

        y = (
            GRID_Y
            + row * CELL_H
            + CELL_H * 0.65
        )

        svg_parts.append(
            f"""
<text
    x="{GRID_X - 28}"
    y="{y:.2f}"
    text-anchor="end"
    font-family="Arial, Helvetica, sans-serif"
    font-size="11"
    fill="{LABEL_COLOR}"
    opacity="0.82">
    {label}
</text>
"""
        )

    # --------------------------------------------------------
    # MONTH LABELS
    # --------------------------------------------------------

    month_names = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    month_positions = get_month_positions(weeks)

    for week_index, month_number in month_positions:

        if not 1 <= month_number <= 12:
            continue

        x = (
            GRID_X
            + week_index * CELL_W
        )

        svg_parts.append(
            f"""
<text
    x="{x:.2f}"
    y="{GRID_Y - 24}"
    text-anchor="start"
    font-family="Arial, Helvetica, sans-serif"
    font-size="12"
    font-weight="500"
    fill="{LABEL_COLOR}"
    opacity="0.88">
    {month_names[month_number - 1]}
</text>
"""
        )

    # --------------------------------------------------------
    # COLLECT ACTIVE STARS
    # --------------------------------------------------------

    active_stars = []

    contribution_index = 0

    # GitHub normally returns 52/53 weeks.
    # We render up to WEEKS columns.
    for week_index, week in enumerate(weeks[:WEEKS]):

        for day_index, day in enumerate(week):

            count = int(
                day.get("contributionCount", 0)
            )

            contribution_date = day.get(
                "date",
                ""
            )

            cx = (
                GRID_X
                + week_index * CELL_W
                + CELL_W / 2
            )

            cy = (
                GRID_Y
                + day_index * CELL_H
                + CELL_H / 2
            )

            if count <= 0:

                svg_parts.append(
                    make_empty_day(
                        cx,
                        cy,
                        contribution_index
                    )
                )

            else:

                svg_parts.append(
                    make_contribution_star(
                        cx,
                        cy,
                        count,
                        contribution_index,
                        contribution_date
                    )
                )

                active_stars.append(
                    (
                        cx,
                        cy,
                        count
                    )
                )

            contribution_index += 1

    # --------------------------------------------------------
    # CONSTELLATION CONNECTIONS
    # --------------------------------------------------------
    # Only connect nearby actual contribution stars.
    # No decorative orbital lines.

    for i, star_a in enumerate(active_stars):

        x1, y1, count_a = star_a

        for j in range(i + 1, len(active_stars)):

            x2, y2, count_b = active_stars[j]

            distance = math.sqrt(
                (x2 - x1) ** 2
                + (y2 - y1) ** 2
            )

            # Only nearby stars.
            if distance <= 48:

                svg_parts.append(
                    make_constellation_line(
                        x1,
                        y1,
                        x2,
                        y2
                    )
                )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    footer_y = SVG_HEIGHT - 42

    svg_parts.append(
        f"""
<text
    x="{SVG_WIDTH / 2:.2f}"
    y="{footer_y}"
    text-anchor="middle"
    font-family="Arial, Helvetica, sans-serif"
    font-size="14"
    font-weight="600"
    letter-spacing="3"
    fill="{WHITE}"
    opacity="0.88">

    EVERY LITTLE CONTRIBUTION BECOMES A STAR

</text>

<text
    x="{SVG_WIDTH / 2:.2f}"
    y="{footer_y + 24}"
    text-anchor="middle"
    font-family="Arial, Helvetica, sans-serif"
    font-size="10"
    letter-spacing="1"
    fill="{LABEL_COLOR}"
    opacity="0.72">

    {total_contributions} contributions in the last year

</text>
"""
    )

    # --------------------------------------------------------
    # CLOSE SVG
    # --------------------------------------------------------

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)


# ============================================================
# MAIN
# ============================================================

def main():

    print("Generating Pixel Universe...")
    print(f"GitHub user: {GH_USER}")
    print(f"Background: {BACKGROUND_PATH}")
    print(f"Output: {OUTPUT_PATH}")

    calendar = get_contributions()

    svg = generate_svg(calendar)

    os.makedirs(
        os.path.dirname(OUTPUT_PATH),
        exist_ok=True
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg)

    print()
    print("Pixel Universe generated successfully.")
    print(
        f"Total contributions: "
        f"{calendar.get('totalContributions', 0)}"
    )
    print(
        f"SVG saved to: {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()