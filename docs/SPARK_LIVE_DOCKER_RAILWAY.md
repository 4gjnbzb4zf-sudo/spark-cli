# Spark Live on Docker, Railway, and VPS

Last updated: 2026-04-28

Spark should be easy to test in an environment that is not the operator's laptop. This lane is for realtime sandbox agents: a disposable or persistent container that runs Spark Live, Telegram long polling, Builder, memory, character, and Spawner together.

This is separate from the locked-down Docker workbench in `docs/OPTIONAL_DOCKER_WORKBENCH.md`. The live lane has network on by design because Telegram and the selected LLM provider need it.

## What Runs

The live container starts:

- `spark setup telegram-starter` in `/data/spark`;
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
TELEGRAM_BOT_TOKEN
TELEGRAM_ADMIN_IDS
SPARK_LLM_PROVIDER
ZAI_API_KEY / OPENAI_API_KEY / etc.
SPARK_SPAWNER_PORT=${PORT}
```

`RAILWAY_RUN_UID=0` is required when using Railway volumes with this image because
Railway mounts volumes as `root`; without it, Spark cannot create `/data/spark/state`.
`SPARK_ALLOWED_HOSTS` lets Spawner's Vite server accept the generated Railway
domain without disabling host-header protection for every possible host.

After deploy:

1. Open the Railway logs and confirm `Spark Live is running`.
2. Send `/diagnose` to the sandbox Telegram bot.
3. Open the Railway URL for Spawner UI.
4. Send `/remember Railway sandbox works`, then `/recall Railway sandbox`.
5. Send `/run say exactly OK`.

## Security Rules

- Use a fresh Telegram bot for every hosted sandbox.
- Keep sandbox API keys scoped and revocable.
- Do not mount or copy a real local `~/.spark` into hosted containers.
- Use a persistent volume only when you intentionally want memory/state to survive redeploys.
- Treat public Spawner URLs as sensitive until access control is stronger.
- Rotate tokens after demos if screenshots/logs might have exposed them.

## What This Proves

This lane proves Spark can:

- install the whole ecosystem on a clean Linux host;
- run Telegram long polling without webhooks;
- keep Spawner, Telegram, memory, and LLM routing alive under one foreground process;
- support VPS/Railway users who do not want to keep a laptop terminal open.

It does not replace the local installer. Local users should still use the hosted installer from `agent.sparkswarm.ai`.
