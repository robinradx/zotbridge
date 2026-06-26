# CLI

`zotbridge` is the human-facing CLI. `zotbridge raw ...` exposes the same core operations with JSON-first output for scripts and agents.

## Setup

```bash
zotbridge setup start
zotbridge setup account
zotbridge setup libraries
zotbridge setup list
zotbridge setup add codex --scope user
zotbridge setup add claude-code --scope project
zotbridge setup add cursor --scope project
zotbridge setup add json
zotbridge setup remove cursor --scope project
```

Supported MCP setup targets:

- `codex`
- `claude-code`
- `claude-desktop`
- `cursor`
- `gemini`
- `cline`
- `antigravity`
- `opencode`
- `windsurf`
- `json`

## Skills

```bash
zotbridge skill install codex
zotbridge skill install claude-code
zotbridge skill install cline
zotbridge skill install all
zotbridge skill export claude-desktop
```

Skill variants:

- `general`
- `daemon`

There is no native plugin install/update command. Use MCP setup plus skills.

## Config

```bash
zotbridge config init --api-key "$ZOTERO_API_KEY" --remote-library-id user:123456
zotbridge config show
zotbridge config wizard
```

Legacy `data_dir` and `zotero_bin` keys are ignored if found in older config files.

## Sync

```bash
zotbridge raw sync discover
zotbridge raw sync pull --library user:123456
zotbridge raw sync push --library user:123456
zotbridge raw sync conflicts --library user:123456
zotbridge raw sync conflict-rebase --library user:123456 --entity-type item --key ABC12345
zotbridge raw sync conflict-accept-remote --library user:123456 --entity-type item --key ABC12345
```

The mirror commands are retained for compatibility:

```bash
zotbridge raw sync mirror-discover
zotbridge raw sync mirror-pull --library user:123456
```

## Items And Collections

```bash
zotbridge raw item create user:123456 '{"itemType":"book","title":"Draft"}'
zotbridge raw item update user:123456 ABC12345 '{"title":"Updated"}'
zotbridge raw item delete user:123456 ABC12345

zotbridge raw collection create user:123456 '{"name":"Reading"}'
zotbridge raw collection update user:123456 COL12345 '{"name":"Reviewed"}'
zotbridge raw collection delete user:123456 COL12345
```

Writes go either to the canonical zotbridge store when that library is present there, or to the Zotero Web API for remote mirror-backed libraries.

## qmd Search

```bash
zotbridge qmd export --library user:123456
zotbridge qmd embed --max-docs-per-batch 500 --max-batch-mb 64
zotbridge qmd query "retrieval augmented generation"
zotbridge qmd search "citation key"
zotbridge qmd vsearch "semantic related work"
zotbridge qmd get "<target-from-result>"
zotbridge qmd doctor
```

Use `qmd query`, `search`, and `vsearch` for discovery. Use `qmd get` to recover the exported Markdown behind a useful hit when the snippet is not enough.

## Daemon

```bash
zotbridge daemon status
zotbridge daemon command
zotbridge daemon serve --host 127.0.0.1 --port 23119 --sync-interval 300
```

`zotbridge-daemon serve` is equivalent to `zotbridge daemon serve`.

## Recovery

```bash
zotbridge recovery repositories
zotbridge recovery snapshot-create --reason before-sync
zotbridge recovery snapshot-list
zotbridge recovery snapshot-show <snapshot_id>
zotbridge recovery snapshot-verify <snapshot_id>
zotbridge recovery restore-plan --snapshot <snapshot_id>
zotbridge recovery restore-execute --snapshot <snapshot_id> --confirm
zotbridge recovery restore-execute --snapshot <snapshot_id> --library user:123456 --push-remote --confirm
```

Restores no longer apply changes into Zotero Desktop. Remote follow-up uses the Zotero Web API.

## Update

```bash
zotbridge update --check
zotbridge update
```

After a successful package update, already-installed skills are refreshed. No plugin bundles are refreshed because the package no longer ships them.
