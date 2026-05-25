# Cursor multi-repo dev environment

This repository owns the Cursor dev-environment setup for the Index Health and TheRx Assistant repos. It is intentionally separate from `index-member-portal` so environment automation does not live inside any one product repo.

## What is included

- `Dockerfile` installs common development tooling: Git, Git LFS, GitHub CLI, SSH client, Python 3, Node 22, pnpm, and Bun.
- `config/repos.json` is the single source of truth for the repo list and package roots.
- `scripts/dev-repos` manages clone/status/fetch/update/default branches/worktrees across the configured repos.
- `scripts/bootstrap` clones the configured repos and prints their status for first-run setup.

You provided 8 repos so far. Add the remaining 2 repos to `config/repos.json` when ready.

## Authentication

The Dockerfile does not bake GitHub credentials into the image.

Recommended setup is SSH access to both GitHub orgs:

1. Add an SSH key with access to `index_health` and `therx_assistant`.
2. Make the key available to the Cursor environment through the platform's secret/SSH mechanism.
3. Keep `DEV_REPOS_GIT_PROTOCOL=ssh`, which is the default.

If you prefer HTTPS, set:

```bash
DEV_REPOS_GIT_PROTOCOL=https
```

Then authenticate GitHub in the environment before cloning.

## Cursor setup

Use this repository as the dev-environment repository and configure Cursor to build from `Dockerfile`.

Recommended startup command:

```bash
scripts/bootstrap
```

By default, repos are cloned into:

```txt
/workspace/repos/<org>/<repo>
```

Worktrees are created under:

```txt
/workspace/worktrees/<org>/<repo>/<branch-name>
```

You can override those locations:

```bash
DEV_REPOS_ROOT=/workspace
DEV_REPOS_CHECKOUT_ROOT=/workspace/repos
DEV_REPOS_WORKTREES_ROOT=/workspace/worktrees
```

## Common commands

List configured repos:

```bash
dev-repos list
```

Clone all missing repos:

```bash
dev-repos clone
```

Check all repo states:

```bash
dev-repos status
```

Fetch without changing branches:

```bash
dev-repos fetch
```

Fast-forward current branches where safe:

```bash
dev-repos update
```

Sync default branches across all repos:

```bash
dev-repos sync-default
```

Create the same branch in selected repos:

```bash
dev-repos branch-create feature/member-sync index_health/core-engine index-member-portal
```

Create worktrees for parallel branch work:

```bash
dev-repos worktree-add feature/member-sync index_health/core-engine index-member-portal
```

Remove matching worktrees:

```bash
dev-repos worktree-remove feature/member-sync index_health/core-engine index-member-portal
```

Print package root paths for install automation:

```bash
dev-repos package-roots
```

## Local three-service stack

Run **capabilities-ai** (3001), **core-engine** (3002), and **rx-analytics** (16588) wired to each other on localhost:

```bash
cp .env.stack.example .env.stack   # add stage DB URLs + API keys
export DEV_REPOS_ROOT=/workspace DEV_REPOS_CHECKOUT_ROOT=/workspace/repos
local-dev setup
tmux attach -t local-stack
```

See [docs/local-stack.md](docs/local-stack.md) for ports, env variables, and troubleshooting.

## Benefits

- One Cursor environment can clone and manage all configured repos.
- Bulk update commands skip dirty repos instead of overwriting local work.
- Worktrees let you keep multiple branches checked out at the same time.
- Repo layout is predictable across humans and agents.
- GitHub credentials stay outside the Docker image.

## Tradeoffs

- Startup is slower when cloning many large repos.
- The environment uses more disk space, especially with many worktrees.
- Dependency installation is not automatic yet; use `dev-repos package-roots` to decide which package roots to install.
- Branches that span multiple repos still need separate commits and PRs per repo.
- If SSH or GitHub token access expires, clone/update commands will fail until auth is fixed.
