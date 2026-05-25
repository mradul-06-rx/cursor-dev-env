# Cursor Dev Environment - Agent Instructions

This is a **multi-repo dev environment orchestrator**, not an application codebase. It manages cloning and coordinating 8 product repositories across two GitHub organizations (`IndexHealth`, `TheRxAssistant`).

## Cursor Cloud specific instructions

### What this repo does

The `dev-repos` CLI (`scripts/dev-repos`) manages clone/status/fetch/update/branches/worktrees across configured repos listed in `config/repos.json`. The `scripts/bootstrap` script runs clone + status for first-run setup.

### Runtime tooling

| Tool | Version | Purpose |
|------|---------|---------|
| Node.js | 22.x | JS/TS runtime for product repos |
| pnpm | latest | Package manager for product repos |
| Bun | latest | Alt runtime/bundler for product repos |
| Python 3 | 3.12+ | Powers the `dev-repos` CLI |
| gh | latest | GitHub CLI (HTTPS auth for cloning) |

### Authentication

- The `GITHUB_SSH_PRIVATE_KEY` secret must contain a valid **private** key (starts with `-----BEGIN OPENSSH PRIVATE KEY-----`), not a public key.
- If SSH is unavailable, set `DEV_REPOS_GIT_PROTOCOL=https` and ensure the gh token has access to both orgs.
- The Cursor platform's default `gh` token does NOT have access to the private `IndexHealth` and `TheRxAssistant` org repos. SSH is the recommended auth method.
- GitHub org names are `IndexHealth` and `TheRxAssistant` (PascalCase, not snake_case).

### Key environment variables

```
DEV_REPOS_ROOT=/workspace          # Root of the dev environment
DEV_REPOS_CHECKOUT_ROOT=/workspace/repos   # Where repos are cloned
DEV_REPOS_WORKTREES_ROOT=/workspace/worktrees  # Worktree location
DEV_REPOS_GIT_PROTOCOL=ssh         # ssh (default) or https
```

### Running the tooling

All commands are documented in `README.md`. Key ones:

- `dev-repos list` — show configured repos
- `dev-repos clone` — clone missing repos
- `dev-repos status` — show branch/dirty state
- `dev-repos update` — fetch + fast-forward
- `dev-repos package-roots` — print paths for install automation

### Gotchas

1. **No `package.json` in this repo** — this orchestrator has no JS dependencies of its own. Dependency installation happens inside the cloned child repos.
2. **Repos dir is gitignored** — `/workspace/repos/` and `/workspace/worktrees/` are created at runtime by `dev-repos clone`.
3. **Python module path** — `dev-repos` imports `dev_repos_ops` from the same `scripts/` directory. The symlink at `/usr/local/bin/dev-repos` makes this work because Python resolves the real path.
4. **Bun install location** — Bun installs to `~/.bun/bin/bun`; ensure PATH includes `$HOME/.bun/bin`.
5. **Product repos are private** — The configured repos under `IndexHealth` and `TheRxAssistant` orgs are private and require a valid SSH private key in the `GITHUB_SSH_PRIVATE_KEY` secret.
6. **Cloned repos do NOT persist across sessions** — `/workspace/` is the git checkout, and `repos/` is gitignored. Every new Cloud Agent session starts fresh. The update script re-runs `dev-repos clone` (idempotent) to restore them.
7. **Git URL rewriting blocks SSH** — Cursor Cloud Agent VMs have global `git config url.*.insteadOf` rules that rewrite `git@github.com:` to HTTPS with the platform token. This token lacks access to `IndexHealth`/`TheRxAssistant` private repos. The update script adds org-specific identity overrides (`git config --global url."git@github.com:IndexHealth/".insteadOf "git@github.com:IndexHealth/"`) so that SSH is preserved for these orgs.
8. **`DEV_REPOS_ROOT` must be set** — The Dockerfile sets `ENV DEV_REPOS_ROOT="/workspace"` but Cloud Agent VMs don't use the Dockerfile. Without this variable, repos clone to `~/workspace/repos/` instead of `/workspace/repos/`. The update script exports it.
