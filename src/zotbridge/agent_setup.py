from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .config import Settings
from .daemon import current_daemon_status
from .qmd import QmdClient
from .utils import ensure_dir


SERVER_NAME = "zotbridge"
SUPPORTED_SETUP_TARGETS = (
    "all",
    "codex",
    "claude-code",
    "claude-desktop",
    "cursor",
    "gemini",
    "cline",
    "antigravity",
    "opencode",
    "windsurf",
    "json",
)
SUPPORTED_SKILL_TARGETS = (
    "cline",
    "antigravity",
    "codex",
    "opencode",
    "claude-code",
    "claude-desktop",
    "gemini-cli",
)
BULK_SKILL_TARGETS = tuple(target for target in SUPPORTED_SKILL_TARGETS if target != "claude-desktop")
SUPPORTED_SKILL_VARIANTS = ("general", "daemon")
USER_SCOPE_ONLY_TARGETS = {"codex", "claude-desktop", "gemini", "cline", "antigravity", "opencode", "windsurf"}
PROJECT_OR_USER_TARGETS = {"cursor", "claude-code"}
PROJECT_ONLY_TARGETS: set[str] = set()
TARGET_ALIASES: dict[str, str] = {}


def normalize_target_name(target: str) -> str:
    return TARGET_ALIASES.get(target, target)


def _env_map(settings: Settings) -> dict[str, str]:
    env: dict[str, str] = {}
    if settings.api_key:
        env["ZOTBRIDGE_API_KEY"] = settings.api_key
    if settings.state_dir:
        env["ZOTBRIDGE_STATE_DIR"] = str(settings.resolved_state_dir())
    return env


def mcp_stdio_spec(settings: Settings) -> dict[str, Any]:
    spec: dict[str, Any] = {
        "command": "zotbridge-mcp",
        "args": ["--profile", settings.selected_profile] if settings.selected_profile else [],
    }
    env = _env_map(settings)
    if env:
        spec["env"] = env
    return spec


def mcp_json_document(settings: Settings) -> dict[str, Any]:
    return {"mcpServers": {SERVER_NAME: mcp_stdio_spec(settings)}}


def _quote_toml(value: str) -> str:
    return json.dumps(value)


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_quote_toml(value) for value in values) + "]"


def _codex_block(settings: Settings) -> str:
    spec = mcp_stdio_spec(settings)
    lines = [
        f"[mcp_servers.{SERVER_NAME}]",
        f'command = {_quote_toml(str(spec["command"]))}',
        f'args = {_toml_array([str(arg) for arg in spec.get("args") or []])}',
    ]
    env = spec.get("env") or {}
    if env:
        lines.append("")
        lines.append(f"[mcp_servers.{SERVER_NAME}.env]")
        for key in sorted(env):
            lines.append(f"{key} = {_quote_toml(str(env[key]))}")
    return "\n".join(lines) + "\n"


def _remove_codex_server_block(text: str) -> str:
    lines = text.splitlines()
    kept: list[str] = []
    skipping = False
    prefix = f"[mcp_servers.{SERVER_NAME}"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if stripped.startswith(prefix):
                skipping = True
                continue
            if skipping:
                skipping = False
        if not skipping:
            kept.append(line)
    result = "\n".join(kept).strip()
    return result + ("\n" if result else "")


def _write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _merge_mcp_server(payload: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    servers = dict(merged.get("mcpServers") or {})
    servers[SERVER_NAME] = spec
    merged["mcpServers"] = servers
    return merged


def _remove_mcp_server(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    servers = dict(merged.get("mcpServers") or {})
    servers.pop(SERVER_NAME, None)
    if servers:
        merged["mcpServers"] = servers
    else:
        merged.pop("mcpServers", None)
    return merged


def _opencode_mcp_spec(settings: Settings) -> dict[str, Any]:
    spec = mcp_stdio_spec(settings)
    return {
        "type": "local",
        "command": [str(spec["command"]), *[str(arg) for arg in spec.get("args") or []]],
        "enabled": True,
        "environment": {key: str(value) for key, value in (spec.get("env") or {}).items()},
    }


def _merge_opencode_mcp(payload: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    if "$schema" not in merged:
        merged["$schema"] = "https://opencode.ai/config.json"
    mcp = dict(merged.get("mcp") or {})
    mcp[SERVER_NAME] = spec
    merged["mcp"] = mcp
    return merged


def _remove_opencode_mcp(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    mcp = dict(merged.get("mcp") or {})
    mcp.pop(SERVER_NAME, None)
    if mcp:
        merged["mcp"] = mcp
    else:
        merged.pop("mcp", None)
    return merged


def _setup_targets_for_scope(scope: str) -> tuple[str, ...]:
    if scope == "user":
        return tuple(
            target
            for target in SUPPORTED_SETUP_TARGETS
            if target not in {"all", "json"} and target not in PROJECT_ONLY_TARGETS
        )
    if scope == "project":
        return tuple(
            target
            for target in SUPPORTED_SETUP_TARGETS
            if target not in {"all", "json"} and target not in USER_SCOPE_ONLY_TARGETS
        )
    raise ValueError(f"Unsupported setup scope: {scope}")


def setup_target_path(
    target: str,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    scope: str = "project",
) -> Path | None:
    target = normalize_target_name(target)
    cwd = (cwd or Path.cwd()).resolve()
    home = (home or Path.home()).expanduser()
    if target in USER_SCOPE_ONLY_TARGETS and scope != "user":
        raise ValueError(f"{target} only supports --scope user")
    if target in PROJECT_ONLY_TARGETS and scope != "project":
        raise ValueError(f"{target} only supports --scope project")
    if target == "codex":
        return home / ".codex" / "config.toml"
    if target == "claude-code":
        if scope == "user":
            return home / ".claude" / "settings.json"
        return cwd / ".mcp.json"
    if target == "claude-desktop":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if target == "cursor":
        if scope == "user":
            return home / ".cursor" / "mcp.json"
        return cwd / ".cursor" / "mcp.json"
    if target == "gemini":
        return home / ".gemini" / "settings.json"
    if target == "cline":
        return home / ".cline" / "data" / "settings" / "cline_mcp_settings.json"
    if target == "antigravity":
        return home / ".gemini" / "antigravity" / "mcp_config.json"
    if target == "opencode":
        return home / ".config" / "opencode" / "opencode.json"
    if target == "windsurf":
        return home / ".codeium" / "windsurf" / "mcp_config.json"
    if target == "json":
        return None
    raise ValueError(f"Unsupported setup target: {target}")


def install_mcp_setup(
    target: str,
    settings: Settings,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    scope: str = "project",
) -> dict[str, Any]:
    target = normalize_target_name(target)
    if target == "all":
        return {
            "scope": scope,
            "results": [install_mcp_setup(name, settings, cwd=cwd, home=home, scope=scope) for name in _setup_targets_for_scope(scope)],
        }
    if target not in SUPPORTED_SETUP_TARGETS:
        raise ValueError(f"Unsupported setup target: {target}")
    spec = mcp_stdio_spec(settings)
    if target == "json":
        return {
            "target": target,
            "written": False,
            "path": None,
            "config": mcp_json_document(settings),
        }
    path = setup_target_path(target, cwd=cwd, home=home, scope=scope)
    assert path is not None
    if target == "codex":
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        cleaned = _remove_codex_server_block(existing).rstrip()
        block = _codex_block(settings).strip()
        content = (cleaned + "\n\n" + block).strip() + "\n"
        _write_text(path, content)
    elif target == "opencode":
        payload = _read_json_file(path)
        payload = _merge_opencode_mcp(payload, _opencode_mcp_spec(settings))
        _write_json_file(path, payload)
    else:
        payload = _read_json_file(path)
        payload = _merge_mcp_server(payload, spec)
        _write_json_file(path, payload)
    return {
        "target": target,
        "written": True,
        "path": str(path),
        "config": spec if target != "codex" else {"toml_server": SERVER_NAME},
        "scope": scope,
    }


def remove_mcp_setup(
    target: str,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    scope: str = "project",
) -> dict[str, Any]:
    target = normalize_target_name(target)
    if target == "all":
        return {
            "scope": scope,
            "results": [remove_mcp_setup(name, cwd=cwd, home=home, scope=scope) for name in _setup_targets_for_scope(scope)],
        }
    if target not in SUPPORTED_SETUP_TARGETS or target == "json":
        raise ValueError(f"Unsupported removable setup target: {target}")
    path = setup_target_path(target, cwd=cwd, home=home, scope=scope)
    assert path is not None
    if not path.exists():
        return {"target": target, "removed": False, "path": str(path), "reason": "config_not_found"}
    if target == "codex":
        cleaned = _remove_codex_server_block(path.read_text(encoding="utf-8"))
        _write_text(path, cleaned)
    elif target == "opencode":
        payload = _remove_opencode_mcp(_read_json_file(path))
        _write_json_file(path, payload)
    else:
        payload = _remove_mcp_server(_read_json_file(path))
        _write_json_file(path, payload)
    return {"target": target, "removed": True, "path": str(path), "scope": scope}


def inspect_setup_target(
    target: str,
    settings: Settings,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    scope: str = "project",
) -> dict[str, Any]:
    target = normalize_target_name(target)
    path = setup_target_path(target, cwd=cwd, home=home, scope=scope)
    installed = False
    if path and path.exists():
        if target == "codex":
            installed = f"[mcp_servers.{SERVER_NAME}]" in path.read_text(encoding="utf-8")
        elif target == "opencode":
            payload = _read_json_file(path)
            installed = SERVER_NAME in (payload.get("mcp") or {})
        else:
            payload = _read_json_file(path)
            installed = SERVER_NAME in (payload.get("mcpServers") or {})
    return {
        "target": target,
        "path": str(path) if path else None,
        "installed": installed,
        "scope": scope,
        "config": mcp_json_document(settings) if target == "json" else mcp_stdio_spec(settings),
    }


def setup_list(settings: Settings, *, cwd: Path | None = None, home: Path | None = None) -> list[dict[str, Any]]:
    return [
        inspect_setup_target("codex", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("claude-code", settings, cwd=cwd, home=home, scope="project"),
        inspect_setup_target("claude-code", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("claude-desktop", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("cursor", settings, cwd=cwd, home=home, scope="project"),
        inspect_setup_target("cursor", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("gemini", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("cline", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("antigravity", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("opencode", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("windsurf", settings, cwd=cwd, home=home, scope="user"),
        inspect_setup_target("json", settings, cwd=cwd, home=home, scope="project"),
    ]


def _target_label(target: str) -> str:
    labels = {
        "codex": "Codex",
        "claude-code": "Claude Code",
        "claude-desktop": "Claude Desktop",
        "gemini-cli": "Gemini CLI",
        "cline": "Cline",
        "antigravity": "Antigravity",
        "opencode": "OpenCode",
    }
    return labels.get(target, target)


def _variant_label(variant: str) -> str:
    labels = {
        "general": "general runtime",
        "daemon": "daemon runtime",
    }
    return labels.get(variant, variant)


def _target_specific_notes(target: str) -> list[str]:
    if target == "claude-desktop":
        return [
            "- This skill is uploaded manually into Claude Desktop or claude.ai; it does not configure MCP by itself.",
            "- Use the HTTP API when Claude can reach a running `zotbridge-daemon` process directly.",
            "- Use MCP only after the separate Claude Desktop MCP config has been installed.",
        ]
    if target in {"codex", "claude-code", "cline", "antigravity", "opencode"}:
        return [
            "- Prefer MCP for exact reads and mutations when the server is installed.",
            "- Prefer the HTTP API for stable structured integrations or remote daemon access.",
        ]
    if target == "gemini-cli":
        return [
            "- Prefer the HTTP API for direct structured integrations when available.",
            "- Use MCP when the Gemini environment is already configured for MCP tool calls.",
        ]
    return []


def _variant_specific_notes(variant: str) -> list[str]:
    if variant == "daemon":
        return [
            "- Assume a service deployment with no Zotero Desktop dependency.",
            "- Prefer the daemon HTTP API as the primary integration surface and MCP as a client convenience layer.",
            "- Treat remote sync, runtime observability, and background jobs as normal operational concerns.",
        ]
    return [
        "- Use the canonical zotbridge store as the primary working state.",
        "- Use Zotero Web API sync for user and group libraries.",
        "- Do not assume local Zotero Desktop paths, schemas, or helper runtimes are available.",
    ]


def _skill_frontmatter(target: str, *, variant: str) -> str:
    target_label = _target_label(target)
    variant_label = _variant_label(variant)
    description = (
        f"Use this skill when working with the zotbridge CLI, HTTP API, or MCP runtime from "
        f"{target_label}. Active variant: {variant_label}."
    )
    return f"---\nname: {SERVER_NAME}\ndescription: {description}\n---\n\n"


def skill_text(target: str, *, variant: str = "general") -> str:
    target = normalize_target_name(target)
    if target not in SUPPORTED_SKILL_TARGETS:
        raise ValueError(f"Unsupported skill target: {target}")
    if variant not in SUPPORTED_SKILL_VARIANTS:
        raise ValueError(f"Unsupported skill variant: {variant}")
    target_label = _target_label(target)
    variant_label = _variant_label(variant)
    target_notes = "\n".join(_target_specific_notes(target))
    if target_notes:
        target_notes = f"\nTarget-specific notes:\n{target_notes}\n"
    variant_notes = "\n".join(_variant_specific_notes(variant))
    if variant_notes:
        variant_notes = f"\nVariant-specific notes:\n{variant_notes}\n"
    frontmatter = _skill_frontmatter(target, variant=variant)
    bundled_assets = ""
    if target == "claude-desktop":
        bundled_assets = """
Bundled references:
- `references/interface-selection.md` expands the routing model, variant posture, and target-specific notes.
- `references/workflow.md` gives the operational workflow and recovery order.
- `references/common-recipes.md` collects exact command patterns and daemon endpoints.
"""
    return f"""{frontmatter}# zotbridge

Use this when working with zotbridge through the `zotbridge` CLI, HTTP API, or MCP runtime from {target_label}.
Active skill variant: `{variant}` ({variant_label}).

Core priorities:
- Prefer the canonical zotbridge store and daemon runtime.
- Use Zotero Web API sync for personal and group libraries.
- Treat qmd semantic search as derived from library state, not as authoritative metadata.
- Use qmd as the discovery layer: search ranks exported Zotero Markdown by meaning, and `qmd get` recovers the exact exported source behind a hit for auditable context.
- Use recovery snapshots before large sync, restore, or mutation workflows.
- Use direct sync and conflict flows instead of retrying remote mutations blindly.

Decision table:
- Exploratory retrieval, topic discovery, related-work lookup, RAG context building:
  - Use qmd semantic search, then `qmd get` to recover the exported source behind useful hits.
- Exact metadata lookup with a known library ID, item key, or collection key:
  - Use direct API, CLI, or MCP reads.
- Create, update, delete, sync, or conflict resolution:
  - Use direct mutation and sync commands, never qmd.
- Stable structured integration with a reachable daemon:
  - Prefer the HTTP API.
- MCP-native tool calling environment:
  - Prefer MCP when the client already handles tool use well.

Routing policy:
- Use qmd semantic search for:
  - finding relevant papers on a topic
  - retrieving related sources from natural-language prompts
  - summarizing themes across a library
  - building retrieval context before writing
- Use `qmd get` after search when a snippet is not enough and you need the exported source that produced a hit.
- Use direct reads through API, CLI, or MCP for:
  - exact metadata inspection
  - exact list/get operations
  - authoritative current state
  - keyed parent/child traversal
- Use direct mutation and sync commands for:
  - item and collection create/update/delete
  - sync discover, pull, push
  - conflict resolution
- Use recovery commands for:
  - snapshots before high-risk changes
  - restore plans before executing a restore
  - snapshot verification before relying on backups
- If you must use the CLI from an agent or script, prefer the strict `zotbridge raw ...` namespace over the human-oriented top-level commands.
- Prefer the HTTP API over MCP when the agent can call HTTP directly and wants stable structured integration.
- Prefer MCP when the client is already MCP-native and tool-use ergonomics are better there.
- Do not use qmd semantic search when the task already names exact objects or requires authoritative current metadata.
{bundled_assets}
{variant_notes}
{target_notes}
Recommended workflow:
1. Start with `zotbridge capabilities` or `zotbridge daemon status` when runtime shape is unclear.
2. If remote libraries are involved, run `zotbridge raw sync discover` and `zotbridge raw sync pull --library <library_id>` before deeper work when you are driving the CLI programmatically.
3. Choose retrieval mode:
   - qmd for exploratory retrieval
   - API/MCP/CLI for exact reads
4. For writes, use direct mutation commands and then `zotbridge raw sync push --library <library_id>` when remote sync is required.
5. If a write fails, inspect `zotbridge raw sync conflicts --library <library_id>` before retrying.

Common recipes:
- Find papers about a topic:
  - `zotbridge qmd query "papers about retrieval augmented generation"`
- Recover source context from a qmd hit:
  - `zotbridge qmd get "<target-from-result>"`
- Fetch an exact item:
  - use API or MCP item-get tools with the known `library_id` and `item_key`
- Sync a remote library before exact reads:
  - `zotbridge raw sync discover`
  - `zotbridge raw sync pull --library user:123456`
- Resolve remote write issues:
  - `zotbridge raw sync conflicts --library user:123456`
- Daemon workflow:
  - `zotbridge-daemon serve --host 127.0.0.1 --port 23119 --sync-interval 300`
- Daemon observability:
  - `curl -s http://127.0.0.1:23119/daemon/runtime`
  - `curl -s http://127.0.0.1:23119/daemon/jobs`
  - `curl -s http://127.0.0.1:23119/metrics`

Anti-patterns:
- Do not scan exported markdown directly when qmd can answer the retrieval question.
- Do not use qmd for exact authoritative metadata lookups.
- Do not mutate Zotero Desktop files or SQLite databases through this package.
- Do not use native client extensions; this package ships skills plus MCP/HTTP integration.
- Do not retry failed remote writes blindly; inspect conflicts first.

High-value commands:
- `zotbridge capabilities`
- `zotbridge daemon status`
- `zotbridge raw sync discover`
- `zotbridge raw sync pull --library <library_id>`
- `zotbridge raw sync push --library <library_id>`
- `zotbridge raw sync conflicts --library <library_id>`
- `zotbridge qmd query "<topic>"`
- `zotbridge qmd get "<target-from-result>"`
- `zotbridge recovery snapshot-create --reason before-large-sync`

Useful daemon endpoints:
- `/health`
- `/capabilities`
- `/daemon/status`
- `/daemon/runtime`
- `/daemon/jobs`
- `/metrics`
"""


def _claude_desktop_reference_documents(*, variant: str) -> dict[str, str]:
    variant_label = _variant_label(variant)
    variant_notes = "\n".join(_variant_specific_notes(variant))
    target_notes = "\n".join(_target_specific_notes("claude-desktop"))
    interface_selection = f"""# Interface Selection

Active skill variant: `{variant}` ({variant_label}).

Decision table:
- Exploratory retrieval, topic discovery, related-work lookup, RAG context building:
  - Use qmd semantic search, then `qmd get` to recover the exported source behind useful hits.
- Exact metadata lookup with a known library ID, item key, or collection key:
  - Use direct API, CLI, or MCP reads.
- Create, update, delete, sync, or conflict resolution:
  - Use direct mutation and sync commands, never qmd.
- Stable structured integration with a reachable daemon:
  - Prefer the HTTP API.
- MCP-native tool calling environment:
  - Prefer MCP when the client already handles tool use well.

Variant-specific notes:
{variant_notes}

Target-specific notes:
{target_notes}
"""
    workflow = """# Workflow

Recommended workflow:
1. Start with `zotbridge capabilities` or `zotbridge daemon status` when runtime shape is unclear.
2. If remote libraries are involved, run `zotbridge raw sync discover` and `zotbridge raw sync pull --library <library_id>` before deeper work.
3. Choose retrieval mode:
   - qmd for exploratory retrieval
   - qmd get for source recovery from a search hit
   - API/MCP/CLI for exact reads
4. For writes, use direct mutation commands and then `zotbridge raw sync push --library <library_id>` when remote sync is required.
5. If a write fails, inspect `zotbridge raw sync conflicts --library <library_id>` before retrying.
"""
    common_recipes = """# Common Recipes

- Find papers about a topic:
  - `zotbridge qmd query "papers about retrieval augmented generation"`
- Recover source context from a qmd hit:
  - `zotbridge qmd get "<target-from-result>"`
- Fetch an exact item:
  - use API or MCP item-get tools with the known `library_id` and `item_key`
- Sync a remote library before exact reads:
  - `zotbridge raw sync discover`
  - `zotbridge raw sync pull --library user:123456`
- Resolve remote write issues:
  - `zotbridge raw sync conflicts --library user:123456`
- Daemon workflow:
  - `zotbridge-daemon serve --host 127.0.0.1 --port 23119 --sync-interval 300`

Anti-patterns:
- Do not scan exported markdown directly when qmd can answer the retrieval question.
- Do not use qmd for exact authoritative metadata lookups.
- Do not mutate Zotero Desktop files or SQLite databases through this package.
"""
    return {
        "references/interface-selection.md": interface_selection,
        "references/workflow.md": workflow,
        "references/common-recipes.md": common_recipes,
    }


def skill_target_path(target: str, *, home: Path | None = None, variant: str = "general") -> Path:
    target = normalize_target_name(target)
    if target not in SUPPORTED_SKILL_TARGETS:
        raise ValueError(f"Unsupported skill target: {target}")
    if variant not in SUPPORTED_SKILL_VARIANTS:
        raise ValueError(f"Unsupported skill variant: {variant}")
    home = (home or Path.home()).expanduser()
    if target == "codex":
        return home / ".codex" / "skills" / SERVER_NAME / "SKILL.md"
    if target == "claude-code":
        return home / ".claude" / "skills" / SERVER_NAME / "SKILL.md"
    if target == "claude-desktop":
        suffix = "" if variant == "general" else f"-{variant}"
        return home / "Desktop" / f"{SERVER_NAME}-claude-desktop{suffix}-skill.zip"
    if target == "gemini-cli":
        return home / ".gemini" / "skills" / SERVER_NAME / "SKILL.md"
    if target == "cline":
        return home / ".cline" / "skills" / SERVER_NAME / "SKILL.md"
    if target == "antigravity":
        return home / ".gemini" / "antigravity" / "skills" / SERVER_NAME / "SKILL.md"
    if target == "opencode":
        return home / ".config" / "opencode" / "skill" / SERVER_NAME / "SKILL.md"
    raise ValueError(f"Unsupported skill target: {target}")


def _claude_desktop_upload_instructions(path: Path) -> list[str]:
    return [
        f"Find the generated skill archive at: {path}",
        "In Claude Desktop, open the Skills section and upload the archive.",
        "You can also upload the same archive in the Claude web app on claude.ai.",
    ]


def _claude_desktop_archive_contents(*, variant: str) -> list[str]:
    contents = ["SKILL.md"]
    contents.extend(sorted(_claude_desktop_reference_documents(variant=variant)))
    return contents


def _write_claude_desktop_skill_archive(path: Path, *, variant: str) -> None:
    ensure_dir(path.parent)
    skill_body = skill_text("claude-desktop", variant=variant)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("SKILL.md", skill_body)
        for archive_path, body in sorted(_claude_desktop_reference_documents(variant=variant).items()):
            zf.writestr(archive_path, body)


def install_skill(
    target: str,
    *,
    home: Path | None = None,
    variant: str = "general",
) -> dict[str, Any]:
    target = normalize_target_name(target)
    if target not in SUPPORTED_SKILL_TARGETS:
        raise ValueError(f"Unsupported skill target: {target}")
    if variant not in SUPPORTED_SKILL_VARIANTS:
        raise ValueError(f"Unsupported skill variant: {variant}")
    path = skill_target_path(target, home=home, variant=variant)
    if target == "claude-desktop":
        _write_claude_desktop_skill_archive(path, variant=variant)
        return {
            "target": target,
            "variant": variant,
            "installed": True,
            "path": str(path),
            "format": "zip",
            "instructions": _claude_desktop_upload_instructions(path),
        }
    _write_text(path, skill_text(target, variant=variant))
    return {"target": target, "variant": variant, "installed": True, "path": str(path)}


def install_skill_set(
    target: str,
    *,
    home: Path | None = None,
    variant: str = "general",
) -> list[dict[str, Any]]:
    target = normalize_target_name(target)
    if target == "all":
        targets = BULK_SKILL_TARGETS
    elif target in SUPPORTED_SKILL_TARGETS:
        targets = (target,)
    else:
        raise ValueError(f"Unsupported skill target: {target}")
    return [install_skill(name, home=home, variant=variant) for name in targets]


def installed_skill_targets(*, home: Path | None = None, variant: str = "general") -> list[str]:
    return [
        target
        for target in BULK_SKILL_TARGETS
        if skill_target_path(target, home=home, variant=variant).exists()
    ]


def refresh_installed_integrations(
    settings: Settings,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
    variant: str = "general",
) -> dict[str, Any]:
    refreshed_skills = [
        install_skill(target, home=home, variant=variant)
        for target in installed_skill_targets(home=home, variant=variant)
    ]
    return {"skills": refreshed_skills}


def export_skill(
    target: str,
    *,
    home: Path | None = None,
    variant: str = "general",
) -> dict[str, Any]:
    target = normalize_target_name(target)
    if variant not in SUPPORTED_SKILL_VARIANTS:
        raise ValueError(f"Unsupported skill variant: {variant}")
    if target == "claude-desktop":
        path = skill_target_path(target, home=home, variant=variant)
        _write_claude_desktop_skill_archive(path, variant=variant)
        return {
            "target": target,
            "variant": variant,
            "path": str(path),
            "content": skill_text(target, variant=variant),
            "format": "zip",
            "archive_contents": _claude_desktop_archive_contents(variant=variant),
            "instructions": _claude_desktop_upload_instructions(path),
        }
    return {"target": target, "variant": variant, "content": skill_text(target, variant=variant)}


def doctor_report(
    settings: Settings,
    *,
    cwd: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    daemon = current_daemon_status(settings)
    return {
        "cli": {
            "zotbridge": shutil.which("zotbridge"),
            "zotbridge_mcp": shutil.which("zotbridge-mcp"),
            "zotbridge_daemon": shutil.which("zotbridge-daemon"),
            "qmd": shutil.which("qmd"),
        },
        "settings": {
            "state_dir": str(settings.resolved_state_dir()),
            "canonical_db": str(settings.resolved_canonical_db()),
            "mirror_db": str(settings.resolved_mirror_db()),
            "file_cache_dir": str(settings.resolved_file_cache_dir()),
            "export_dir": str(settings.resolved_export_dir()),
            "recovery_snapshot_dir": str(settings.resolved_recovery_snapshot_dir()),
            "recovery_temp_dir": str(settings.resolved_recovery_temp_dir()),
            "recovery_auto_snapshots": bool(settings.recovery_auto_snapshots),
            "api_key_configured": bool(settings.api_key),
        },
        "daemon": daemon.to_dict(),
        "qmd": QmdClient(settings).doctor(),
        "setup_targets": setup_list(settings, cwd=cwd, home=home),
        "skill_targets": [
            {"target": target, "install_supported": True, "variants": list(SUPPORTED_SKILL_VARIANTS)}
            for target in SUPPORTED_SKILL_TARGETS
        ],
    }
