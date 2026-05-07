# Spark Pro Connection Tokens Are Paused

Spark CLI does not currently ship a public setup path for Spark Pro connection
tokens.

## Current Hosted Setup

Railway and VPS deployments should use the hosted Spark secrets that are already
part of the live path:

```text
SPARK_UI_API_KEY=<private browser/API owner key>
SPARK_BRIDGE_API_KEY=<private bot-to-spawner bridge key>
TELEGRAM_RELAY_SECRET=<private Telegram relay secret>
SPAWNER_UI_PUBLIC_URL=https://<public-spawner-host>
SPAWNER_UI_BASE_URL=http://<private-spawner-host>:<port>
```

Do not add a Pro bearer-token setup step to Spark CLI docs, generated env files,
or onboarding output. That would make an unshipped entitlement path look
production-ready and could confuse it with Spawner's owner and bridge secrets.

## Bringing It Back Later

Reactivate this only after Spark Pro systems expose a shipped downstream flow
that consumes `SPARK_PRO_CONNECTION_TOKEN` end to end. The reactivation should
include:

1. A clear CLI command or guided prompt that explains what the token unlocks.
2. Tests proving the token is never treated as `SPARK_UI_API_KEY` or
   `SPARK_BRIDGE_API_KEY`.
3. Railway and VPS docs that mark the token as optional Pro-gated content proof,
   not as required deploy auth.
4. A rollback path that lets hosted deployments keep running without Pro tokens.
