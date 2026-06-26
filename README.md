# zotbridge

zotbridge is a Zotero integration layer for agents, apps, and scripts, with Web API sync, HTTP/MCP access, semantic search over libraries, and recoverable headless state. It keeps the local runtime focused:

- canonical SQLite store
- Zotero Web API sync for personal and group libraries
- HTTP API and MCP server for tool-capable clients
- qmd-backed semantic search over exported Markdown
- skills for clients that support them
- recovery snapshots for canonical state and derived artifacts

It no longer ships a Zotero Desktop helper, reads or writes `zotero.sqlite`, or bundles native client plugin projects; compatibility is tracked against Zotero `9.0.5` while relying on the Zotero Web API instead of Desktop internals.

## Install

```bash
uv tool install zotbridge
# or, from a checkout:
uv run --no-editable zotbridge version
```

Useful entry points:

```bash
zotbridge                 # human-oriented CLI
zotbridge raw ...         # strict JSON/machine-friendly commands
zotbridge-daemon serve    # HTTP API daemon
zotbridge-mcp             # MCP stdio server
```

## Setup

Run the wizard:

```bash
zotbridge setup start
```

Or configure directly:

```bash
zotbridge config init \
  --api-key "$ZOTERO_API_KEY" \
  --remote-library-id user:123456 \
  --default-library-id user:123456
```

Discover and sync remote libraries:

```bash
zotbridge raw sync discover
zotbridge raw sync pull --library user:123456
```

## Integration

Use MCP setup when a client can call MCP tools:

```bash
zotbridge setup add codex --scope user
zotbridge setup add claude-code --scope project
zotbridge setup add cursor --scope project
zotbridge setup add json
```

Use skills when a client supports them:

```bash
zotbridge skill install codex
zotbridge skill install claude-code
zotbridge skill install cline
zotbridge skill export claude-desktop
```

There is no native client plugin install/update flow. The intended distribution boundary is the Python runtime plus MCP/HTTP config and skills.

## Runtime

Start the API daemon:

```bash
zotbridge-daemon serve --host 127.0.0.1 --port 23119 --sync-interval 300
```

Useful endpoints:

- `GET /health`
- `GET /capabilities`
- `GET /daemon/status`
- `GET /libraries`
- `GET /libraries/{library_id}/items`
- `POST /sync/discover`
- `POST /sync/pull`
- `POST /sync/push`
- `POST /recovery/snapshots`

## Search

Export Markdown and query through qmd:

```bash
zotbridge qmd export --library user:123456
zotbridge qmd query "retrieval augmented generation"
zotbridge qmd vsearch "semantic search over papers"
zotbridge qmd get "<target-from-result>"
```

Use qmd for discovery and related-work retrieval, then `qmd get` to recover the exported source behind a useful hit. Use direct API/CLI/MCP reads for exact item keys, collections, and authoritative metadata.

## Recovery

Create and inspect snapshots:

```bash
zotbridge recovery snapshot-create --reason before-large-sync
zotbridge recovery snapshot-list
zotbridge recovery restore-plan --snapshot <snapshot_id>
```

Execute a restore only with explicit confirmation:

```bash
zotbridge recovery restore-execute --snapshot <snapshot_id> --confirm
```

For remote libraries, optionally push restored pending changes through the Zotero Web API:

```bash
zotbridge recovery restore-execute --snapshot <snapshot_id> --library user:123456 --push-remote --confirm
```

## Project Layout

- `src/zotbridge/core/`: canonical store and change model
- `src/zotbridge/adapters/web_sync.py`: Zotero Web API sync adapter
- `src/zotbridge/api.py`: HTTP API
- `src/zotbridge/mcp.py`: MCP stdio server
- `src/zotbridge/agent_setup.py`: MCP config and skill installers
- `src/zotbridge/recovery.py`: snapshots and restore flow
- `tests/`: Python runtime and integration tests
- `docs/`: focused CLI, API, MCP, skills, sync, and recovery docs

## Verification

```bash
uv run pytest -q
```
