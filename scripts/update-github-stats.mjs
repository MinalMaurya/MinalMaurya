import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const username = process.env.GH_USER || "MinalMaurya";
const token = process.env.GH_TOKEN;

if (!username || !token) {
  throw new Error("GH_USER and GH_TOKEN must be set.");
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function assertNonNegativeInteger(name, value) {
  if (!Number.isInteger(value) || value < 0) {
    throw new Error(`Invalid statistic value for ${name}: ${value}`);
  }
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

  if (!result.data) {
    throw new Error("GitHub GraphQL response did not include data.");
  }

  return result.data;
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

function formatUtcDate(date, { longMonth = false } = {}) {
  const year = date.getUTCFullYear();
  const month = date.getUTCMonth();
  const day = date.getUTCDate();
  const monthName = (longMonth ? MONTHS_LONG : MONTHS_SHORT)[month];
  return `${monthName} ${day}, ${year}`;
}

async function fetchTotalStars(login) {
  let totalStars = 0;
  let after = null;

  const repositoriesQuery = `query($login: String!, $after: String) {
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
    const data = await githubGraphql(repositoriesQuery, { login, after });
    const repositories = data.user?.repositories;
    if (!repositories || !Array.isArray(repositories.nodes)) {
      throw new Error(`Unable to read repositories for ${login}.`);
    }

    for (const repository of repositories.nodes) {
      assertNonNegativeInteger("repository.stargazerCount", repository.stargazerCount);
      totalStars += repository.stargazerCount;
    }

    if (!repositories.pageInfo?.hasNextPage) {
      break;
    }
    after = repositories.pageInfo.endCursor;
  }

  return totalStars;
}

async function fetchLifetimeContributions(login, createdAt, now) {
  const contributionQuery = `query($login: String!, $from: DateTime!, $to: DateTime!) {
    user(login: $login) {
      contributionsCollection(from: $from, to: $to) {
        contributionCalendar {
          totalContributions
        }
      }
    }
  }`;

  let totalContributions = 0;
  const startYear = createdAt.getUTCFullYear();
  const currentYear = now.getUTCFullYear();

  for (let year = startYear; year <= currentYear; year += 1) {
    const from = year === startYear ? createdAt : new Date(Date.UTC(year, 0, 1, 0, 0, 0));
    const to =
      year === currentYear ? now : new Date(Date.UTC(year, 11, 31, 23, 59, 59, 999));

    const data = await githubGraphql(contributionQuery, {
      login,
      from: from.toISOString(),
      to: to.toISOString(),
    });

    const yearlyTotal =
      data.user?.contributionsCollection?.contributionCalendar?.totalContributions;
    assertNonNegativeInteger(`contributions(${year})`, yearlyTotal);
    totalContributions += yearlyTotal;
  }

  return totalContributions;
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
    repositoriesContributedTo(
      first: 1
      contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]
    ) {
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
if (Number.isNaN(createdAt.getTime())) {
  throw new Error(`Invalid createdAt date for ${username}: ${profileData.user.createdAt}`);
}

const now = new Date();
const [totalContributions, totalStars] = await Promise.all([
  fetchLifetimeContributions(username, createdAt, now),
  fetchTotalStars(username),
]);

const totalPullRequests = profileData.user.pullRequests?.totalCount;
const totalIssues = profileData.user.issues?.totalCount;
const contributedToLastYear = profileData.user.repositoriesContributedTo?.totalCount;

assertNonNegativeInteger("totalContributions", totalContributions);
assertNonNegativeInteger("totalStars", totalStars);
assertNonNegativeInteger("totalPullRequests", totalPullRequests);
assertNonNegativeInteger("totalIssues", totalIssues);
assertNonNegativeInteger("contributedToLastYear", contributedToLastYear);

const createdAtShortLabel = formatUtcDate(createdAt, { longMonth: false });
const createdAtLongLabel = formatUtcDate(createdAt, { longMonth: true });

const metrics = [
  [`Total Contributions (${createdAtShortLabel}–Present)`, totalContributions],
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

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="580" height="258" viewBox="0 0 580 258" role="img" aria-labelledby="title desc">
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

const outputPath = fileURLToPath(new URL("../assets/github-stats.svg", import.meta.url));
await mkdir(dirname(outputPath), { recursive: true });

let existingSvg = null;
try {
  existingSvg = await readFile(outputPath, "utf8");
} catch (error) {
  if (error.code !== "ENOENT") {
    throw error;
  }
}

if (existingSvg === svg) {
  console.log(`No changes in GitHub statistics for ${username}.`);
} else {
  await writeFile(outputPath, svg, "utf8");
  console.log(`Updated GitHub statistics for ${username}.`);
}
