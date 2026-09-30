import os
import json
import base64
import math
import urllib.request
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

# NEW COSMIC BACKGROUND
BACKGROUND_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "cosmic-background.png"
)

# GENERATED FINAL SVG
OUTPUT_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "pixel-universe.svg"
)


# ============================================================
# CANVAS
# ============================================================

SVG_WIDTH = 2048
SVG_HEIGHT = 1152


# ============================================================
# CONTRIBUTION GRID POSITION
# ============================================================

# The grid is placed over the open central area
# of the cosmic background.

GRID_X = 250
GRID_Y = 315

CELL_W = 28
CELL_H = 35

GRID_WEEKS = 53
GRID_DAYS = 7


# ============================================================
# LABELS
# ============================================================

MONTHS = [
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
    "Dec"
]

WEEKDAYS = [
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
    "Sun"
]


# ============================================================
# COLORS
# ============================================================

DOT_COLOR = "#8aa8ff"

STAR_BLUE = "#8db7ff"
STAR_CYAN = "#7ee7ff"
STAR_PURPLE = "#c9a7ff"
STAR_GOLD = "#ffd66b"

LABEL_COLOR = "#aebdff"

LINE_COLOR = "#91a8ff"


# ============================================================
# LOAD BACKGROUND IMAGE
# ============================================================

def load_background():

    if not os.path.exists(BACKGROUND_PATH):
        raise FileNotFoundError(
            "\nBackground image not found:\n"
            f"{BACKGROUND_PATH}\n\n"
            "Make sure this file exists:\n"
            "assets/cosmic-background.png\n"
        )

    print("Loading cosmic background...")

    with open(
        BACKGROUND_PATH,
        "rb"
    ) as file:

        encoded = base64.b64encode(
            file.read()
        ).decode("utf-8")

    return encoded


# ============================================================
# FETCH GITHUB CONTRIBUTION DATA
# ============================================================

def fetch_contributions():

    if not GH_TOKEN:

        raise RuntimeError(
            "\nGH_TOKEN is missing.\n\n"
            "GitHub Actions supplies GH_TOKEN automatically.\n"
            "For local testing, run:\n\n"
            'export GH_TOKEN="YOUR_GITHUB_TOKEN"\n'
        )

    print("Fetching GitHub contribution data...")

    query = """
    query($user:String!) {
      user(login:$user) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
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
                "user": GH_USER
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
        }
    )

    with urllib.request.urlopen(request) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

    if "errors" in data:

        raise RuntimeError(
            "GitHub GraphQL error:\n"
            + json.dumps(
                data["errors"],
                indent=2
            )
        )

    calendar = (
        data["data"]
        ["user"]
        ["contributionsCollection"]
        ["contributionCalendar"]
    )

    return calendar


# ============================================================
# STAR SHAPE
# ============================================================

def star_points(
    cx,
    cy,
    outer,
    inner,
    points
):

    result = []

    for i in range(points * 2):

        angle = (
            -math.pi / 2
            + i * math.pi / points
        )

        radius = (
            outer
            if i % 2 == 0
            else inner
        )

        x = (
            cx
            + math.cos(angle) * radius
        )

        y = (
            cy
            + math.sin(angle) * radius
        )

        result.append(
            f"{x:.2f},{y:.2f}"
        )

    return " ".join(result)


# ============================================================
# EMPTY CONTRIBUTION DAY
# ============================================================

def animated_dot(
    x,
    y,
    index
):

    delay = (
        index * 0.17
    ) % 5.5

    return f"""
    <circle
        cx="{x:.2f}"
        cy="{y:.2f}"
        r="2.0"
        fill="{DOT_COLOR}"
        opacity="0.22">

        <animate
            attributeName="opacity"
            values="0.16;0.82;0.16"
            dur="2.8s"
            begin="{delay:.2f}s"
            repeatCount="indefinite"/>

        <animate
            attributeName="r"
            values="1.6;2.7;1.6"
            dur="2.8s"
            begin="{delay:.2f}s"
            repeatCount="indefinite"/>

    </circle>
    """


# ============================================================
# CONTRIBUTION STAR
# ============================================================

def contribution_star(
    x,
    y,
    count,
    index
):

    # --------------------------------------------------------
    # 1 CONTRIBUTION
    # --------------------------------------------------------

    if count == 1:

        outer = 4.0
        inner = 1.8
        points = 4
        color = STAR_BLUE


    # --------------------------------------------------------
    # 2–3 CONTRIBUTIONS
    # --------------------------------------------------------

    elif count <= 3:

        outer = 5.0
        inner = 2.0
        points = 4
        color = STAR_CYAN


    # --------------------------------------------------------
    # 4–6 CONTRIBUTIONS
    # --------------------------------------------------------

    elif count <= 6:

        outer = 6.5
        inner = 2.7
        points = 6
        color = STAR_CYAN


    # --------------------------------------------------------
    # 7–9 CONTRIBUTIONS
    # --------------------------------------------------------

    elif count <= 9:

        outer = 8.0
        inner = 3.2
        points = 8
        color = STAR_PURPLE


    # --------------------------------------------------------
    # 10+ CONTRIBUTIONS
    # --------------------------------------------------------

    else:

        outer = min(
            13.0,
            8.5 + count * 0.35
        )

        inner = outer * 0.38
        points = 8
        color = STAR_GOLD


    delay = (
        index * 0.31
    ) % 4.8

    duration = (
        2.0
        + (index % 5) * 0.35
    )

    points_data = star_points(
        x,
        y,
        outer,
        inner,
        points
    )

    contribution_text = (
        "contribution"
        if count == 1
        else "contributions"
    )

    return f"""
    <g>

        <title>
            {count} {contribution_text}
        </title>


        <!-- Soft glow -->

        <circle
            cx="{x:.2f}"
            cy="{y:.2f}"
            r="{outer * 1.9:.2f}"
            fill="{color}"
            opacity="0.08">

            <animate
                attributeName="opacity"
                values="0.04;0.20;0.04"
                dur="{duration}s"
                begin="{delay:.2f}s"
                repeatCount="indefinite"/>

        </circle>


        <!-- Main star -->

        <polygon
            points="{points_data}"
            fill="{color}"
            opacity="0.92">

            <animate
                attributeName="opacity"
                values="0.70;1;0.70"
                dur="{duration}s"
                begin="{delay:.2f}s"
                repeatCount="indefinite"/>

            <animateTransform
                attributeName="transform"
                type="scale"
                values="0.82;1.08;0.82"
                dur="{duration}s"
                begin="{delay:.2f}s"
                repeatCount="indefinite"
                additive="sum"/>

        </polygon>


        <!-- Bright center -->

        <circle
            cx="{x:.2f}"
            cy="{y:.2f}"
            r="1.15"
            fill="#ffffff"
            opacity="0.95"/>

    </g>
    """


# ============================================================
# BUILD CONTRIBUTION GRID
# ============================================================

def build_contribution_grid(
    calendar
):

    weeks = calendar["weeks"]

    # GitHub normally provides 53 weeks.
    weeks = weeks[-GRID_WEEKS:]

    elements = []

    active_positions = []

    contribution_index = 0


    for week_index, week in enumerate(weeks):

        days = week[
            "contributionDays"
        ]

        for day in days:

            github_weekday = int(
                day["weekday"]
            )

            # GitHub:
            #
            # 0 = Sunday
            # 1 = Monday
            # ...
            # 6 = Saturday
            #
            # Display:
            #
            # Monday = row 0
            # ...
            # Sunday = row 6

            display_row = (
                (github_weekday - 1)
                % 7
            )


            x = (
                GRID_X
                + week_index * CELL_W
            )

            y = (
                GRID_Y
                + display_row * CELL_H
            )


            count = int(
                day["contributionCount"]
            )


            if count == 0:

                elements.append(
                    animated_dot(
                        x,
                        y,
                        contribution_index
                    )
                )

            else:

                elements.append(
                    contribution_star(
                        x,
                        y,
                        count,
                        contribution_index
                    )
                )

                active_positions.append(
                    (x, y)
                )


            contribution_index += 1


    return (
        elements,
        active_positions
    )


# ============================================================
# CONSTELLATION LINES
# ============================================================

def build_constellations(
    active_positions
):

    lines = []

    max_distance = 95


    for i, (
        x1,
        y1
    ) in enumerate(
        active_positions
    ):

        nearby = 0


        for j in range(
            i + 1,
            len(active_positions)
        ):

            x2, y2 = (
                active_positions[j]
            )


            dx = x2 - x1
            dy = y2 - y1


            distance = math.sqrt(
                dx * dx
                + dy * dy
            )


            if distance <= max_distance:

                lines.append(
                    f"""
                    <line
                        x1="{x1:.2f}"
                        y1="{y1:.2f}"
                        x2="{x2:.2f}"
                        y2="{y2:.2f}"
                        stroke="{LINE_COLOR}"
                        stroke-width="0.8"
                        opacity="0.12"/>
                    """
                )

                nearby += 1


                # Keep constellation
                # patterns subtle.

                if nearby >= 2:
                    break


    return lines


# ============================================================
# MONTH LABELS
# ============================================================

def build_month_labels(
    weeks
):

    labels = []

    previous_month = None


    for week_index, week in enumerate(
        weeks
    ):

        if not week[
            "contributionDays"
        ]:
            continue


        date_text = (
            week[
                "contributionDays"
            ][0]["date"]
        )


        date = datetime.strptime(
            date_text,
            "%Y-%m-%d"
        )


        month = date.strftime(
            "%b"
        )


        if month != previous_month:

            x = (
                GRID_X
                + week_index * CELL_W
            )


            labels.append(
                f"""
                <text
                    x="{x:.2f}"
                    y="{GRID_Y - 35}"
                    fill="{LABEL_COLOR}"
                    font-family="Arial, sans-serif"
                    font-size="15"
                    text-anchor="start"
                    opacity="0.92">
                    {month}
                </text>
                """
            )


            previous_month = month


    return labels


# ============================================================
# WEEKDAY LABELS
# ============================================================

def build_weekday_labels():

    labels = []


    for row, name in enumerate(
        WEEKDAYS
    ):

        y = (
            GRID_Y
            + row * CELL_H
            + 5
        )


        labels.append(
            f"""
            <text
                x="{GRID_X - 24}"
                y="{y:.2f}"
                fill="{LABEL_COLOR}"
                font-family="Arial, sans-serif"
                font-size="13"
                text-anchor="end"
                opacity="0.82">
                {name}
            </text>
            """
        )


    return labels


# ============================================================
# FOOTER
# ============================================================

def build_footer(
    total
):

    return f"""
    <g>

        <text
            x="1024"
            y="865"
            fill="#c5d2ff"
            font-family="Arial, sans-serif"
            font-size="18"
            letter-spacing="5"
            text-anchor="middle"
            opacity="0.90">

            EVERY LITTLE CONTRIBUTION BECOMES A STAR

        </text>


        <line
            x1="720"
            y1="892"
            x2="965"
            y2="892"
            stroke="#9fb5ff"
            stroke-width="1"
            opacity="0.45"/>


        <polygon
            points="1024,885 1028,892 1024,899 1020,892"
            fill="#ffffff"
            opacity="0.95"/>


        <line
            x1="1083"
            y1="892"
            x2="1328"
            y2="892"
            stroke="#9fb5ff"
            stroke-width="1"
            opacity="0.45"/>


        <text
            x="1024"
            y="927"
            fill="#9eaff0"
            font-family="Arial, sans-serif"
            font-size="14"
            text-anchor="middle"
            opacity="0.82">

            {total} contributions in the last year

        </text>

    </g>
    """


# ============================================================
# GENERATE FINAL SVG
# ============================================================

def generate():

    # --------------------------------------------------------
    # Load the PNG background
    # --------------------------------------------------------

    background = load_background()


    # --------------------------------------------------------
    # Get real GitHub contribution data
    # --------------------------------------------------------

    calendar = fetch_contributions()


    total = calendar[
        "totalContributions"
    ]


    print(
        f"GitHub contributions: {total}"
    )


    weeks = calendar[
        "weeks"
    ][-GRID_WEEKS:]


    # --------------------------------------------------------
    # Build contribution stars
    # --------------------------------------------------------

    (
        grid_elements,
        active_positions
    ) = build_contribution_grid(
        calendar
    )


    # --------------------------------------------------------
    # Build constellation lines
    # --------------------------------------------------------

    constellation_lines = (
        build_constellations(
            active_positions
        )
    )


    # --------------------------------------------------------
    # Build month labels
    # --------------------------------------------------------

    month_labels = (
        build_month_labels(
            weeks
        )
    )


    # --------------------------------------------------------
    # Build weekday labels
    # --------------------------------------------------------

    weekday_labels = (
        build_weekday_labels()
    )


    # ========================================================
    # FINAL SVG
    # ========================================================

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>

<svg
    xmlns="http://www.w3.org/2000/svg"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    width="{SVG_WIDTH}"
    height="{SVG_HEIGHT}"
    viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">


    <title>
        Minal Maurya GitHub Contribution Universe
    </title>


    <!-- ================================================== -->
    <!-- COSMIC BACKGROUND                                  -->
    <!-- ================================================== -->

    <image
        x="0"
        y="0"
        width="{SVG_WIDTH}"
        height="{SVG_HEIGHT}"
        preserveAspectRatio="xMidYMid slice"
        href="data:image/png;base64,{background}"/>


    <!-- ================================================== -->
    <!-- VERY SUBTLE BACKGROUND FOR GRID READABILITY        -->
    <!-- ================================================== -->

    <rect
        x="190"
        y="275"
        width="1670"
        height="485"
        rx="35"
        fill="#02081f"
        opacity="0.12"/>


    <!-- ================================================== -->
    <!-- MONTH LABELS                                      -->
    <!-- ================================================== -->

    {''.join(month_labels)}


    <!-- ================================================== -->
    <!-- WEEKDAY LABELS                                    -->
    <!-- ================================================== -->

    {''.join(weekday_labels)}


    <!-- ================================================== -->
    <!-- CONSTELLATION CONNECTIONS                         -->
    <!-- ================================================== -->

    {''.join(constellation_lines)}


    <!-- ================================================== -->
    <!-- CONTRIBUTION STARS + EMPTY DAY DOTS              -->
    <!-- ================================================== -->

    {''.join(grid_elements)}


    <!-- ================================================== -->
    <!-- FOOTER                                             -->
    <!-- ================================================== -->

    {build_footer(total)}


</svg>
"""


    # --------------------------------------------------------
    # Write output
    # --------------------------------------------------------

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(svg)


    print()
    print(
        "=========================================="
    )
    print(
        "Pixel Universe generated successfully!"
    )
    print(
        "=========================================="
    )
    print()

    print(
        f"Background: {BACKGROUND_PATH}"
    )

    print(
        f"Output: {OUTPUT_PATH}"
    )

    print(
        f"Total contributions: {total}"
    )

    print()


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    generate()