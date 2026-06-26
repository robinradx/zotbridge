# API

The HTTP API is the stable service interface for scripts, local services, and remote daemon deployments.

Start the daemon:

```bash
zotbridge-daemon serve --host 127.0.0.1 --port 23119 --sync-interval 300
```

## Runtime

- `GET /health`
- `GET /capabilities`
- `GET /daemon/status`
- `GET /daemon/runtime`
- `GET /daemon/jobs`
- `GET /metrics`

## Core Store

- `GET /core/status`
- `GET /core/libraries`
- `GET /core/changes`
- `POST /core/libraries`

## Libraries

- `GET /libraries`
- `GET /libraries/{library_id}/items`
- `GET /libraries/{library_id}/collections`
- `GET /libraries/{library_id}/searches`
- `GET /libraries/{library_id}/items/{item_key}`
- `GET /libraries/{library_id}/collections/{collection_key}`

## Mutations

- `POST /libraries/{library_id}/items`
- `PATCH /libraries/{library_id}/items/{item_key}`
- `DELETE /libraries/{library_id}/items/{item_key}`
- `POST /libraries/{library_id}/collections`
- `PATCH /libraries/{library_id}/collections/{collection_key}`
- `DELETE /libraries/{library_id}/collections/{collection_key}`

Writes use the canonical zotbridge store when the library is present there. Otherwise, remote mirror-backed writes use the Zotero Web API.

## Sync

- `POST /sync/discover`
- `POST /sync/pull`
- `POST /sync/push`
- `GET /sync/conflicts`
- `POST /sync/conflicts/rebase`
- `POST /sync/conflicts/accept-remote`
- `POST /sync/mirror/discover`
- `POST /sync/mirror/pull`

## Search

- `GET /search/query?q=...`
- `GET /search/search?q=...`
- `GET /search/vsearch?q=...`
- `GET /search/get?target=...`
- `POST /search/export`

Use qmd search for discovery and `search/get` to recover the exported Markdown behind a useful hit. Use library/item endpoints for exact metadata.

## Recovery

- `GET /recovery/repositories`
- `GET /recovery/snapshots`
- `POST /recovery/snapshots`
- `GET /recovery/snapshots/{snapshot_id}`
- `POST /recovery/snapshots/{snapshot_id}/verify`
- `POST /recovery/snapshots/{snapshot_id}/push`
- `POST /recovery/snapshots/{snapshot_id}/pull`
- `GET /recovery/restores`
- `GET /recovery/restores/{run_id}`
- `POST /recovery/restore/plan`
- `POST /recovery/restore/execute`

## Removed Endpoints

The desktop-local endpoints were removed:

- `/local/import`
- `/local/poll`
- `/local/plan-apply`
- `/local/apply`
