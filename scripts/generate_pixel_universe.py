import os
import json
import base64
import math
import urllib.request
import urllib.error
from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

GH_USER = os.environ.get("GH_USER", "MinalMaurya")
GH_TOKEN = os.environ.get("GH_TOKEN")

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

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
# CANVAS
# ============================================================

SVG_WIDTH = 2048
SVG_HEIGHT = 900


# ============================================================
# STAR FIELD POSITION
#
# IMPORTANT:
# The contribution constellation lives ONLY in the
# upper portion of the image.
# ============================================================

STAR_AREA_LEFT = 150
STAR_AREA_RIGHT = 1890

STAR_AREA_TOP = 135
STAR_AREA_BOTTOM = 450


# ============================================================
# CONTRIBUTION LAYOUT
# ============================================================

WEEKS = 53

CELL_W = (
    STAR_AREA_RIGHT - STAR_AREA_LEFT
) / WEEKS

CELL_H = (
    STAR_AREA_BOTTOM - STAR_AREA_TOP
) / 7


# ============================================================
# STAR COLORS
# ============================================================

STAR_BLUE = "#8db7ff"
STAR_CYAN = "#7ee7ff"
STAR_PURPLE = "#c9a7ff"
STAR_GOLD = "#ffd66b"

WHITE = "#ffffff"

LINE_COLOR = "#91a8ff"


# ============================================================
# XML HELPER
# ============================================================

def escape_xml(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ============================================================
# LOAD BACKGROUND
# ============================================================

def load_background():
    """
    Load the existing cosmic PNG and embed it
    directly inside the SVG.
    """

    if not os.path.exists(BACKGROUND_PATH):
        raise FileNotFoundError(
            f"Background image not found:\n"
            f"{BACKGROUND_PATH}"
        )

    with open(
        BACKGROUND_PATH,
        "rb"
    ) as file:

        return base64.b64encode(
            file.read()
        ).decode("ascii")


# ============================================================
# GITHUB WEEK NORMALIZATION
# ============================================================

def get_week_days(week):
    """
    GitHub GraphQL returns weeks in this form:

    {
        "contributionDays": [
            {
                "date": "2026-09-01",
                "contributionCount": 3
            }
        ]
    }

    This also accepts a plain list for safety.
    """

    if isinstance(week, list):
        return week

    if isinstance(week, dict):

        days = week.get(
            "contributionDays",
            []
        )

        if isinstance(days, list):
            return days

    return []


def normalize_weeks(weeks):
    """
    Convert GitHub's response into:

        [
            [day, day, day, ...],
            [day, day, day, ...],
            ...
        ]
    """

    normalized = []

    if not isinstance(weeks, list):
        raise TypeError(
            "Expected GitHub weeks to be a list, "
            f"got {type(weeks).__name__}"
        )

    for week in weeks:

        days = get_week_days(week)

        if days:
            normalized.append(days)

    return normalized


# ============================================================
# GITHUB CONTRIBUTIONS
# ============================================================

def get_contributions():

    if not GH_TOKEN:
        raise RuntimeError(
            "GH_TOKEN is not set.\n\n"
            "For GitHub Actions this is provided automatically.\n\n"
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

    payload = json.dumps(
        {
            "query": query,
            "variables": {
                "login": GH_USER
            }
        }
    ).encode("utf-8")

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

        with urllib.request.urlopen(
            request
        ) as response:

            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"GitHub API error {error.code}:\n"
            f"{body}"
        )

    except urllib.error.URLError as error:

        raise RuntimeError(
            f"Could not connect to GitHub:\n"
            f"{error}"
        )

    if "errors" in result:

        raise RuntimeError(
            "GitHub GraphQL error:\n"
            + json.dumps(
                result["errors"],
                indent=2
            )
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
            f"Could not retrieve contribution "
            f"calendar for {GH_USER}"
        )

    return calendar


# ============================================================
# STAR GEOMETRY
# ============================================================

def star_points(
    cx,
    cy,
    outer_radius,
    inner_radius,
    points
):

    coordinates = []

    total_points = points * 2

    for index in range(total_points):

        angle = (
            -math.pi / 2
            + index * math.pi / points
        )

        radius = (
            outer_radius
            if index % 2 == 0
            else inner_radius
        )

        x = (
            cx
            + math.cos(angle) * radius
        )

        y = (
            cy
            + math.sin(angle) * radius
        )

        coordinates.append(
            f"{x:.2f},{y:.2f}"
        )

    return " ".join(coordinates)


# ============================================================
# STAR STYLE
# ============================================================

def get_star_style(count):

    # 1 contribution
    if count == 1:

        return {
            "points": 4,
            "outer": 3.5,
            "inner": 1.1,
            "color": STAR_BLUE,
            "duration": 4.8
        }

    # 2 - 3 contributions
    if count <= 3:

        return {
            "points": 4,
            "outer": 4.5,
            "inner": 1.3,
            "color": STAR_CYAN,
            "duration": 4.3
        }

    # 4 - 6 contributions
    if count <= 6:

        return {
            "points": 6,
            "outer": 6.0,
            "inner": 1.9,
            "color": STAR_CYAN,
            "duration": 3.8
        }

    # 7 - 9 contributions
    if count <= 9:

        return {
            "points": 8,
            "outer": 8.0,
            "inner": 2.4,
            "color": STAR_PURPLE,
            "duration": 3.3
        }

    # 10+ contributions
    return {
        "points": 8,
        "outer": 11.0,
        "inner": 3.1,
        "color": STAR_GOLD,
        "duration": 2.8
    }


# ============================================================
# ANIMATION DELAY
# ============================================================

def animation_delay(
    index,
    multiplier=0.37
):

    return (
        f"{(index * multiplier) % 6:.2f}s"
    )


# ============================================================
# CONTRIBUTION STAR
# ============================================================

def make_contribution_star(
    cx,
    cy,
    count,
    index,
    contribution_date
):

    style = get_star_style(count)

    points = star_points(
        cx,
        cy,
        style["outer"],
        style["inner"],
        style["points"]
    )

    delay = animation_delay(
        index,
        0.53
    )

    title = escape_xml(
        f"{contribution_date} — "
        f"{count} contributions"
    )

    outer = style["outer"]

    return f"""
    <g>

        <!--
            Native SVG tooltip.
            Hovering over the star shows:
            date + contribution count.
        -->
        <title>{title}</title>

        <!-- Outer atmospheric glow -->
        <circle
            cx="{cx:.2f}"
            cy="{cy:.2f}"
            r="{outer * 2.0:.2f}"
            fill="{style["color"]}"
            opacity="0.12"
            filter="url(#softGlow)"
        >

            <animate
                attributeName="opacity"
                values="0.05;0.24;0.05"
                dur="{style["duration"]:.1f}s"
                begin="{delay}"
                repeatCount="indefinite"
            />

            <animate
                attributeName="r"
                values="
                    {outer * 1.35:.2f};
                    {outer * 2.10:.2f};
                    {outer * 1.35:.2f}
                "
                dur="{style["duration"]:.1f}s"
                begin="{delay}"
                repeatCount="indefinite"
            />

        </circle>


        <!-- Main star -->
        <polygon
            points="{points}"
            fill="{style["color"]}"
            stroke="{WHITE}"
            stroke-width="0.35"
            opacity="0.90"
        >

            <!-- Gentle twinkle -->
            <animate
                attributeName="opacity"
                values="0.58;1;0.58"
                dur="{style["duration"]:.1f}s"
                begin="{delay}"
                repeatCount="indefinite"
            />

        </polygon>


        <!-- Bright center -->
        <circle
            cx="{cx:.2f}"
            cy="{cy:.2f}"
            r="{max(0.7, outer * 0.16):.2f}"
            fill="{WHITE}"
            opacity="0.70"
        >

            <animate
                attributeName="opacity"
                values="0.35;1;0.35"
                dur="{style["duration"]:.1f}s"
                begin="{delay}"
                repeatCount="indefinite"
            />

        </circle>

    </g>
    """


# ============================================================
# CONSTELLATION LINE
# ============================================================

def make_constellation_line(
    x1,
    y1,
    x2,
    y2
):

    return f"""
    <line
        x1="{x1:.2f}"
        y1="{y1:.2f}"
        x2="{x2:.2f}"
        y2="{y2:.2f}"
        stroke="{LINE_COLOR}"
        stroke-width="0.45"
        opacity="0.08"
    />
    """


# ============================================================
# DAY POSITION
# ============================================================

def get_day_index(date_string):
    """
    Return Monday=0 ... Sunday=6.

    Using the actual date makes the star positions
    independent of the order returned by the API.
    """

    try:

        date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        )

        return date.weekday()

    except (
        ValueError,
        TypeError
    ):

        return None


# ============================================================
# BUILD SVG
# ============================================================

def generate_svg(calendar):

    background = load_background()

    raw_weeks = calendar.get(
        "weeks",
        []
    )

    # Normalize GitHub's dictionary structure.
    weeks = normalize_weeks(
        raw_weeks
    )

    svg_parts = []

    # ========================================================
    # SVG HEADER
    # ========================================================

    svg_parts.append(
        f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    width="{SVG_WIDTH}"
    height="{SVG_HEIGHT}"
    viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}"
>

    <defs>

        <!-- Soft star glow -->
        <filter
            id="softGlow"
            x="-100%"
            y="-100%"
            width="300%"
            height="300%"
        >

            <feGaussianBlur
                stdDeviation="4"
                result="blur"
            />

        </filter>

    </defs>
"""
    )

    # ========================================================
    # COSMIC BACKGROUND
    # ========================================================

    svg_parts.append(
        f"""
    <image
        x="0"
        y="0"
        width="{SVG_WIDTH}"
        height="{SVG_HEIGHT}"
        preserveAspectRatio="xMidYMid slice"
        href="data:image/png;base64,{background}"
    />
"""
    )

    # ========================================================
    # CONTRIBUTION STARS
    #
    # ONLY stars are drawn.
    # No grid.
    # No labels.
    # No empty cells.
    # No footer.
    # ========================================================

    active_stars = []

    contribution_index = 0

    for week_index, days in enumerate(
        weeks[:WEEKS]
    ):

        if not days:
            continue

        for day in days:

            if not isinstance(
                day,
                dict
            ):
                continue

            count = int(
                day.get(
                    "contributionCount",
                    0
                )
            )

            # Empty contribution days are invisible.
            if count <= 0:
                continue

            contribution_date = day.get(
                "date",
                ""
            )

            if not contribution_date:
                continue

            # ------------------------------------------------
            # Find the actual weekday.
            # Monday = 0
            # Sunday = 6
            # ------------------------------------------------

            day_index = get_day_index(
                contribution_date
            )

            if day_index is None:
                continue

            # ------------------------------------------------
            # X position
            # ------------------------------------------------

            cx = (
                STAR_AREA_LEFT
                + week_index * CELL_W
                + CELL_W / 2
            )

            # ------------------------------------------------
            # Y position
            #
            # The entire contribution constellation stays
            # in the TOP section of the image.
            # ------------------------------------------------

            cy = (
                STAR_AREA_TOP
                + day_index * CELL_H
                + CELL_H / 2
            )

            # ------------------------------------------------
            # Create star
            # ------------------------------------------------

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

    # ========================================================
    # SUBTLE CONSTELLATION CONNECTIONS
    # ========================================================

    for i, star_a in enumerate(
        active_stars
    ):

        x1, y1, count_a = star_a

        for j in range(
            i + 1,
            len(active_stars)
        ):

            x2, y2, count_b = (
                active_stars[j]
            )

            distance = math.sqrt(
                (x2 - x1) ** 2
                + (y2 - y1) ** 2
            )

            # Very subtle connections.
            if distance <= 48:

                svg_parts.append(
                    make_constellation_line(
                        x1,
                        y1,
                        x2,
                        y2
                    )
                )

    # ========================================================
    # CLOSE SVG
    # ========================================================

    svg_parts.append(
        "</svg>"
    )

    return "\n".join(
        svg_parts
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Generating Pixel Universe..."
    )

    print(
        f"GitHub user: {GH_USER}"
    )

    print(
        f"Background: {BACKGROUND_PATH}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    # --------------------------------------------------------
    # Get GitHub contribution data
    # --------------------------------------------------------

    calendar = get_contributions()

    # --------------------------------------------------------
    # Generate SVG
    # --------------------------------------------------------

    svg = generate_svg(
        calendar
    )

    # --------------------------------------------------------
    # Ensure output directory exists
    # --------------------------------------------------------

    os.makedirs(
        os.path.dirname(
            OUTPUT_PATH
        ),
        exist_ok=True
    )

    # --------------------------------------------------------
    # Write SVG
    # --------------------------------------------------------

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg)

    # --------------------------------------------------------
    # Success information
    # --------------------------------------------------------

    print()

    print(
        "Pixel Universe generated successfully."
    )

    print(
        "Total contributions:",
        calendar.get(
            "totalContributions",
            0
        )
    )

    print(
        f"SVG saved to: {OUTPUT_PATH}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()