from __future__ import annotations

import shutil

from .config import Settings, active_profile_name
from .daemon import current_daemon_status


def get_capabilities(settings: Settings) -> dict:
    daemon = current_daemon_status(settings)
    return {
        "profile": active_profile_name(settings),
        "local_desktop": False,
        "local_desktop_removed": True,
        "remote_read": bool(settings.api_key),
        "remote_write": bool(settings.api_key),
        "remote_sync": bool(settings.api_key),
        "remote_file_pull": bool(settings.api_key),
        "remote_fulltext_pull": bool(settings.api_key),
        "remote_conflict_tracking": bool(settings.api_key),
        "remote_conflict_resolution": bool(settings.api_key),
        "remote_attachment_upload_experimental": bool(settings.api_key),
        "remote_attachment_upload_scope": [
            "imported-file/imported-url attachment upload for remote item create/update when sourcePath is provided",
            "ZIP transport for snapshot-style imported_url HTML attachments and directory bundles",
            "ZIP extraction for bundled remote attachment downloads into the headless file cache",
            "embedded-image attachment upload/download as a stored-file attachment",
            "metadata refresh after remote upload to capture md5, mtime, filename, and object version",
            "headless attachment cache pruning on remote delete detection and successful remote attachment deletes",
        ] if settings.api_key else [],
        "qmd_search": shutil.which("qmd") is not None,
        "citation_export": True,
        "citation_export_enabled": bool(settings.citation_export_enabled),
        "citation_export_format": settings.citation_export_format,
        "daemon_mode": daemon.mode,
        "daemon_message": daemon.message,
        "runtime_daemon_available": daemon.runtime_available,
        "runtime_daemon_mode": daemon.runtime_mode,
        "runtime_daemon_message": daemon.runtime_message,
        "runtime_daemon_read_api_ready": daemon.runtime_read_api_ready,
        "runtime_daemon_write_api_ready": daemon.runtime_write_api_ready,
        "runtime_daemon_observability": daemon.runtime_available,
        "paths": {
            "canonical_db": str(settings.resolved_canonical_db()),
            "mirror_db": str(settings.resolved_mirror_db()),
            "export_dir": str(settings.resolved_export_dir()),
            "citation_export_path": str(settings.resolved_citation_export_path()),
            "file_cache_dir": str(settings.resolved_file_cache_dir()),
            "recovery_snapshot_dir": str(settings.resolved_recovery_snapshot_dir()),
            "recovery_temp_dir": str(settings.resolved_recovery_temp_dir()),
            "daemon_runtime_state": daemon.runtime_state_path,
            "daemon_jobs_state": daemon.jobs_state_path,
            "daemon_events_log": daemon.events_log_path,
        },
    }
