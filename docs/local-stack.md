# Local stack: capabilities-ai, core-engine, rx-analytics

Run the three backends/frontends on fixed localhost ports with cross-service URLs wired automatically.

| Service | Port | Role |
|---------|------|------|
| capabilities-ai | 3001 | API hub — rx-analytics calls this |
| core-engine | 3002 | Chat/voice engine — calls capabilities for analytics |
| rx-analytics | 16588 | Vite dashboard (proxies to capabilities only) |

## Prerequisites

1. **GitHub SSH** with read access to `IndexHealth` and `TheRxAssistant` (see README authentication).
2. **Bun** and **Docker** (Redis via compose).
3. **`.env.stack`** at the workspace root — copy from `.env.stack.example` and paste stage DB URLs and API keys from your team secrets.

## Quick start

```bash
export DEV_REPOS_ROOT=/workspace DEV_REPOS_CHECKOUT_ROOT=/workspace/repos

# One-shot: clone, write .env files, install, Redis, start tmux servers
cp .env.stack.example .env.stack   # then edit with real values
local-dev setup

# Attach to running servers
tmux attach -t local-stack
```

## Step by step

```bash
dev-repos clone core-engine capabilities-ai rx-analytics
local-dev env          # writes .env / .env.local in each repo
local-dev install
local-dev infra-up     # Redis on localhost:6379
local-dev start        # tmux session: core-engine | capabilities | rx-analytics
local-dev status
```

## What `local-dev env` sets

Cross-service URLs (always localhost):

- capabilities → `CORE_ENGINE_URL=http://localhost:3002`
- core-engine → `CAPABILITIES_AI=http://localhost:3001`
- rx-analytics → `VITE_BASE_URL_CAPABILITITES=http://localhost:3001`

Secrets and databases come from `.env.stack` (typically **stage** Postgres on `52.39.160.45` ports `25001` / `26001` / `27001`).

## Optional: document-manager

Core-engine and capabilities validate `DOC_MANAGER_URL` at runtime for some flows. For full RAG/chat you may also run document-manager on port `3000`, or point `DOC_MANAGER_URL` in `.env.stack` at stage (`https://docs-admin-be-stage.healthbackend.com/inference`).

## Troubleshooting

- **Clone fails with "Repository not found"** — SSH key must have org access; ensure `dev-repos` uses SSH (`GIT_CONFIG_GLOBAL=/dev/null` is applied automatically).
- **Boot fails on missing env** — fill every required key in `.env.stack`; compare each repo's `.env.example`.
- **capabilities cannot reach core-engine** — start order in tmux is core-engine first; wait until port 3002 responds before capabilities finishes boot checks on `/api-status/...` (capabilities only checks connectivity on the status page, not at process start).
- **Redis errors** — run `local-dev infra-up` or set `REDIS_HOST` / `REDIS_PORT` in `.env.stack` to stage Redis if you prefer.
