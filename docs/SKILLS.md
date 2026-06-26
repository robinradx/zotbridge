# Skills

Skills are the lightweight guidance package for clients that support them. They describe how to choose qmd, CLI, HTTP, or MCP without embedding client-specific native code.

## Install

```bash
zotbridge skill install codex
zotbridge skill install claude-code
zotbridge skill install cline
zotbridge skill install all
```

Claude Desktop uses an exported archive:

```bash
zotbridge skill export claude-desktop
```

## Variants

- `general`: default usage guidance for local and project workflows
- `daemon`: daemon-first guidance for service deployments

Example:

```bash
zotbridge skill install codex --variant daemon
```

## What Skills Cover

- when to use qmd semantic search
- how qmd search connects to source recovery with `qmd get`
- when to use direct API, CLI, or MCP reads
- how to handle sync, push, and conflicts
- how to treat recovery snapshots
- what not to do with Zotero Desktop files

## Boundary

Skills are separate from MCP setup:

- `zotbridge setup add ...` writes MCP client configuration.
- `zotbridge skill install ...` writes skill instructions.

Use both when a client supports both. Use only skills when the client cannot use MCP but can still follow local instructions.
