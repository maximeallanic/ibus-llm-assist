"""Swapping plain keyboard layouts for the engine in the person's input sources, and back.

Each engine types with the layout it is named after, so an engine and its plain layout stand for each other. Every
other source keeps its place, so sources added after ``enable`` survive ``disable``.
"""
from .layouts import ENGINE_PREFIX, engine_layout

Source = tuple[str, str]


def enable(sources: list[Source], wanted=lambda xkb_id: True) -> list[Source]:
    """Each plain layout that wanted() accepts is replaced by its engine."""
    out: list[Source] = []
    for kind, name in sources:
        source = ('ibus', ENGINE_PREFIX + name) if kind == 'xkb' and wanted(name) else (kind, name)
        if source not in out:
            out.append(source)
    return out


def disable(sources: list[Source]) -> list[Source]:
    """Each engine of ours is replaced by its plain layout."""
    out: list[Source] = []
    for kind, name in sources:
        xkb_id = engine_layout(name) if kind == 'ibus' else None
        source = ('xkb', xkb_id) if xkb_id else (kind, name)
        if source not in out:
            out.append(source)
    return out


def enabled_layouts(sources: list[Source]) -> list[str]:
    return [xkb_id for kind, name in sources if kind == 'ibus' and (xkb_id := engine_layout(name))]
