# MCP

MCP is the tool-call interface for clients that already support MCP.

Run the stdio server directly:

```bash
zotbridge-mcp
```

Configure a client:

```bash
zotbridge setup add codex --scope user
zotbridge setup add claude-code --scope project
zotbridge setup add cursor --scope project
zotbridge setup add json
```

## Setup Targets

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

## Tool Groups

Library reads:

- `zotero_list_libraries`
- `zotero_list_items`
- `zotero_list_collections`
- `zotero_get_item`
- `zotero_get_collection`

Core store:

- `zotero_core_status`
- `zotero_core_libraries`
- `zotero_core_changes`

Sync:

- `zotero_sync_discover`
- `zotero_sync_pull`
- `zotero_sync_push`
- `zotero_sync_conflicts`
- `zotero_sync_conflict_rebase`
- `zotero_sync_conflict_accept_remote`
- `zotero_sync_mirror_discover`
- `zotero_sync_mirror_pull`

Search:

- `zotero_qmd_query`
- `zotero_qmd_search`
- `zotero_qmd_vsearch`
- `zotero_qmd_get`
- `zotero_qmd_doctor`

Mutations:

- `zotero_create_item`
- `zotero_update_item`
- `zotero_delete_item`
- `zotero_create_collection`
- `zotero_update_collection`
- `zotero_delete_collection`

Recovery:

- `zotero_recovery_repositories`
- `zotero_recovery_snapshot_create`
- `zotero_recovery_snapshot_list`
- `zotero_recovery_snapshot_verify`
- `zotero_recovery_restore_plan`
- `zotero_recovery_restore_execute`
- `zotero_recovery_restore_list`
- `zotero_recovery_restore_show`

Runtime:

- `zotero_capabilities`
- `zotero_daemon_status`

## Removed Tools

The desktop-local tools were removed:

- `zotero_local_sql`
- `zotero_local_import`
- `zotero_local_poll`
- `zotero_local_plan_apply`
- `zotero_local_apply`
