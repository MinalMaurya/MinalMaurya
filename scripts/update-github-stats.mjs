import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const username = process.env.GH_USER;
const token = process.env.GH_TOKEN;

if (!username || !token) {
  throw new Error("GH_USER and GH_TOKEN must be set.");
}

async function githubGraphql(query, variables = {}) {
  const response = await fetch("https://api.github.com/graphql", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    throw new Error(`GitHub GraphQL request failed with HTTP ${response.status}.`);
  }

  const result = await response.json();
  if (result.errors?.length) {
    throw new Error(`GitHub GraphQL request failed: ${result.errors.map((error) => error.message).join("; ")}`);
  }

  return result.data;
}

async function getSearchCount(searchQuery) {
  const data = await githubGraphql(
    "query($query: String!) { search(query: $query, type: ISSUE, first: 1) { issueCount } }",
    { query: searchQuery },
  );
  return data.search.issueCount;
}

const profile = await githubGraphql(
  "query($login: String!) { user(login: $login) { createdAt } }",
  { login: username },
);

if (!profile.user) {
  throw new Error(`GitHub user ${username} was not found.`);
}

const createdAt = new Date(profile.user.createdAt);
const now = new Date();
const contributionQuery = `query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { totalContributions }
      repositoriesContributedTo(first: 1) { totalCount }
    }
  }
}`;

let totalContributions = 0;
for (let year = createdAt.getUTCFullYear(); year <= now.getUTCFullYear(); year += 1) {
  const from = year === createdAt.getUTCFullYear()
    ? createdAt
    : new Date(Date.UTC(year, 0, 1));
  const to = year === now.getUTCFullYear()
    ? now
    : new Date(Date.UTC(year + 1, 0, 1) - 1);
  const data = await githubGraphql(contributionQuery, {
    login: username,
    from: from.toISOString(),
    to: to.toISOString(),
  });

  if (!data.user) {
    throw new Error(`GitHub user ${username} was not found while reading contributions.`);
  }
  totalContributions += data.user.contributionsCollection.contributionCalendar.totalContributions;
}

const lastYearStart = new Date(now);
lastYearStart.setUTCFullYear(lastYearStart.getUTCFullYear() - 1);
const lastYear = await githubGraphql(contributionQuery, {
  login: username,
  from: lastYearStart.toISOString(),
  to: now.toISOString(),
});

if (!lastYear.user) {
  throw new Error(`GitHub user ${username} was not found while reading last-year contributions.`);
}
const contributedToLastYear =
  lastYear.user.contributionsCollection.repositoriesContributedTo.totalCount;

let totalStars = 0;
for (let page = 1; ; page += 1) {
  const response = await fetch(
    `https://api.github.com/users/${encodeURIComponent(username)}/repos?per_page=100&page=${page}&type=owner`,
    { headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json" } },
  );
  if (!response.ok) {
    throw new Error(`GitHub repositories request failed with HTTP ${response.status}.`);
  }
  const repositories = await response.json();
  totalStars += repositories.reduce((sum, repository) => sum + repository.stargazers_count, 0);
  if (repositories.length < 100) {
    break;
  }
}

const [totalPullRequests, totalIssues] = await Promise.all([
  getSearchCount(`author:${username} is:pr`),
  getSearchCount(`author:${username} is:issue`),
]);

const metrics = [
  ["Total Contributions (Oct 13, 2023–Present)", totalContributions],
  ["Total Stars Earned", totalStars],
  ["Total PRs", totalPullRequests],
  ["Total Issues", totalIssues],
  ["Contributed to (last year)", contributedToLastYear],
];
const rows = metrics.map(([label, value], index) => {
  const y = 89 + index * 32;
  return `  <text x="28" y="${y}" class="label">${label}:</text>\n  <text x="425" y="${y}" class="value">${value}</text>`;
}).join("\n");

const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="580" height="258" viewBox="0 0 580 258" role="img" aria-labelledby="title desc">
  <title id="title">Minal Maurya's GitHub Stats</title>
  <desc id="desc">Live GitHub statistics. Contributions are counted since October 13, 2023.</desc>
  <style>
    .title { font: 700 20px 'Segoe UI', Ubuntu, sans-serif; fill: #5B8DEF; }
    .label { font: 600 15px 'Segoe UI', Ubuntu, sans-serif; fill: #6B5B73; }
    .value { font: 700 15px 'Segoe UI', Ubuntu, sans-serif; fill: #E889B9; }
  </style>
  <rect x="1" y="1" width="578" height="256" rx="8" fill="#FDF7FB" stroke="#F3DDEB"/>
  <text x="28" y="43" class="title">Minal Maurya's GitHub Stats</text>
${rows}
</svg>
`;

const outputPath = fileURLToPath(new URL("../assets/github-stats.svg", import.meta.url));
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, svg);
console.log(`Updated GitHub statistics for ${username}.`);
