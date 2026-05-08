from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


ENTRYPOINT = Path(__file__).resolve().parents[1] / "docker" / "live" / "entrypoint.sh"


def bash_available() -> bool:
    try:
        result = subprocess.run(
            ["bash", "-lc", "set -euo pipefail; printf ok"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and result.stdout == "ok"


def read_entrypoint() -> str:
    return ENTRYPOINT.read_text(encoding="utf-8")


def test_live_docker_entrypoint_fails_closed_for_public_spawner() -> None:
    script = read_entrypoint()
    assert "umask 077" in script
    assert "is_public_spawner_bind" in script
    assert "SPARK_ALLOWED_HOSTS is required when Spawner binds publicly" in script
    assert "require_strong_secret SPARK_BRIDGE_API_KEY" in script
    assert "require_strong_secret SPARK_UI_API_KEY" in script
    assert "SPARK_BRIDGE_API_KEY and SPARK_UI_API_KEY must be different" in script
    assert "must contain hostnames only, with no scheme, path, wildcard, or port" in script


def test_live_docker_entrypoint_supports_external_telegram_ingress() -> None:
    script = read_entrypoint()
    assert 'SPARK_LIVE_TELEGRAM_MODE:-monolith' in script
    assert 'SPARK_LIVE_TELEGRAM_MODE must be' in script
    assert 'setup_args+=(--external-telegram-ingress)' in script
    assert 'Using external Telegram ingress owner' in script


def test_live_docker_entrypoint_rejects_local_telegram_secrets_in_external_mode() -> None:
    script = read_entrypoint()
    assert "looks_like_telegram_bot_token" in script
    assert "looks_like_telegram_admin_ids" in script
    assert "has_telegram_bot_token_env" in script
    assert "has_telegram_admin_ids_env" in script
    assert "TELEGRAM_BOT_TOKEN looks like a real bot token" in script
    assert "BOT_TOKEN looks like a real bot token" in script
    assert "TELEGRAM_ADMIN_IDS looks like real admin IDs" in script
    assert "ADMIN_TELEGRAM_IDS looks like real admin IDs" in script
    assert "Put the token only on spark-telegram-bot" in script
    assert "Put admin IDs only on spark-telegram-bot" in script
    assert "Scrubbing Telegram ingress env vars from Spark Live external mode." in script
    assert "unset TELEGRAM_BOT_TOKEN TELEGRAM_ADMIN_IDS BOT_TOKEN ADMIN_TELEGRAM_IDS" in script


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("TELEGRAM_BOT_TOKEN", "123456789:real-looking-token", "TELEGRAM_BOT_TOKEN looks like a real bot token"),
        ("BOT_TOKEN", "123456789:real-looking-token", "BOT_TOKEN looks like a real bot token"),
        ("TELEGRAM_ADMIN_IDS", "123456789", "TELEGRAM_ADMIN_IDS looks like real admin IDs"),
        ("ADMIN_TELEGRAM_IDS", "123456789", "ADMIN_TELEGRAM_IDS looks like real admin IDs"),
    ],
)
@pytest.mark.skipif(not bash_available(), reason="bash is required for executable entrypoint regression tests")
@pytest.mark.skipif(sys.platform == "win32", reason="entrypoint executable regression tests run under Linux bash in CI")
def test_live_docker_entrypoint_external_mode_rejects_telegram_env_before_setup(
    name: str, value: str, message: str
) -> None:
    env = os.environ.copy()
    for telegram_name in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_IDS", "BOT_TOKEN", "ADMIN_TELEGRAM_IDS"):
        env.pop(telegram_name, None)
    env.update(
        {
            "SPARK_LLM_PROVIDER": "zai",
            "SPARK_LIVE_PRIVILEGE_DROPPED": "1",
            "SPARK_LIVE_TELEGRAM_MODE": "external",
            name: value,
        }
    )

    result = subprocess.run(
        ["bash", "-s"],
        capture_output=True,
        env=env,
        input=read_entrypoint().replace("\r", ""),
        text=True,
        timeout=10,
    )

    assert result.returncode == 2
    assert message in result.stdout
    assert "Configuring Spark" not in result.stdout


def test_live_docker_entrypoint_disables_os_autostart() -> None:
    script = read_entrypoint()
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
