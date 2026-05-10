from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .modal import modal_auth_markers, modal_sdk_available
from .ssh import load_ssh_targets


def access_os_family(platform: str | None = None) -> str:
    value = platform or sys.platform
    if value == "darwin":
        return "macos"
    if value.startswith("win"):
        return "windows"
    if value.startswith("linux"):
        return "linux"
    return "unknown"


def spark_workspace_root(*, home: Path | None = None, env: dict[str, str] | None = None) -> Path:
    env_values = env or os.environ
    configured = env_values.get("SPARK_WORKSPACE_ROOT") or env_values.get("SPAWNER_WORKSPACE_ROOT")
    if configured:
        return Path(configured).expanduser()
    spark_home = home or Path(env_values.get("SPARK_HOME", Path.home() / ".spark")).expanduser()
    return spark_home / "workspaces"


def ensure_level4_workspace(*, home: Path | None = None, env: dict[str, str] | None = None) -> Path:
    root = spark_workspace_root(home=home, env=env)
    default_workspace = root / "default"
    default_workspace.mkdir(parents=True, exist_ok=True)
    return default_workspace


def docker_available() -> bool:
    return bool(shutil.which("docker"))


def docker_os_hint(family: str) -> str:
    if family == "macos":
        return "Spark can guide Docker Desktop for macOS when a task needs stronger isolation."
    if family == "windows":
        return "Spark can guide Docker Desktop with WSL on Windows when a task needs stronger isolation."
    if family == "linux":
        return "Spark can guide Docker Engine or Docker Desktop on Linux with distro-aware checks."
    return "Spark can guide Docker setup when this OS supports it."


def workspace_os_hint(family: str) -> str:
    if family == "macos":
        return "macOS default: Spark uses a workspace sandbox first, then adds Docker only when useful."
    if family == "windows":
        return "Windows default: Spark uses a workspace sandbox first, then guides Docker/WSL only when useful."
    if family == "linux":
        return "Linux default: Spark uses a workspace sandbox first, then guides Docker only when useful."
    return "Default: Spark uses a workspace sandbox first, then guides heavier sandboxes only when useful."


def goal_needs(goal: str, lane: str) -> bool:
    text = goal.lower()
    if lane == "docker":
        return any(word in text for word in ("docker", "container", "containerized", "isolated", "reproducible"))
    if lane == "ssh":
        return any(word in text for word in ("ssh", "remote machine", "remote server", "remote box", "vps"))
    if lane == "modal":
        return any(word in text for word in ("modal", "gpu", "cloud sandbox", "remote compute", "large job"))
    return False


def access_lane_payload(
    *,
    level: int = 4,
    goal: str = "",
    setup: bool = False,
    home: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env_values = env or os.environ
    family = access_os_family()
    workspace_root = spark_workspace_root(home=home, env=env_values)
    workspace_path = ensure_level4_workspace(home=home, env=env_values) if setup else workspace_root / "default"
    ssh_targets = load_ssh_targets(home=home)
    modal_auth = modal_auth_markers(home=home)
    modal_ready = modal_sdk_available() and bool(modal_auth.get("env_auth") or modal_auth.get("config_present"))
    docker_ready = docker_available()
    level5_enabled = str(env_values.get("SPARK_ALLOW_HIGH_AGENCY_WORKERS", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    lanes = [
        {
            "id": "spark_workspace",
            "label": "Spark Workspace Sandbox",
            "available": True,
            "setup_mode": "automatic",
            "spark_cli_action": "spark access setup",
            "user_message": f"Spark can work safely inside {workspace_path}.",
            "os_hint": workspace_os_hint(family),
        },
        {
            "id": "docker",
            "label": "Docker Sandbox",
            "available": docker_ready,
            "setup_mode": "automatic" if docker_ready else "guided",
            "spark_cli_action": "spark access setup --with docker" if docker_ready else "spark access setup --with docker",
            "user_message": "Docker is ready for stronger isolation." if docker_ready else "Docker is optional; Spark can guide setup when a task needs it.",
            "os_hint": docker_os_hint(family),
        },
        {
            "id": "ssh",
            "label": "SSH Remote Sandbox",
            "available": bool(ssh_targets),
            "setup_mode": "automatic" if ssh_targets else "guided",
            "spark_cli_action": "spark sandbox ssh list" if ssh_targets else "spark sandbox ssh add <name> --host <host> --user <user> --identity-file <path>",
            "user_message": "A trusted remote target is configured." if ssh_targets else "SSH is optional; connect a trusted remote machine only when needed.",
        },
        {
            "id": "modal",
            "label": "Modal Cloud Sandbox",
            "available": modal_ready,
            "setup_mode": "automatic" if modal_ready else "guided",
            "spark_cli_action": "spark sandbox modal doctor" if modal_ready else "spark sandbox modal doctor",
            "user_message": "Modal is ready for bounded cloud sandbox work." if modal_ready else "Modal is optional; connect it only for cloud compute jobs.",
        },
    ]

    recommended_id = "spark_workspace"
    if level >= 5 and level5_enabled:
        recommended_id = "level5_operator"
    elif goal_needs(goal, "modal") and modal_ready:
        recommended_id = "modal"
    elif goal_needs(goal, "ssh") and ssh_targets:
        recommended_id = "ssh"
    elif goal_needs(goal, "docker") and docker_ready:
        recommended_id = "docker"

    if level >= 5:
        lanes.insert(
            0,
            {
                "id": "level5_operator",
                "label": "Whole-Computer Operator Mode",
                "available": level5_enabled,
                "setup_mode": "guided" if level5_enabled else "blocked",
                "spark_cli_action": "spark access setup --level 5",
                "user_message": (
                    "Whole-computer mode is enabled, but Spark should still prefer a sandbox."
                    if level5_enabled
                    else "Whole-computer mode is blocked until high-agency guardrails are explicitly enabled."
                ),
            },
        )

    for lane in lanes:
        lane["recommended"] = lane["id"] == recommended_id
    recommended = next((lane for lane in lanes if lane["recommended"]), lanes[0])
    if recommended.get("available") is False:
        recommended = next(lane for lane in lanes if lane["id"] == "spark_workspace")
        recommended["recommended"] = True

    return {
        "ok": True,
        "access_level": level,
        "os_family": family,
        "workspace_root": str(workspace_root),
        "workspace_path": str(workspace_path),
        "setup_ran": setup,
        "recommended": recommended,
        "lanes": lanes,
        "next": recommended["spark_cli_action"],
    }

