from __future__ import annotations

from pathlib import Path


def test_live_docker_entrypoint_fails_closed_for_public_spawner() -> None:
    script = (Path(__file__).resolve().parents[1] / "docker" / "live" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "umask 077" in script
    assert "is_public_spawner_bind" in script
    assert "SPARK_ALLOWED_HOSTS is required when Spawner binds publicly" in script
    assert "require_strong_secret SPARK_BRIDGE_API_KEY" in script
    assert "require_strong_secret SPARK_UI_API_KEY" in script
    assert "SPARK_BRIDGE_API_KEY and SPARK_UI_API_KEY must be different" in script
    assert "must contain hostnames only, with no scheme, path, wildcard, or port" in script


def test_live_docker_entrypoint_supports_external_telegram_ingress() -> None:
    script = (Path(__file__).resolve().parents[1] / "docker" / "live" / "entrypoint.sh").read_text(encoding="utf-8")
    assert 'SPARK_LIVE_TELEGRAM_MODE:-monolith' in script
    assert 'SPARK_LIVE_TELEGRAM_MODE must be' in script
    assert 'setup_args+=(--external-telegram-ingress)' in script
    assert 'Using external Telegram ingress owner' in script


def test_live_docker_entrypoint_rejects_local_telegram_secrets_in_external_mode() -> None:
    script = (Path(__file__).resolve().parents[1] / "docker" / "live" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "looks_like_telegram_bot_token" in script
    assert "looks_like_telegram_admin_ids" in script
    assert "TELEGRAM_BOT_TOKEN looks like a real bot token" in script
    assert "TELEGRAM_ADMIN_IDS looks like real admin IDs" in script
    assert "Put the token only on spark-telegram-bot" in script
    assert "Put admin IDs only on spark-telegram-bot" in script


def test_live_docker_entrypoint_disables_os_autostart() -> None:
    script = (Path(__file__).resolve().parents[1] / "docker" / "live" / "entrypoint.sh").read_text(encoding="utf-8")
    assert "--no-autostart" in script
    assert "--no-start-now" in script


def test_live_vps_compose_uses_container_hardening() -> None:
    compose = (Path(__file__).resolve().parents[1] / "docker" / "live" / "docker-compose.vps.yml").read_text(encoding="utf-8")
    assert 'user: "1001:1001"' in compose
    assert "read_only: true" in compose
    assert "cap_drop:" in compose
    assert "- ALL" in compose
    assert "no-new-privileges:true" in compose
    assert "/tmp:rw,noexec,nosuid" in compose
    assert "./spark-data:/data/spark" in compose


def test_live_vps_env_example_has_placeholders_only() -> None:
    env = (Path(__file__).resolve().parents[1] / "docker" / "live" / "spark-live.env.example").read_text(encoding="utf-8")
    assert "SPARK_UI_API_KEY=replace-with-a-random-value" in env
    assert "SPARK_BRIDGE_API_KEY=replace-with-a-different-random-value" in env
    assert "TELEGRAM_BOT_TOKEN=" in env
    assert "ZAI_API_KEY=" in env
    assert "SPARK_LIVE_TELEGRAM_MODE=external" in env
