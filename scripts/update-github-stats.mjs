import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const username = process.env.GH_USER;
const token = process.env.GH_TOKEN;
const timeZone = process.env.STATS_TIMEZONE || "Asia/Kolkata";

if (!username || !token) {
  throw new Error("GH_USER and GH_TOKEN environment variables must be set.");
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

async function githubGraphql(query, variables = {}) {
  const response = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "github-profile-stats-updater",
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    throw new Error(`GitHub GraphQL request failed with HTTP ${response.status}.`);
  }

  const result = await response.json();
  if (result.errors?.length) {
    throw new Error(
      `GitHub GraphQL request failed: ${result.errors.map((error) => error.message).join("; ")}`,
    );
  }

  return result.data;
}

function getDatePartsInTimeZone(date, tz) {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  const parts = Object.fromEntries(
    formatter.formatToParts(date).map((part) => [part.type, part.value]),
  );
  return {
    year: Number(parts.year),
    month: Number(parts.month),
    day: Number(parts.day),
    isoDate: `${parts.year}-${parts.month}-${parts.day}`,
  };
}

function parseIsoDate(isoDate) {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

function addDays(isoDate, deltaDays) {
  const date = parseIsoDate(isoDate);
  date.setUTCDate(date.getUTCDate() + deltaDays);
  return date.toISOString().slice(0, 10);
}

const MONTHS_SHORT = [
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
];

const MONTHS_LONG = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function formatCalendarDate(isoDate, { includeYear = true, longMonth = false } = {}) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const monthName = (longMonth ? MONTHS_LONG : MONTHS_SHORT)[month - 1];
  return includeYear ? `${monthName} ${day}, ${year}` : `${monthName} ${day}`;
}

function formatStreakDateRange(streak, currentYear, todayIsoDate) {
  if (!streak || streak.count === 0 || !streak.start || !streak.end) {
    return formatCalendarDate(todayIsoDate, { includeYear: false });
  }
  const startYear = Number(streak.start.slice(0, 4));
  const endYear = Number(streak.end.slice(0, 4));
  if (streak.start === streak.end) {
    return formatCalendarDate(streak.start, { includeYear: startYear !== currentYear });
  }
  const startLabel = formatCalendarDate(streak.start, { includeYear: startYear !== currentYear });
  const endLabel = formatCalendarDate(streak.end, { includeYear: endYear !== currentYear });
  return `${startLabel} - ${endLabel}`;
}

/**
 * Calculates Current Streak and Longest Streak from a chronological list of
 * daily contribution entries ({ date: "YYYY-MM-DD", contributionCount: number })
 * using consistent streak rules:
 * 1. Only calendar days on or before `todayIsoDate` are evaluated.
 * 2. A day qualifies for a streak iff `contributionCount > 0`.
 * 3. Consecutive qualifying calendar days form a streak segment.
 * 4. Longest Streak is the segment with the maximum day count.
 * 5. Current Streak is the active segment ending on `todayIsoDate` (if today has
 *    contributions) or `yesterdayIsoDate` (if today has 0 contributions so far);
 *    otherwise Current Streak is 0.
 */
function calculateStreaks(contributionDays, todayIsoDate) {
  const validDays = contributionDays
    .filter((day) => day.date <= todayIsoDate)
    .sort((a, b) => a.date.localeCompare(b.date));

  const segments = [];
  let activeSegment = null;

  for (const day of validDays) {
    if (day.contributionCount > 0) {
      if (activeSegment && addDays(activeSegment.end, 1) === day.date) {
        activeSegment.end = day.date;
        activeSegment.count += 1;
      } else {
        activeSegment = { start: day.date, end: day.date, count: 1 };
        segments.push(activeSegment);
      }
    } else {
      activeSegment = null;
    }
  }

  let longestStreak = { count: 0, start: todayIsoDate, end: todayIsoDate };
  for (const segment of segments) {
    if (segment.count > longestStreak.count) {
      longestStreak = { ...segment };
    }
  }

  const yesterdayIsoDate = addDays(todayIsoDate, -1);
  const lastSegment = segments[segments.length - 1];
  const currentStreak =
    lastSegment && (lastSegment.end === todayIsoDate || lastSegment.end === yesterdayIsoDate)
      ? { ...lastSegment }
      : { count: 0, start: todayIsoDate, end: todayIsoDate };

  return { currentStreak, longestStreak };
}

async function fetchTotalStars(login) {
  let totalStars = 0;
  let after = null;

  const repoQuery = `query($login: String!, $after: String) {
    user(login: $login) {
      repositories(ownerAffiliations: OWNER, first: 100, after: $after) {
        nodes {
          stargazerCount
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }`;

  for (;;) {
    const data = await githubGraphql(repoQuery, { login, after });
    const repositories = data.user?.repositories;
    if (!repositories) {
      throw new Error(`Unable to read repositories for ${login}.`);
    }
    for (const repo of repositories.nodes) {
      totalStars += repo.stargazerCount;
    }
    if (!repositories.pageInfo.hasNextPage) {
      break;
    }
    after = repositories.pageInfo.endCursor;
  }

  return totalStars;
}

const profileQuery = `query($login: String!) {
  user(login: $login) {
    name
    login
    createdAt
    pullRequests(first: 1) {
      totalCount
    }
    issues(first: 1) {
      totalCount
    }
  }
}`;

const profileData = await githubGraphql(profileQuery, { login: username });
if (!profileData.user) {
  throw new Error(`GitHub user ${username} was not found.`);
}

const displayName = profileData.user.name || profileData.user.login;
const createdAt = new Date(profileData.user.createdAt);
const createdAtIsoDate = createdAt.toISOString().slice(0, 10);
const createdAtShortLabel = formatCalendarDate(createdAtIsoDate, {
  includeYear: true,
  longMonth: false,
});
const createdAtLongLabel = formatCalendarDate(createdAtIsoDate, {
  includeYear: true,
  longMonth: true,
});

const now = new Date();
const { year: currentYear, isoDate: todayIsoDate } = getDatePartsInTimeZone(now, timeZone);

const contributionQuery = `query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
      repositoriesContributedTo(first: 1) {
        totalCount
      }
    }
  }
}`;

let lifetimeContributions = 0;
const currentYearDaysMap = new Map();
const currentYearStartIsoDate = `${currentYear}-01-01`;

for (let year = createdAt.getUTCFullYear(); year <= currentYear; year += 1) {
  const from =
    year === createdAt.getUTCFullYear() ? createdAt : new Date(Date.UTC(year, 0, 1, 0, 0, 0));
  const to =
    year === currentYear ? now : new Date(Date.UTC(year, 11, 31, 23, 59, 59, 999));

  const data = await githubGraphql(contributionQuery, {
    login: username,
    from: from.toISOString(),
    to: to.toISOString(),
  });

  const calendar = data.user?.contributionsCollection?.contributionCalendar;
  if (!calendar) {
    throw new Error(`GitHub user ${username} was not found while reading contributions.`);
  }

  lifetimeContributions += calendar.totalContributions;

  if (year === currentYear) {
    for (const week of calendar.weeks) {
      for (const day of week.contributionDays) {
        if (day.date >= currentYearStartIsoDate && day.date <= todayIsoDate) {
          currentYearDaysMap.set(day.date, {
            date: day.date,
            contributionCount: day.contributionCount,
          });
        }
      }
    }
  }
}

const currentYearDays = Array.from(currentYearDaysMap.values()).sort((a, b) =>
  a.date.localeCompare(b.date),
);
const currentYearContributions = currentYearDays.reduce(
  (sum, day) => sum + day.contributionCount,
  0,
);
const { currentStreak, longestStreak } = calculateStreaks(currentYearDays, todayIsoDate);

const lastYearStart = new Date(now);
lastYearStart.setUTCFullYear(lastYearStart.getUTCFullYear() - 1);
const lastYearData = await githubGraphql(contributionQuery, {
  login: username,
  from: lastYearStart.toISOString(),
  to: now.toISOString(),
});

if (!lastYearData.user) {
  throw new Error(`GitHub user ${username} was not found while reading last-year contributions.`);
}

const contributedToLastYear =
  lastYearData.user.contributionsCollection.repositoriesContributedTo.totalCount;
const totalStars = await fetchTotalStars(username);
const totalPullRequests = profileData.user.pullRequests.totalCount;
const totalIssues = profileData.user.issues.totalCount;

function buildGitHubStatsSvg() {
  const metrics = [
    [`Total Contributions (${createdAtShortLabel}–Present)`, lifetimeContributions],
    ["Total Stars Earned", totalStars],
    ["Total PRs", totalPullRequests],
    ["Total Issues", totalIssues],
    ["Contributed to (last year)", contributedToLastYear],
  ];

  const rows = metrics
    .map(([label, value], index) => {
      const y = 89 + index * 32;
      return `  <text x="28" y="${y}" class="label">${escapeXml(label)}:</text>\n  <text x="425" y="${y}" class="value">${escapeXml(value)}</text>`;
    })
    .join("\n");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="580" height="258" viewBox="0 0 580 258" role="img" aria-labelledby="title desc">
  <title id="title">${escapeXml(displayName)}'s GitHub Stats</title>
  <desc id="desc">Live GitHub statistics. Contributions are counted since ${escapeXml(createdAtLongLabel)}.</desc>
  <style>
    .title { font: 700 20px 'Segoe UI', Ubuntu, sans-serif; fill: #5B8DEF; }
    .label { font: 600 15px 'Segoe UI', Ubuntu, sans-serif; fill: #6B5B73; }
    .value { font: 700 15px 'Segoe UI', Ubuntu, sans-serif; fill: #E889B9; }
  </style>
  <rect x="1" y="1" width="578" height="256" rx="8" fill="#FDF7FB" stroke="#F3DDEB"/>
  <text x="28" y="43" class="title">${escapeXml(displayName)}'s GitHub Stats</text>
${rows}
</svg>
`;
}

function buildStreakStatsSvg() {
  const totalRangeLabel = `Jan 1, ${currentYear} - Present`;
  const currentStreakRangeLabel = formatStreakDateRange(currentStreak, currentYear, todayIsoDate);
  const longestStreakRangeLabel = formatStreakDateRange(longestStreak, currentYear, todayIsoDate);

  return `<svg xmlns="http://www.w3.org/2000/svg" style="isolation: isolate" viewBox="0 0 495 195" width="495px" height="195px" direction="ltr" role="img" aria-labelledby="streak-title streak-desc">
  <title id="streak-title">${escapeXml(displayName)}'s ${escapeXml(currentYear)} Contribution and Streak Stats</title>
  <desc id="streak-desc">Total contributions in ${escapeXml(currentYear)}: ${escapeXml(currentYearContributions)} (${escapeXml(totalRangeLabel)}). Current streak: ${escapeXml(currentStreak.count)} days (${escapeXml(currentStreakRangeLabel)}). Longest streak: ${escapeXml(longestStreak.count)} days (${escapeXml(longestStreakRangeLabel)}).</desc>
  <style>
    @keyframes currstreak {
      0% { font-size: 3px; opacity: 0.2; }
      80% { font-size: 34px; opacity: 1; }
      100% { font-size: 28px; opacity: 1; }
    }
    @keyframes fadein {
      0% { opacity: 0; }
      100% { opacity: 1; }
    }
  </style>
  <defs>
    <clipPath id="outer_rectangle">
      <rect width="495" height="195" rx="4.5"/>
    </clipPath>
    <mask id="mask_out_ring_behind_fire">
      <rect width="495" height="195" fill="white"/>
      <ellipse id="mask-ellipse" cx="247.5" cy="32" rx="13" ry="18" fill="black"/>
    </mask>
  </defs>
  <g clip-path="url(#outer_rectangle)">
    <g style="isolation: isolate">
      <rect stroke="#000000" stroke-opacity="0" fill="#fdf7fb" rx="4.5" x="0.5" y="0.5" width="494" height="194"/>
    </g>
    <g style="isolation: isolate">
      <line x1="165" y1="28" x2="165" y2="170" vector-effect="non-scaling-stroke" stroke-width="1" stroke="#f3ddeb" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="3"/>
      <line x1="330" y1="28" x2="330" y2="170" vector-effect="non-scaling-stroke" stroke-width="1" stroke="#f3ddeb" stroke-linejoin="miter" stroke-linecap="square" stroke-miterlimit="3"/>
    </g>
    <g style="isolation: isolate">
      <!-- Total Contributions big number -->
      <g transform="translate(82.5, 48)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#5b8def" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="700" font-size="28px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s">
          ${escapeXml(currentYearContributions)}
        </text>
      </g>
      <!-- Total Contributions label -->
      <g transform="translate(82.5, 84)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#6b5b73" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="400" font-size="14px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.7s">
          Total Contributions
        </text>
      </g>
      <!-- Total Contributions range -->
      <g transform="translate(82.5, 114)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#8a7c91" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="400" font-size="12px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.8s">
          ${escapeXml(totalRangeLabel)}
        </text>
      </g>
    </g>
    <g style="isolation: isolate">
      <!-- Current Streak label -->
      <g transform="translate(247.5, 108)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#8f64a7" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="700" font-size="14px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s">
          Current Streak
        </text>
      </g>
      <!-- Current Streak range -->
      <g transform="translate(247.5, 145)">
        <text x="0" y="21" stroke-width="0" text-anchor="middle" fill="#8a7c91" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="400" font-size="12px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 0.9s">
          ${escapeXml(currentStreakRangeLabel)}
        </text>
      </g>
      <!-- Ring around number -->
      <g mask="url(#mask_out_ring_behind_fire)">
        <circle cx="247.5" cy="71" r="40" fill="none" stroke="#7fa9ff" stroke-width="5" style="opacity: 0; animation: fadein 0.5s linear forwards 0.4s"/>
      </g>
      <!-- Fire icon -->
      <g transform="translate(247.5, 19.5)" stroke-opacity="0" style="opacity: 0; animation: fadein 0.5s linear forwards 0.6s">
        <path d="M -12 -0.5 L 15 -0.5 L 15 23.5 L -12 23.5 L -12 -0.5 Z" fill="none"/>
        <path d="M 1.5 0.67 C 1.5 0.67 2.24 3.32 2.24 5.47 C 2.24 7.53 0.89 9.2 -1.17 9.2 C -3.23 9.2 -4.79 7.53 -4.79 5.47 L -4.76 5.11 C -6.78 7.51 -8 10.62 -8 13.99 C -8 18.41 -4.42 22 0 22 C 4.42 22 8 18.41 8 13.99 C 8 8.6 5.41 3.79 1.5 0.67 Z M -0.29 19 C -2.07 19 -3.51 17.6 -3.51 15.86 C -3.51 14.24 -2.46 13.1 -0.7 12.74 C 1.07 12.38 2.9 11.53 3.92 10.16 C 4.31 11.45 4.51 12.81 4.51 14.2 C 4.51 16.85 2.36 19 -0.29 19 Z" fill="#e889b9" stroke-opacity="0"/>
      </g>
      <!-- Current Streak big number -->
      <g transform="translate(247.5, 48)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#5b8def" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="700" font-size="28px" font-style="normal" style="animation: currstreak 0.6s linear forwards">
          ${escapeXml(currentStreak.count)}
        </text>
      </g>
    </g>
    <g style="isolation: isolate">
      <!-- Longest Streak big number -->
      <g transform="translate(412.5, 48)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#5b8def" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="700" font-size="28px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 1.2s">
          ${escapeXml(longestStreak.count)}
        </text>
      </g>
      <!-- Longest Streak label -->
      <g transform="translate(412.5, 84)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#6b5b73" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="400" font-size="14px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 1.3s">
          Longest Streak
        </text>
      </g>
      <!-- Longest Streak range -->
      <g transform="translate(412.5, 114)">
        <text x="0" y="32" stroke-width="0" text-anchor="middle" fill="#8a7c91" stroke="none" font-family="&quot;Segoe UI&quot;, Ubuntu, sans-serif" font-weight="400" font-size="12px" font-style="normal" style="opacity: 0; animation: fadein 0.5s linear forwards 1.4s">
          ${escapeXml(longestStreakRangeLabel)}
        </text>
      </g>
    </g>
  </g>
</svg>
`;
}

async function writeSvgIfChanged(targetUrl, content) {
  const outputPath = fileURLToPath(targetUrl);
  await mkdir(dirname(outputPath), { recursive: true });
  let existingContent = null;
  try {
    existingContent = await readFile(outputPath, "utf8");
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }
  if (existingContent === content) {
    return false;
  }
  await writeFile(outputPath, content, "utf8");
  return true;
}

const statsUpdated = await writeSvgIfChanged(
  new URL("../assets/github-stats.svg", import.meta.url),
  buildGitHubStatsSvg(),
);
const streakUpdated = await writeSvgIfChanged(
  new URL("../assets/streak-stats.svg", import.meta.url),
  buildStreakStatsSvg(),
);

console.log(
  `Processed GitHub statistics for ${username} (stats updated: ${statsUpdated}, streak updated: ${streakUpdated}).`,
);
