# Spark Live on Docker, Railway, and VPS

Last updated: 2026-04-29

Spark should be easy to test in an environment that is not the operator's laptop. This lane is for realtime sandbox agents: a disposable or persistent container that runs Spark Live, Telegram long polling, Builder, memory, character, and Spawner together.

This is separate from the locked-down Docker workbench in `docs/OPTIONAL_DOCKER_WORKBENCH.md`. The live lane has network on by design because Telegram and the selected LLM provider need it.

## What Runs

The live container starts:

- as `root` only long enough to prepare the mounted state volume, then drops to the non-root `spark` user;
- `spark setup telegram-starter` in `/data/spark`;
- `spark update --skip-dirty` so persistent volumes move to the image's current registry pins on redeploy;
- `spark live start`;
- `spawner-ui`, bound to `0.0.0.0:$SPARK_SPAWNER_PORT`;
- `spark-telegram-bot`, using Telegram long polling;
- Builder, memory, researcher, and character as installed modules/configured roots.

Secrets are read from environment variables only. They are not baked into the image.

## Best First Host

Use Docker locally for smoke tests, then Railway for a hosted sandbox.

Railway is a good first target because it gives:

- a public HTTPS app URL for Spawner/Canvas/Kanban;
- app secrets as environment variables;
- optional persistent volumes for `/data/spark`;
- simple redeploys when Spark CLI is pinned to a new release.

Any VPS with Docker also works.

## What We Learned From Other Agent Hosts

OpenClaw-style hosted deployments show why browser-first onboarding matters:
users understand a single `/setup` or control-panel surface much faster than
SSH plus many terminal commands. Railway templates also proved that a persistent
volume, setup wizard, model/channel picker, and one public HTTPS URL are a good
shape for nontechnical users.

The same pattern creates risk if it is not locked down. Spark Live should keep
these standards:

- one public surface, protected by a user-chosen access key;
- API routes require `SPARK_BRIDGE_API_KEY`, not just a browser cookie;
- setup is browser-friendly, but repeat setup is not an unauthenticated open URL;
- public hosts must set `SPARK_ALLOWED_HOSTS` to exact domains;
- the runtime drops to a non-root user before starting Spark services;
- no Docker socket, host root, cloud credentials, SSH keys, browser profiles, or
  real local `~/.spark` mounts;
- headless hosts use API-key providers, not interactive OAuth CLIs;
- every hosted release must pass `spark verify --hosted --deep`.

Hermes-style approval systems are also relevant for future full-access hosted
agents: dangerous shell/file operations should ask in-chat or in-UI, with
allowlists that users can inspect and remove. Spark Live is not ready for a
public "full operating system access" VPS mode until those approvals and
sandbox boundaries are first-class.

## Required Environment

Minimum:

```text
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ADMIN_IDS=123456789
SPARK_LLM_PROVIDER=zai
ZAI_API_KEY=...
```

Supported `SPARK_LLM_PROVIDER` values for headless hosts:

| Provider | Required env | Notes |
|---|---|---|
| `zai` | `ZAI_API_KEY` | Good default for API-key VPS sandboxes. |
| `openai` | `OPENAI_API_KEY` | Use this for OpenAI API keys. |
| `openrouter` | `OPENROUTER_API_KEY` | Broad model gateway. |
| `kimi` | `KIMI_API_KEY` | Moonshot/Kimi OpenAI-compatible route. |
| `huggingface` | `HF_TOKEN` | Hugging Face router. |
| `minimax` | `MINIMAX_API_KEY` | MiniMax OpenAI-compatible route. |
| `anthropic` | `ANTHROPIC_API_KEY` | API-key mode only in containers. |
| `lmstudio` | `LMSTUDIO_BASE_URL`, optional `LMSTUDIO_MODEL` | Only if the container can reach your LM Studio server. |
| `ollama` | `OLLAMA_URL`, optional `OLLAMA_MODEL` | Only if the container can reach your Ollama server. |

Do not use `codex` for Railway/VPS containers. Codex OAuth is an interactive local CLI sign-in path, so it belongs on a user's machine, not in a headless hosted container. Use `openai` with an API key for hosted OpenAI access.

Optional:

```text
SPARK_MODEL=provider-specific-model-id
SPARK_SPAWNER_PORT=5173
SPARK_SPAWNER_HOST=0.0.0.0
```

On Railway, map `SPARK_SPAWNER_PORT` to `$PORT` if you expose the web process.

## Local Docker Smoke

From the `spark-cli` repo:

```bash
docker build -f docker/live/Dockerfile -t spark-live:local .
```

Run with a disposable Spark home:

```bash
docker run --rm -it \
  -p 5173:5173 \
  -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -e TELEGRAM_ADMIN_IDS="$TELEGRAM_ADMIN_IDS" \
  -e SPARK_LLM_PROVIDER=zai \
  -e ZAI_API_KEY="$ZAI_API_KEY" \
  spark-live:local
```

For persistence:

```bash
docker volume create spark-live-data
docker run --rm -it \
  -p 5173:5173 \
  -v spark-live-data:/data/spark \
  -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -e TELEGRAM_ADMIN_IDS="$TELEGRAM_ADMIN_IDS" \
  -e SPARK_LLM_PROVIDER=zai \
  -e ZAI_API_KEY="$ZAI_API_KEY" \
  spark-live:local
```

Then check:

```bash
docker exec -it <container> spark live status
docker exec -it <container> spark verify --onboarding
```

## Railway Shape

Recommended Railway settings:

```text
Build: Dockerfile
Dockerfile path: docker/live/Dockerfile
Start command: leave empty; the image entrypoint starts Spark Live
Volume mount: /data/spark
```

Set secrets in Railway Variables, never in source control:

```text
RAILWAY_DOCKERFILE_PATH=docker/live/Dockerfile
RAILWAY_RUN_UID=0
SPARK_ALLOWED_HOSTS=<your-railway-domain>.up.railway.app
SPARK_UI_API_KEY=<different-random-secret-at-least-24-chars>
SPARK_BRIDGE_API_KEY=<different-random-secret-at-least-24-chars>
TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_IDS
SPARK_LLM_PROVIDER
ZAI_API_KEY / OPENAI_API_KEY / etc.
SPARK_SPAWNER_PORT=${PORT}
```

`RAILWAY_RUN_UID=0` lets the entrypoint repair Railway volume ownership. Spark then
drops to the non-root `spark` user before setup and runtime work starts.
`SPARK_ALLOWED_HOSTS` lets Spawner's Vite server accept the generated Railway
domain without disabling host-header protection for every possible host. Use
hostnames only: no `https://`, no paths, no wildcards, no loopback values.
`SPARK_UI_API_KEY` protects the hosted Spawner UI. Open the Railway URL and Spark
will redirect browser users to `/spark-live/login`; paste the UI key there to set
an httpOnly browser cookie. The `?uiKey=<SPARK_UI_API_KEY>` route remains
available for automation/bootstrap, but it should not be the main human path.
`SPARK_BRIDGE_API_KEY` protects mission-start/control APIs.

After deploy:

1. Open the Railway logs and confirm `Spark Live is running`.
2. Run `spark verify --hosted` inside the container or over `railway ssh`.
3. Run `spark verify --hosted --deep` to start a protected mission smoke and
   confirm the result reaches the mission board.
4. Send `/diagnose` to the sandbox Telegram bot.
5. Open the Railway URL and sign in at `/spark-live/login`.
6. Send `/remember Railway sandbox works`, then `/recall Railway sandbox`.
7. Send `/run say exactly OK`.

The hosted deep smoke is intentionally not part of the fast default check. It
uses the configured mission provider and may spend real LLM credits.

## Security Rules

- Use a fresh Telegram bot for every hosted sandbox.
- Keep sandbox API keys scoped and revocable.
- Prefer separate hosted sandbox provider keys from the operator's main personal keys.
- Require `SPARK_UI_API_KEY` and `SPARK_BRIDGE_API_KEY` before exposing Spawner on a public host.
- Make `SPARK_UI_API_KEY` and `SPARK_BRIDGE_API_KEY` different random values,
  at least 24 characters each. Do not use placeholders such as `changeme`,
  `password`, `secret`, or `spark`.
- Keep hosted secret files private. `spark verify --hosted` fails if a POSIX
  `secrets.local.json` is group/world-readable.
- Do not mount or copy a real local `~/.spark` into hosted containers.
- Never mount `/var/run/docker.sock`, `/`, `/root`, cloud credential directories, SSH keys, or browser profiles.
- Prefer Docker hardening flags on VPS: `--cap-drop=ALL`, `--security-opt no-new-privileges`, resource limits, and only one writable Spark state volume.
- Use a persistent volume only when you intentionally want memory/state to survive redeploys.
- Rotate tokens after demos if screenshots/logs might have exposed them.
- Do not expose shell/terminal access in the browser until it is behind a separate
  admin auth layer and a dangerous-command approval system.
- Keep public health probes shallow. Deep health checks that reveal providers,
  mission ids, logs, or memory state must require an admin key.

## Recommended Hosted UX

For Spark to feel easier than current agent VPS setups, the target flow should be:

1. Click "Deploy Spark Live" from the site.
2. Choose a host template such as Railway for the easiest first path.
3. Enter one setup password/UI key, Telegram bot token, Telegram admin id, and one LLM provider.
4. Spark generates bridge secrets, stores them as platform variables, and starts.
5. Browser opens `/spark-live/login`, then Mission Control shows a guided checklist.
6. Telegram `/diagnose` and `spark verify --hosted --deep` both pass.

For VPS users who want full control, offer a Docker Compose path with the same
checks, but do not make them discover firewall, host header, volume ownership,
and secret rules by accident.

## References Used For This Standard

- OpenClaw Docker docs: non-root image, persistence paths, health checks,
  gateway bind modes, sandbox behavior, and Docker socket caveats.
- Railway OpenClaw templates: browser setup, model/channel picker, admin
  dashboard, persistent `/data`, and single-port deployment pattern.
- Hermes Agent security docs: dangerous-command approval, gateway allowlists,
  pairing, and Docker terminal backend resource/security settings.

## What This Proves

This lane proves Spark can:

- install the whole ecosystem on a clean Linux host;
- run Telegram long polling without webhooks;
- keep Spawner, Telegram, memory, and LLM routing alive under one foreground process;
- support VPS/Railway users who do not want to keep a laptop terminal open.

It does not replace the local installer. Local users should still use the hosted installer from `agent.sparkswarm.ai`.
