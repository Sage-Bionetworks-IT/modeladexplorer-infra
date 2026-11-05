---
name: pr-description
description: >
  Generates a PR title and description body for this infra repo, following the team's PR standards.
  Use this skill whenever the user asks to create, write, generate, or update a PR description,
  or when working with an active pull request that needs documentation. Also use this when the
  user says things like "write up this PR", "draft the PR", "prepare the PR", or "describe these changes".
---

# PR Description Generator

Generate a PR title and a markdown description body that a contributor can paste directly into
a new GitHub pull request. Save the output to a single file in `tmp/pr-description/` at the
repo root (this directory is gitignored).

## Output File

Write one file: `tmp/pr-description/<ticket-id>.md`, where `<ticket-id>` is the Jira ticket
found in Step 1. For example, if the commits reference `EX-164`, the output file is
`tmp/pr-description/EX-164.md`.

The file starts with the PR title as an H1 heading, followed by the description body:

```markdown
# feat: send ECS task and deployment events to CloudWatch Logs (EX-164)

## Description

...
```

Tell the user where the file is after writing it.

---

## Step 1 — Identify the Jira Ticket

The ticket ID appears in one of these places (check in order):

1. Recent commit messages on the current branch (not on `dev`) — usually in parentheses at the
   end of the subject, e.g. `feat: add Claude Code MCP and dev container support (MG-1198)`
2. The current git branch name — branches in this repo usually don't include the ticket
   (e.g. `feat/ecs-events-logs`), but check in case one does
3. The user may state it directly

Common ticket prefixes for this repo: **EX**, **MG**.

### Fetching ticket details from Jira

Use the Atlassian MCP server (`mcp__atlassian__*`), with `sagebionetworks.jira.com` as the
`cloudId`.

For each PR, pull:

- The ticket itself — summary, description, and acceptance criteria
- All **sub-tasks**
- All **linked/related issues**
- The **parent / epic**, including its description and acceptance criteria

Acceptance criteria feed the Testing and Validation sections directly. Parent/epic context explains _why_
the work exists, which strengthens the Description section.

**If a Jira call fails with an auth error (401/403), stop and ask the user to run `/mcp`
to re-authenticate. Do not continue generating the PR description until access is
confirmed.** Non-auth errors (404, network timeout) are fine to work around — note that
the ticket couldn't be fetched and proceed with what you have from the branch name,
commit messages, and code changes.

---

## Step 2 — Analyze the Changes

PRs in this repo target `dev`. Look at all commits on the current branch that are not on `dev`.
The local `dev` can be behind, so compare against `upstream/dev` when that remote exists
(`git fetch upstream dev` first), and against `dev` otherwise:

```bash
git log upstream/dev..HEAD --oneline
git diff upstream/dev...HEAD --stat
```

Read the changed files to understand what was done. Categorize changes by:

- **Type** — see Step 3
- **Stacks and AWS resources** — which CDK stacks (`src/*_stack.py`, wired up in `app.py`) are
  added or changed, and which AWS resources that creates, replaces or deletes
- **Environment-specific changes** — values in the per-environment blocks of `app.py`
  (dev, stage, prod), such as image versions, capacity or domain names
- **Deploy impact** — anything that replaces a resource, causes downtime, changes a
  cross-stack export, or needs a manual step before or after deploying (secrets, certificates,
  DNS)

---

## Step 3 — Generate the PR Title

This repo has no PR title lint workflow; follow the conventional-commit style of recent commits:

```
type(scope): lowercase subject (TICKET-IDs)
```

Rules:

- **type**: one of `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, `test`
- **scope** (optional): use one only when it adds clarity, e.g. `deps`
- **subject**: must NOT start with an uppercase letter
- Append the Jira ticket ID(s) in parentheses at the end, e.g., `(EX-164)` or `(EX-164, EX-166)`

Match the style of recent commits. Check a few with:

```bash
git log upstream/dev --oneline --no-merges -10
```

Examples from this repo:

- `feat: add Claude Code MCP and dev container support (MG-1198)`
- `chore: use pre-commit frozen rev format and update hooks`
- `chore(deps): bump ghcr.io/devcontainers/features/python`

---

## Step 4 — Generate the Description Body

Use this exact template. Do not add sections or change headings — this is the team's standard
PR description format. It replaces the contents of this repo's
`.github/pull_request_template.md`, which is a checklist to delete before submitting.

```markdown
## Description

[2-4 sentences explaining WHY these changes were made and the business/technical motivation.
Focus on the objective and benefits, not a list of what changed.]

## Related Issue

[Link to the Jira ticket. Include sub-tasks and related issues if they exist.]

- [TICKET-ID](https://sagebionetworks.jira.com/browse/TICKET-ID)
  - Sub-task: [TICKET-ID](url) — summary
  - Related: [TICKET-ID](url) — summary

## Changelog

- [High-level change — imperative voice, e.g., "Add feature X"]
- [Another high-level change]

## Testing

[Steps a reviewer can follow locally, before anything is deployed.
Do NOT include unit test or synth commands on their own — CI handles those.]

- Step a reviewer can perform locally
- Another local verification step

## Validation

[Steps to confirm in DEV once the PR is merged to `dev` and the `deploy-dev` workflow has deployed it.]

- Check to perform in DEV after the deploy
- Another DEV check

### Preview

[If the PR changes something visible, suggest specific screenshots to capture.]

| Before                                       | After                                       |
| -------------------------------------------- | ------------------------------------------- |
| [describe what to screenshot before merging] | [describe what to screenshot after the DEV deploy] |
```

---

## Content Guidelines

### Description

- Lead with the business or technical objective — why was this work done?
- Mention the Jira ticket context if it adds clarity
- Keep it to 2-4 sentences
- Refer to related work by its Jira ticket key, not by a PR reference such as `sage-monorepo#4230`

### Ticket links

- Every Jira ticket key in the output must be a link with a full URL, wherever it appears —
  in the Description, Changelog, Testing and Validation sections as well as Related Issue:
  `[MG-1028](https://sagebionetworks.jira.com/browse/MG-1028)`, not `MG-1028`
- The only exception is the PR title, which keeps the plain key in parentheses, e.g. `(EX-164)`

### Related Issue

- Always link the Jira ticket with a full URL: `[EX-164](https://sagebionetworks.jira.com/browse/EX-164)`
- If acceptance criteria were found, you do not need to reproduce them here — they inform the Testing and Validation sections instead
- Omit this section only if there is genuinely no related ticket

### Changelog

- Use **flat, single-level bullets only** — no nested items
- Write in imperative voice: "Add", "Remove", "Update", "Fix"
- Keep items coarse-grained — group related file-level changes into one bullet
- Name the stack or AWS resource when it helps, e.g. "Add a `model-ad-<env>-monitoring` stack"
- Call out deploy impact (resource replacement, downtime, manual steps) in its own bullet
- Order from most to least important
- Aim for **3–7 bullets**; this is not an exhaustive file list

### Testing and Validation

Both sections are for **human reviewers**, not CI. Split the steps by where they can be done:

- **Testing** — anything a reviewer can do from their own machine before the PR is merged,
  without deploying anything. For example:
  - run `env $(cat .env | xargs) uv run cdk synth` and inspect the synthesized template in `cdk.out/` for a
    specific resource or property, or confirm an existing stack's template only changed as expected
- **Validation** — anything that needs the change deployed. Merging to `dev` triggers the
  `deploy-dev` workflow, so these are checks to run in DEV after that deploy. For example:
  - check the new or changed resource in the AWS console or with the AWS CLI
  - trigger the behaviour the change is about (a deploy, a data release, a failover) and confirm
    the result
  - confirm the site at the DEV domain still works after the deploy

Rules for both:

- Use a **bullet list** (`-`)
- Pull from Jira acceptance criteria when available — translate them into concrete reviewer
  steps, and put each one in Testing or Validation depending on whether it needs a deploy
- **Do NOT list running `pytest` or `cdk synth` as a step by itself** — the `pr-check` workflow
  runs both on every PR. Inspecting specific parts of the synth output is fine
- Aim for **2–5 actionable steps** in each section. If nothing can be checked before deploying,
  say so in one line under Testing rather than omitting the section

### Preview

- Preview sits under Validation, since screenshots of infra changes come from DEV after the deploy
- Only include this sub-section when the PR changes something a reviewer can see, such as
  the site itself or a page in the AWS console (see the console screenshots in `docs/` for examples)
- Suggest **specific screens** to screenshot, not generic "take a screenshot"
- Use the before/after table format from the template
- Be precise: "Screenshot the Logs Insights saved queries panel for model-ad-dev" is better than "Screenshot the console"
- If the change has nothing to show, omit the Preview sub-section entirely

---

## Final Checklist (internal — do not include in output)

Before writing the files, verify:

- Title follows the conventional-commit format (type, optional scope, lowercase subject, ticket ID)
- Description explains the "why", not just the "what"
- Every ticket key outside the title is a link with a full URL, not just those in Related Issue
- Changelog is 3–7 flat bullets in imperative voice, including any deploy impact
- Testing has only steps that work before deploying; Validation has the steps that need the DEV deploy
- Neither section lists running `pytest` or `cdk synth` by itself
- Preview sub-section is under Validation, present only for visible changes, with specific guidance
- Jira acceptance criteria are reflected in Testing or Validation steps where applicable
- `tmp/` is listed in `.gitignore`
- Output is saved to `tmp/pr-description/TICKET-ID.md`
