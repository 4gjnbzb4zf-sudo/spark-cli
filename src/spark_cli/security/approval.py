from __future__ import annotations

import hashlib
import re
import shlex
from dataclasses import asdict, dataclass
from typing import Literal


ApprovalClass = Literal[
    "none",
    "destructive_filesystem",
    "git_history_mutation",
    "credential_mutation",
    "external_publish",
    "process_autostart_mutation",
    "network_exfiltration",
    "identity_access_mutation",
    "high_cost_execution",
]
ApprovalRisk = Literal["none", "low", "medium", "high", "critical"]


@dataclass(frozen=True)
class CommandContext:
    surface: str = "cli"
    hosted: bool = False
    non_interactive: bool = False


@dataclass(frozen=True)
class ApprovalDecision:
    action_class: ApprovalClass
    risk: ApprovalRisk
    requires_approval: bool
    approval_mode: str
    reason: str
    target_display: str
    command_digest: str
    confirmation_phrase: str
    surface: str = "cli"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


SECRET_LIKE_PATTERN = re.compile(
    r"(?i)(sk-[A-Za-z0-9_-]{8,}|[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}|\d{5,}:[A-Za-z0-9_-]{20,})"
)


def _digest_command(argv: list[str]) -> str:
    redacted = [SECRET_LIKE_PATTERN.sub("[REDACTED]", part) for part in argv]
    return hashlib.sha256("\0".join(redacted).encode("utf-8")).hexdigest()


def _lower_parts(argv: list[str]) -> list[str]:
    return [part.lower() for part in argv]


def _contains_any(parts: list[str], values: set[str]) -> bool:
    return any(part in values for part in parts)


def _target_after(parts: list[str], command_names: set[str]) -> str:
    for index, part in enumerate(parts):
        if part.lower() in command_names and index + 1 < len(parts):
            for candidate in parts[index + 1 :]:
                if not candidate.startswith("-"):
                    return candidate
    return ""


def _decision(
    argv: list[str],
    context: CommandContext,
    action_class: ApprovalClass,
    risk: ApprovalRisk,
    reason: str,
    *,
    target_display: str = "",
    confirmation_phrase: str = "",
) -> ApprovalDecision:
    requires = action_class != "none"
    phrase = confirmation_phrase
    if requires and not phrase:
        noun = target_display or action_class.replace("_", " ")
        phrase = f"approve {noun}".strip().lower()[:80]
    return ApprovalDecision(
        action_class=action_class,
        risk=risk,
        requires_approval=requires,
        approval_mode="interactive" if requires else "none",
        reason=reason,
        target_display=target_display,
        command_digest=_digest_command(argv),
        confirmation_phrase=phrase,
        surface=context.surface,
    )


def parse_command_text(command: str) -> list[str]:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def approval_required_for_command(argv: list[str], context: CommandContext | None = None) -> ApprovalDecision:
    ctx = context or CommandContext()
    parts = [part for part in argv if part != "--"]
    lowered = _lower_parts(parts)
    if not lowered:
        return _decision(parts, ctx, "none", "none", "Empty command.")

    joined = " ".join(lowered)
    first = lowered[0]
    second = lowered[1] if len(lowered) > 1 else ""

    if first == "spark" and second in {"status", "guide"}:
        return _decision(parts, ctx, "none", "none", f"`spark {second}` is read-only.")
    if first == "spark" and second == "verify" and "--deep" not in lowered:
        return _decision(parts, ctx, "none", "none", "`spark verify` without --deep is report-only.")
    if first == "spark" and lowered[1:3] == ["providers", "status"]:
        return _decision(parts, ctx, "none", "none", "`spark providers status` is read-only.")

    destructive_bins = {"rm", "rmdir", "del", "remove-item", "erase"}
    if first in destructive_bins or _contains_any(lowered, destructive_bins):
        recursive_or_force = _contains_any(lowered, {"-rf", "-fr", "-r", "--recursive", "-recurse", "-force", "/s"})
        target = _target_after(parts, destructive_bins)
        return _decision(
            parts,
            ctx,
            "destructive_filesystem",
            "critical" if recursive_or_force else "high",
            "Command can delete local files or directories.",
            target_display=target,
            confirmation_phrase=f"delete {target}".strip().lower()[:80] if target else "approve delete",
        )

    if first == "git" and (
        "filter-repo" in lowered
        or "--force" in lowered
        or "--force-with-lease" in lowered
        or "-f" in lowered and second in {"push", "tag"}
        or second in {"rebase", "reset"}
    ):
        return _decision(
            parts,
            ctx,
            "git_history_mutation",
            "critical",
            "Command can rewrite published history or discard local work.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve git history mutation",
        )

    if first == "spark" and second == "secrets" and _contains_any(lowered, {"delete", "get", "export", "--reveal"}):
        return _decision(
            parts,
            ctx,
            "credential_mutation",
            "high",
            "Command can reveal, export, delete, or mutate stored credentials.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve secret access",
        )

    if first in {"railway", "vercel", "flyctl"} and _contains_any(lowered, {"up", "deploy", "redeploy"}):
        return _decision(
            parts,
            ctx,
            "external_publish",
            "high",
            "Command can publish or redeploy hosted infrastructure.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve hosted deploy",
        )
    if (first == "git" and second == "push") or (first == "npm" and second == "publish") or joined.startswith("gh release create"):
        return _decision(
            parts,
            ctx,
            "external_publish",
            "high",
            "Command can publish code, packages, releases, or tags outside this machine.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve publish",
        )

    if first == "spark" and second == "autostart":
        return _decision(
            parts,
            ctx,
            "process_autostart_mutation",
            "medium",
            "Command changes login/startup behavior for this computer or host.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve autostart change",
        )
    if first in {"schtasks", "setx", "reg", "systemctl", "launchctl"}:
        return _decision(
            parts,
            ctx,
            "process_autostart_mutation",
            "high",
            "Command can change OS services, registry, shell profile, or startup behavior.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve system startup change",
        )

    if first == "spark" and second == "doctor" and "--include-logs" in lowered:
        return _decision(
            parts,
            ctx,
            "network_exfiltration",
            "medium",
            "Doctor logs may be sent to a configured LLM provider after redaction.",
            target_display="spark doctor llm --include-logs",
            confirmation_phrase="approve redacted log sharing",
        )
    if first in {"curl", "wget"} and _contains_any(lowered, {"-t", "--upload-file", "-f", "--form", "--data", "--data-binary"}):
        return _decision(
            parts,
            ctx,
            "network_exfiltration",
            "medium",
            "Command may upload local data to a network endpoint.",
            target_display=parts[0],
            confirmation_phrase="approve network upload",
        )

    if first == "spark" and (
        second == "telegram"
        or ("--admin-telegram-ids" in lowered)
        or ("--bot-token" in lowered)
        or ("--access" in lowered)
    ):
        return _decision(
            parts,
            ctx,
            "identity_access_mutation",
            "high",
            "Command changes Telegram, identity, or operator access configuration.",
            target_display=" ".join(parts[:4]),
            confirmation_phrase="approve access change",
        )

    if first == "spark" and second == "verify" and "--deep" in lowered:
        return _decision(
            parts,
            ctx,
            "high_cost_execution",
            "medium",
            "Deep verification can start live provider or mission smoke tests.",
            target_display="spark verify --deep",
            confirmation_phrase="approve deep verification",
        )

    return _decision(parts, ctx, "none", "none", "No sensitive action class matched.")
