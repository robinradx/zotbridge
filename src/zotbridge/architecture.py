from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ArchitectureState:
    canonical_store: str
    runtime: str
    web_sync: str
    server_mode: str
    desktop_mode: str
    qmd_role: str
    integration_model: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def current_architecture_state() -> ArchitectureState:
    return ArchitectureState(
        canonical_store="zotbridge canonical store",
        runtime="minimal daemon host",
        web_sync="first-class adapter",
        server_mode="core + daemon + web sync",
        desktop_mode="not included",
        qmd_role="derived markdown/text index",
        integration_model="skill package + MCP/HTTP API; no native client extensions",
    )
