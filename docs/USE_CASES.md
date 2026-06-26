# Use Cases

## Research Assistant

1. Configure MCP for the client.
2. Install the skill for that client.
3. Sync the relevant Zotero Web API library.
4. Use qmd for exploratory retrieval and MCP/API for exact metadata.

```bash
zotbridge setup add codex --scope user
zotbridge skill install codex
zotbridge raw sync discover
zotbridge raw sync pull --library user:123456
zotbridge qmd query "papers about long context retrieval"
```

## Service Sync

Use the daemon as a lightweight service:

```bash
zotbridge-daemon serve --host 127.0.0.1 --port 23119 --sync-interval 300
```

Agents or scripts can call:

- `GET /libraries`
- `POST /sync/pull`
- `POST /sync/push`
- `GET /search/query`
- `POST /recovery/snapshots`

## Exact Metadata Operations

Use direct reads when you know the library and key:

```bash
zotbridge raw mirror item user:123456 ABC12345
```

Use mutations for authoritative changes:

```bash
zotbridge raw item create user:123456 '{"itemType":"book","title":"Draft"}'
zotbridge raw sync push --library user:123456
```

## qmd Retrieval

Use qmd for discovery and topic-based research:

```bash
zotbridge qmd export --library user:123456
zotbridge qmd query "citation key support in Zotero"
zotbridge qmd vsearch "semantic search for related work"
zotbridge qmd get "<target-from-result>"
```

QMD is the discovery and source-recovery layer: search ranks exported Zotero Markdown by meaning, and `qmd get` recovers the exported source behind a useful hit. Do not use qmd as the authoritative metadata source for exact keys or writes.

## Recovery Before Risky Work

```bash
zotbridge recovery snapshot-create --reason before-import
zotbridge recovery snapshot-list
zotbridge recovery restore-plan --snapshot <snapshot_id>
```

Execute only after reviewing the plan:

```bash
zotbridge recovery restore-execute --snapshot <snapshot_id> --confirm
```

## Multi-Client Setup

Use MCP setup for exact tool calls:

```bash
zotbridge setup add claude-code --scope project
zotbridge setup add cursor --scope project
zotbridge setup add json
```

Use skills for client-specific guidance:

```bash
zotbridge skill install claude-code
zotbridge skill install cline
zotbridge skill export claude-desktop
```

## Removed Use Cases

The project no longer supports:

- reading a local Zotero Desktop SQLite profile
- writing pending changes into Zotero Desktop
- applying an external desktop helper patch
- installing bundled native client plugin projects

Use Zotero Web API sync, the canonical store, HTTP, MCP, and skills instead.
