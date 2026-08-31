from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IconDescriptor:
    icon_id: str
    semantic: str
    source: str = "cws-vector-line"


class IconRegistry:
    def __init__(self) -> None:
        self._items: dict[str, IconDescriptor] = {}

    def register(self, icon_id: str, semantic: str) -> None:
        if icon_id in self._items:
            raise ValueError(f"Dubbel icon_id: {icon_id}")
        self._items[icon_id] = IconDescriptor(icon_id, semantic)

    def resolve(self, icon_id: str) -> IconDescriptor:
        if icon_id not in self._items:
            raise KeyError(f"Onbekend icon_id: {icon_id}")
        return self._items[icon_id]

    def has(self, icon_id: str) -> bool:
        return icon_id in self._items

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {
            key: {"semantic": value.semantic, "source": value.source}
            for key, value in sorted(self._items.items())
        }


ICON_REGISTRY = IconRegistry()
for _icon_id, _semantic in {
    "action.default": "Contextuele actie",
    "action.add": "Toevoegen",
    "action.delete": "Verwijderen",
    "action.edit": "Bewerken",
    "action.open": "Openen",
    "action.save": "Opslaan",
    "action.export": "Exporteren",
    "action.print": "Afdrukken",
    "action.undo": "Ongedaan maken",
    "action.redo": "Opnieuw",
    "action.settings": "Instellingen",
    "action.search": "Zoeken",
    "action.validate": "Valideren",
    "nav.project": "Project",
    "nav.viewer": "Viewer",
    "nav.production": "Productie",
    "nav.control": "Controle",
    "nav.output": "Uitvoer",
    "viewer.select": "Selecteren",
    "viewer.orbit": "Orbit",
    "viewer.pan": "Slepen",
    "viewer.fit": "Fit",
    "viewer.zoom": "Zoom",
    "viewer.measure": "Meten",
    "viewer.section": "Doorsnede",
    "viewer.isolate": "Isoleren",
    "status.activity": "Activity Center",
    "status.problem": "Problem Center",
    "status.success": "Gereed",
    "status.warning": "Waarschuwing",
    "status.error": "Fout",
}.items():
    ICON_REGISTRY.register(_icon_id, _semantic)


_EXACT_CONTROL_ICONS = {
    "nav_project": "nav.project",
    "nav_viewer": "nav.viewer",
    "nav_productie": "nav.production",
    "nav_controle": "nav.control",
    "nav_uitvoer": "nav.output",
    "global_undo": "action.undo",
    "global_redo": "action.redo",
    "global_activity": "status.activity",
    "global_problems": "status.problem",
    "global_settings": "action.settings",
    "global_command": "action.search",
    "global_print": "action.print",
}


def icon_for_test_id(test_id: str) -> str:
    """Resolve by stable control identity, never by translated label text."""
    exact = _EXACT_CONTROL_ICONS.get(test_id)
    if exact:
        return exact
    identity = test_id.lower()
    rules = (
        (("delete", "remove", "wissen", "clear"), "action.delete"),
        (("add", "new", "create", "toevoeg"), "action.add"),
        (("save", "opslaan"), "action.save"),
        (("print", "afdruk"), "action.print"),
        (("export", "package"), "action.export"),
        (("open", "import"), "action.open"),
        (("valid", "check", "prove"), "action.validate"),
        (("search", "find", "filter"), "action.search"),
        (("setting", "config", "preference"), "action.settings"),
        (("select", "pick"), "viewer.select"),
        (("orbit", "rotate"), "viewer.orbit"),
        (("pan", "drag"), "viewer.pan"),
        (("fit",), "viewer.fit"),
        (("zoom",), "viewer.zoom"),
        (("measure", "dimension"), "viewer.measure"),
        (("section", "clip"), "viewer.section"),
        (("isolate", "hide", "ghost"), "viewer.isolate"),
        (("edit", "workbench"), "action.edit"),
    )
    for needles, icon_id in rules:
        if any(needle in identity for needle in needles):
            return icon_id
    return "action.default"

