"""Which keyboard layouts the engine is offered with, and the IBus engine list built from them.

The engine composes keys like IBus's own xkb engines and leaves the keymap to the desktop, which applies the layout
an engine declares. So there is one engine per layout the person types with, named after its XKB id
(``llm-assist:fr``, ``llm-assist:us+intl``): it takes the place of the plain layout in the input sources and keeps
the same keys.

ibus-daemon runs ``ibus-engine-llm-assist --xml`` when it builds its registry; the layouts come from the person's
input sources (GNOME), or from the system keyboard configuration (systemd-localed) elsewhere.
"""
import gettext
import logging
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .i18n import _

ENGINE_PREFIX = 'llm-assist:'
INPUT_SOURCES_SCHEMA = 'org.gnome.desktop.input-sources'
LOG = logging.getLogger('ibus-llm-assist')

# xkeyboard-config's registry: the classic path, then the one of xkeyboard-config 2.45 and later.
_RULES = ('/usr/share/X11/xkb/rules/evdev.xml', '/usr/share/xkeyboard-config-2/rules/evdev.xml')


@dataclass(frozen=True)
class Layout:
    xkb_id: str            # 'fr', 'us+alt-intl'
    description: str       # English, as in the registry; translated with xkeyboard-config's catalogue
    short: str             # short label shown in the top bar
    language: str          # ISO 639 code, 'other' when the registry has none

    @property
    def layout(self) -> str:
        return self.xkb_id.partition('+')[0]

    @property
    def variant(self) -> str:
        return self.xkb_id.partition('+')[2]

    @property
    def engine_name(self) -> str:
        return ENGINE_PREFIX + self.xkb_id


def engine_layout(engine_name: str) -> str | None:
    """XKB id of one of our engines, None for any other engine name."""
    return engine_name.removeprefix(ENGINE_PREFIX) if engine_name.startswith(ENGINE_PREFIX) else None


def rules_file() -> Path | None:
    root = os.environ.get('XKB_CONFIG_ROOT')
    candidates = ([str(Path(root) / 'rules' / 'evdev.xml')] if root else []) + list(_RULES)
    return next((Path(c) for c in candidates if Path(c).is_file()), None)


def _text(node: ET.Element | None, tag: str) -> str:
    found = node.find(tag) if node is not None else None
    return (found.text or '').strip() if found is not None else ''


def read_registry(path: Path | None = None) -> dict[str, Layout]:
    """Every layout and variant of the XKB registry, by XKB id."""
    path = path or rules_file()
    if path is None:
        return {}
    registry = {}
    for layout in ET.parse(path).getroot().iter('layout'):
        info = layout.find('configItem')
        name = _text(info, 'name')
        if not name:
            continue
        short = _text(info, 'shortDescription') or name
        language = _text(info, 'languageList/iso639Id') or 'other'
        registry[name] = Layout(name, _text(info, 'description') or name, short, language)
        for variant in layout.iterfind('variantList/variant'):
            vinfo = variant.find('configItem')
            vname = _text(vinfo, 'name')
            if vname:
                registry[f'{name}+{vname}'] = Layout(
                    f'{name}+{vname}', _text(vinfo, 'description') or f'{name}+{vname}',
                    _text(vinfo, 'shortDescription') or short, _text(vinfo, 'languageList/iso639Id') or language)
    return registry


def layouts_in_sources(sources: list[tuple[str, str]]) -> list[str]:
    """XKB ids the input sources type with: plain layouts and the layouts of our engines, in order."""
    ids = []
    for kind, name in sources:
        xkb_id = name if kind == 'xkb' else engine_layout(name) if kind == 'ibus' else None
        if xkb_id and xkb_id not in ids:
            ids.append(xkb_id)
    return ids


def _gnome_sources() -> list[tuple[str, str]] | None:
    from gi.repository import Gio
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup(INPUT_SOURCES_SCHEMA, True) is None:
        return None
    return [tuple(s) for s in Gio.Settings.new(INPUT_SOURCES_SCHEMA).get_value('sources').unpack()]


def _localed_layouts() -> list[str]:
    """The system keyboard (systemd-localed), as comma-separated layouts and variants."""
    from gi.repository import Gio, GLib
    try:
        proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SYSTEM, Gio.DBusProxyFlags.DO_NOT_CONNECT_SIGNALS, None, 'org.freedesktop.locale1',
            '/org/freedesktop/locale1', 'org.freedesktop.locale1', None)
    except GLib.Error as error:
        LOG.warning('No system bus to read the keyboard layout from: %s', error.message)
        return []
    layouts = proxy.get_cached_property('X11Layout')
    variants = proxy.get_cached_property('X11Variant')
    names = layouts.unpack().split(',') if layouts else []
    kinds = variants.unpack().split(',') if variants else []
    return [f'{n}+{kinds[i]}' if i < len(kinds) and kinds[i] else n for i, n in enumerate(names) if n]


def user_layouts() -> list[str]:
    sources = _gnome_sources()
    return layouts_in_sources(sources) if sources is not None else _localed_layouts()


def _display_name(layout: Layout) -> str:
    # xkeyboard-config ships the translations of its own descriptions.
    return gettext.dgettext('xkeyboard-config', layout.description)


def engines_xml(xkb_ids: list[str], registry: dict[str, Layout]) -> str:
    """The <engines> element ibus-daemon reads from ``--xml``; unknown layouts are left out."""
    engines = ET.Element('engines')
    for xkb_id in xkb_ids:
        layout = registry.get(xkb_id)
        if layout is None:
            LOG.warning('Layout %s is not in the XKB registry: no engine for it', xkb_id)
            continue
        engine = ET.SubElement(engines, 'engine')
        name = _display_name(layout)
        fields = {
            'name': layout.engine_name,
            'language': layout.language,
            'license': 'MIT',
            'author': 'ibus-llm-assist',
            'icon': 'input-keyboard-symbolic',
            'layout': layout.layout,
            'layout_variant': layout.variant,
            # TRANSLATORS: name of an input source; {layout} is the keyboard layout, such as "French (AZERTY)".
            'longname': _('{layout}, with suggestions').format(layout=name),
            'description': _('{layout} keyboard, with suggestions and corrections from a local language model')
            .format(layout=name),
            'rank': '0',
            'symbol': layout.short,
        }
        for tag, value in fields.items():
            if value:
                ET.SubElement(engine, tag).text = value
    return ET.tostring(engines, encoding='unicode')
