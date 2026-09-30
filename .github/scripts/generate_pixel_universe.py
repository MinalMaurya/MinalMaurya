#!/usr/bin/env python3

import json
import math
import os
import random
import urllib.request
import urllib.error

TOKEN = os.environ["GH_TOKEN"]
USERNAME = os.environ.get("GH_USER", "MinalMaurya")

QUERY = '''
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
'''

payload = json.dumps({
    "query": QUERY,
    "variables": {
        "login": USERNAME
    }
}).encode()

request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "pixel-universe-generator"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(request) as response:
        data = json.load(response)

except urllib.error.HTTPError as exc:
    raise SystemExit(
        f"GitHub API request failed: HTTP {exc.code}"
    )

if data.get("errors"):
    raise SystemExit(
        json.dumps(data["errors"], indent=2)
    )

calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]

weeks = calendar["weeks"]

days = [
    day
    for week in weeks
    for day in week["contributionDays"]
]

# Keep approximately one year of activity
days = days[-371:]

maximum = max(
    (day["contributionCount"] for day in days),
    default=1
)

WIDTH = 1200
HEIGHT = 430

CENTER_X = 600
CENTER_Y = 220


def escape(value):
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def contribution_level(count):

    if count <= 0:
        return 0

    ratio = count / maximum

    if ratio < 0.25:
        return 1

    if ratio < 0.50:
        return 2

    if ratio < 0.75:
        return 3

    return 4


# ----------------------------------------
# Decorative stars
# ----------------------------------------

random_generator = random.Random(2609)

decorative_stars = []

for _ in range(90):

    x = random_generator.randint(
        25,
        WIDTH - 25
    )

    y = random_generator.randint(
        35,
        HEIGHT - 45
    )

    radius = random_generator.choice([
        1,
        1,
        1,
        1.5,
        2
    ])

    phase = random_generator.random()

    decorative_stars.append(
        (x, y, radius, phase)
    )


svg = []

svg.append(
f'''<svg
xmlns="http://www.w3.org/2000/svg"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}"
role="img"
aria-label="Minal Maurya's GitHub contribution universe">

<defs>

    <radialGradient id="background">

        <stop
            offset="0%"
            stop-color="#17132f"/>

        <stop
            offset="55%"
            stop-color="#0b0a1d"/>

        <stop
            offset="100%"
            stop-color="#05050f"/>

    </radialGradient>


    <radialGradient id="nebula">

        <stop
            offset="0%"
            stop-color="#d9c8ff"
            stop-opacity=".18"/>

        <stop
            offset="45%"
            stop-color="#b7a1ff"
            stop-opacity=".08"/>

        <stop
            offset="100%"
            stop-color="#8e7bff"
            stop-opacity="0"/>

    </radialGradient>


    <filter id="glow">

        <feGaussianBlur
            stdDeviation="2.5"
            result="blur"/>

        <feMerge>

            <feMergeNode in="blur"/>

            <feMergeNode in="SourceGraphic"/>

        </feMerge>

    </filter>


    <filter id="softGlow">

        <feGaussianBlur
            stdDeviation="10"/>

    </filter>


    <style>

        .twinkle {{

            transform-box: fill-box;

            transform-origin: center;

            animation:
                twinkle
                3.8s
                ease-in-out
                infinite;

        }}


        @keyframes twinkle {{

            0%, 100% {{

                opacity: .55;

                transform:
                    scale(.85);

            }}

            50% {{

                opacity: 1;

                transform:
                    scale(1.18);

            }}

        }}


        .caption {{

            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

            letter-spacing:
                1.5px;

        }}

    </style>

</defs>


<!-- Background -->

<rect
    width="100%"
    height="100%"
    rx="28"
    fill="url(#background)"/>


<!-- Soft galaxy haze -->

<ellipse
    cx="600"
    cy="220"
    rx="410"
    ry="125"
    fill="url(#nebula)"
    filter="url(#softGlow)"/>


<ellipse
    cx="600"
    cy="220"
    rx="300"
    ry="72"
    fill="none"
    stroke="#b9a5ff"
    stroke-opacity=".08"
    stroke-width="22"
    transform="rotate(-10 600 220)"/>

'''
)


# ----------------------------------------
# Decorative stars
# ----------------------------------------

for index, (x, y, radius, phase) in enumerate(
    decorative_stars
):

    delay = f"{phase * 4:.2f}s"

    svg.append(
        f'''
        <circle
            class="twinkle"
            cx="{x}"
            cy="{y}"
            r="{radius}"
            fill="#eee8ff"
            opacity=".65"
            style="animation-delay:{delay}"/>
        '''
    )


# ----------------------------------------
# Contribution universe
# ----------------------------------------

columns = len(weeks)

for column, week in enumerate(weeks):

    for row, day in enumerate(
        week["contributionDays"]
    ):

        count = day["contributionCount"]

        level = contribution_level(
            count
        )

        # Curved contribution calendar

        t = column / max(
            columns - 1,
            1
        )

        x = (
            145
            + column *
            (
                910 /
                max(columns - 1, 1)
            )
        )

        curve = (
            52 *
            math.sin(
                (t - 0.5) *
                math.pi
            )
        )

        y = (
            160
            + row * 25
            + curve
        )


        # Slight galaxy rotation

        dx = x - CENTER_X
        dy = y - CENTER_Y

        angle = math.radians(-5)

        rotated_x = (
            CENTER_X
            + dx * math.cos(angle)
            - dy * math.sin(angle)
        )

        rotated_y = (
            CENTER_Y
            + dx * math.sin(angle)
            + dy * math.cos(angle)
        )


        # No contribution

        if level == 0:

            svg.append(
                f'''
                <circle
                    cx="{rotated_x:.1f}"
                    cy="{rotated_y:.1f}"
                    r="1.1"
                    fill="#8f89ad"
                    opacity=".28"/>
                '''
            )

            continue


        radii = {
            1: 2.5,
            2: 3.4,
            3: 4.5,
            4: 5.8
        }

        opacities = {
            1: .58,
            2: .72,
            3: .86,
            4: 1.0
        }

        radius = radii[level]


        # Glow around stronger contribution days

        if level >= 3:

            svg.append(
                f'''
                <circle
                    cx="{rotated_x:.1f}"
                    cy="{rotated_y:.1f}"
                    r="{radius * 2.7:.1f}"
                    fill="#c9b7ff"
                    opacity=".10"
                    filter="url(#softGlow)"/>
                '''
            )


        delay = (
            column * 0.09
            + row * 0.17
        ) % 4.8


        svg.append(
            f'''
            <circle
                class="twinkle"
                cx="{rotated_x:.1f}"
                cy="{rotated_y:.1f}"
                r="{radius}"
                fill="#eee7ff"
                opacity="{opacities[level]}"
                filter="url(#glow)"
                style="animation-delay:{delay:.2f}s">

                <title>
                    {escape(day["date"])}
                    —
                    {count}
                    contribution
                    {"s" if count != 1 else ""}
                </title>

            </circle>
            '''
        )


# ----------------------------------------
# Shooting star
# ----------------------------------------

svg.append(
'''
<g opacity=".75">

    <path
        d="M875 92 L820 116"
        stroke="#e8ddff"
        stroke-width="2"
        stroke-linecap="round">

        <animate
            attributeName="opacity"
            values="0;.8;0"
            dur="7s"
            repeatCount="indefinite"/>

    </path>


    <circle
        cx="875"
        cy="92"
        r="2.6"
        fill="#fff"
        filter="url(#glow)">

        <animate
            attributeName="cx"
            values="875;805;875"
            dur="7s"
            repeatCount="indefinite"/>

        <animate
            attributeName="cy"
            values="92;122;92"
            dur="7s"
            repeatCount="indefinite"/>

        <animate
            attributeName="opacity"
            values="0;1;0"
            dur="7s"
            repeatCount="indefinite"/>

    </circle>

</g>
'''
)


# ----------------------------------------
# Caption
# ----------------------------------------

svg.append(
f'''
<text
    x="600"
    y="388"
    text-anchor="middle"
    fill="#dcd5f2"
    font-size="14"
    class="caption">

    EVERY LITTLE CONTRIBUTION BECOMES A STAR ✦

</text>


<text
    x="600"
    y="410"
    text-anchor="middle"
    fill="#8f89ad"
    font-size="10"
    class="caption">

    GitHub activity • {escape(USERNAME)}

</text>


</svg>
'''
)


# ----------------------------------------
# Save
# ----------------------------------------

os.makedirs(
    "assets",
    exist_ok=True
)

with open(
    "assets/pixel-universe.svg",
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "\n".join(svg)
    )


print(
    "Pixel Universe generated successfully!"
)

print(
    "Total contributions:",
    calendar["totalContributions"]
)
