from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class RuntimeMode:
    name: str
    description: str
    requires_desktop_zotero: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def server_runtime_mode() -> RuntimeMode:
    return RuntimeMode(
        name="server",
        description="zotbridge core hosted by zotbridge-daemon with Web API sync and no Zotero desktop dependency.",
        requires_desktop_zotero=False,
    )


def desktop_runtime_mode() -> RuntimeMode:
    return RuntimeMode(
        name="desktop",
        description="zotbridge core running on an end-user machine without bundled Zotero desktop integration.",
        requires_desktop_zotero=False,
    )
