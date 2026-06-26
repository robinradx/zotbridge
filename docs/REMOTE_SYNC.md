# Remote Sync

This guide covers syncing against zotero.org through the Zotero Web API.

## What You Need

- a Zotero Web API key
- at least one configured remote library
- a canonical store managed by zotbridge

Zotero `9.0.5` is the current tracked baseline, but this flow does not depend on Zotero Desktop internals. The browser-based Zotero Desktop login flow does not replace the Web API key used here.

## What It Supports

- personal libraries
- group libraries
- pull and push flows
- version-aware sync
- conflict reporting
- supported attachment upload and download paths
- supported fulltext refresh paths

## Typical Workflow

Run setup:

```text
zotbridge setup start
```

Discover libraries:

```text
zotbridge raw sync discover
```

Pull a library:

```text
zotbridge raw sync pull --library user:123456
```

Push staged changes:

```text
zotbridge raw sync push --library user:123456
```

Check conflicts:

```text
zotbridge raw sync conflicts --library user:123456
```

## How To Think About It

Remote sync is an adapter around the zotbridge runtime.

That means:

- remote objects are pulled into canonical state
- local edits are staged there first
- pushes back to zotero.org use version-aware remote operations
- conflicts are part of the model, not an edge case to ignore

## Zotero 9.0.5 Note

Zotero 9 introduced native citation-key support. zotbridge now:

- attempts native `citationKey` writes on remote item create/update
- falls back automatically when the remote API behavior does not accept that field

That keeps newer behavior available without breaking compatibility with older server-side expectations.
