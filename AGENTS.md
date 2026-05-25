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
DEV_REPOS_ROOT=/workspace                      # Root of the dev environment
DEV_REPOS_CHECKOUT_ROOT=/home/ubuntu/repos     # Where repos are cloned (persists in snapshot)
DEV_REPOS_WORKTREES_ROOT=/home/ubuntu/worktrees # Worktree location (persists in snapshot)
DEV_REPOS_GIT_PROTOCOL=ssh                     # ssh (default) or https
```

These are set in `~/.bashrc` and also exported in the update script.

### Running the tooling

All commands are documented in `README.md`. Key ones:

- `dev-repos list` — show configured repos
- `dev-repos clone` — clone missing repos
- `dev-repos status` — show branch/dirty state
- `dev-repos update` — fetch + fast-forward
- `dev-repos package-roots` — print paths for install automation

### Gotchas

1. **No `package.json` in this repo** — this orchestrator has no JS dependencies of its own. Dependency installation happens inside the cloned child repos.
2. **Repos live at `/home/ubuntu/repos/`** — cloned outside `/workspace/` so they persist in VM snapshots. A symlink `/workspace/repos → /home/ubuntu/repos` exists for convenience.
3. **Python module path** — `dev-repos` imports `dev_repos_ops` from the same `scripts/` directory. The symlink at `/usr/local/bin/dev-repos` makes this work because Python resolves the real path.
4. **Bun install location** — Bun installs to `~/.bun/bin/bun`; ensure PATH includes `$HOME/.bun/bin`.
5. **Product repos are private** — The configured repos under `IndexHealth` and `TheRxAssistant` orgs are private and require a valid SSH private key in the `GITHUB_SSH_PRIVATE_KEY` secret.
6. **Git URL rewriting blocks SSH** — Cursor Cloud Agent VMs have global `git config url.*.insteadOf` rules that rewrite `git@github.com:` to HTTPS with the platform token. This token lacks access to `IndexHealth`/`TheRxAssistant` private repos. The update script adds org-specific identity overrides (`git config --global url."git@github.com:IndexHealth/".insteadOf "git@github.com:IndexHealth/"`) so that SSH is preserved for these orgs.
7. **`DEV_REPOS_ROOT` and `DEV_REPOS_CHECKOUT_ROOT` must be set** — The Dockerfile sets ENV vars but Cloud Agent VMs don't use the Dockerfile. Without these, repos clone to the wrong path. The update script exports them.
8. **`.env` files are pre-created from `.env.example`** — Every repo has its `.env` (or `.env.local` for bausch-lomb) pre-populated from the example. Replace placeholder values with real credentials as needed.
9. **Dependencies are pre-installed** — All `node_modules` are pre-installed in the snapshot. If you need to refresh, use `bun install` for backends and `pnpm install` for frontends (or `npm install` for `index-chat-ui-embed` sub-apps).

### Local infrastructure (Docker)

Postgres, Redis, and Qdrant run as Docker containers on the VM. The update script starts Docker and the containers automatically.

| Container | Port | Credentials | Databases |
|-----------|------|-------------|-----------|
| `dev-postgres` | 5432 | `postgres:postgres` | `capabilities_ai_db`, `core_engine_db`, `doc_manager_db` |
| `dev-redis` | 6379 | none | — |
| `dev-qdrant` | 6333 | none | — |

Data is stored in Docker volumes (`pgdata`, `redisdata`, `qdrantdata`) and persists across container restarts.

To manually manage: `sudo docker start/stop/restart dev-postgres dev-redis dev-qdrant`

### Repo layout and package managers

| Repo | Package Manager | Dev Port | Notes |
|------|----------------|----------|-------|
| `capabilities-ai` (root) | bun | 3001 | Backend; needs Postgres, Redis |
| `capabilities-ai/crm` | pnpm | Vite default | CRM frontend |
| `document-manager/backend` | bun | 3000 | Needs Postgres, Redis, Qdrant |
| `document-manager/frontend` | pnpm | Vite default | Document manager UI |
| `index-member-portal` | pnpm | Vite default | Member portal PWA |
| `core-engine` (root) | bun | 3002 | Backend; needs Postgres |
| `core-engine/ce-frontend` | pnpm | Vite default | Admin/workbench UI |
| `bausch-lomb` | pnpm | 7654 | Chat embed; uses `.env.local` |
| `rx-analytics` | pnpm | 16588 | Ant Design dashboard |
| `index-chat-ui-embed/*` | npm | Vite default | 9 independent Vite apps |
| `rx-crm/backend` | bun | 3003 | CRM API |
| `rx-crm/frontend` | pnpm | 18656 | CRM UI |

### Starting backends

```bash
cd /home/ubuntu/repos/IndexHealth/capabilities-ai && bun run dev
cd /home/ubuntu/repos/IndexHealth/core-engine && bun run dev
cd /home/ubuntu/repos/IndexHealth/document-manager/backend && bun run dev
cd /home/ubuntu/repos/TheRxAssistant/rx-crm/backend && bun run dev
```

### Core-engine strict env validation

`core-engine` uses Zod and **exits on boot** if required vars are missing or blank. See `src/services/common/svc-env-schema.ts` for the full schema. The other backends read env lazily and only fail when a feature is actually used.
