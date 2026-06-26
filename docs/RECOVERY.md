# Recovery

Recovery protects zotbridge runtime state:

- canonical store
- mirror store
- file cache
- qmd export
- citation export
- snapshot metadata and restore run records

It does not restore or mutate Zotero Desktop profiles.

## Repositories

List configured repositories:

```bash
zotbridge recovery repositories
```

The built-in local snapshot repository is always available. Additional filesystem repositories can be configured through `backup_repositories`.

## Snapshots

Create a snapshot:

```bash
zotbridge recovery snapshot-create --reason before-large-sync
```

Inspect snapshots:

```bash
zotbridge recovery snapshot-list
zotbridge recovery snapshot-show <snapshot_id>
zotbridge recovery snapshot-verify <snapshot_id>
```

Copy snapshots to or from an external filesystem repository:

```bash
zotbridge recovery snapshot-push <snapshot_id> --repository archive
zotbridge recovery snapshot-pull <snapshot_id> --repository archive
```

## Restore Planning

Plan a full restore:

```bash
zotbridge recovery restore-plan --snapshot <snapshot_id>
```

Plan a library-scoped restore:

```bash
zotbridge recovery restore-plan --snapshot <snapshot_id> --library user:123456
```

The plan reports create, update, delete, and restore actions before anything is applied.

## Restore Execution

Execute a full restore:

```bash
zotbridge recovery restore-execute --snapshot <snapshot_id> --confirm
```

Execute a library-scoped restore:

```bash
zotbridge recovery restore-execute --snapshot <snapshot_id> --library user:123456 --confirm
```

For remote libraries, optionally push restored pending changes through the Zotero Web API:

```bash
zotbridge recovery restore-execute --snapshot <snapshot_id> --library user:123456 --push-remote --confirm
```

Every restore creates a pre-restore safety snapshot first.

## Restore Runs

```bash
zotbridge recovery restore-list
zotbridge recovery restore-show <run_id>
```

Restore runs record status, plan, safety snapshot, result, and errors.

## Removed Behavior

The old desktop-local restore flow has been removed:

- no `--apply-local`
- no local Zotero SQLite writes
- no desktop helper dependency

Restores only affect the canonical zotbridge store and derived runtime artifacts. Remote propagation goes through the Zotero Web API.
