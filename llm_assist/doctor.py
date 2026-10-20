"""Checks of a working setup, shown by ``ibus-llm-assist status`` and by verify.sh."""
import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version('IBus', '1.0')
from gi.repository import Gio, IBus  # noqa: E402

from .config import SCHEMA, is_local, read_api_key  # noqa: E402
from .i18n import _  # noqa: E402
from .layouts import ENGINE_PREFIX, INPUT_SOURCES_SCHEMA  # noqa: E402
from .shellcode import shell_reads_layout_variant  # noqa: E402
from .sources import enabled_layouts  # noqa: E402

COMPONENT = Path(os.environ.get('IBUS_LLM_ASSIST_COMPONENT', '/usr/share/ibus/component/ibus-llm-assist.xml'))
OK, WARN, FAIL = 'ok', 'warn', 'fail'


@dataclass
class Check:
    status: str
    message: str


def gnome_sources() -> list[tuple[str, str]] | None:
    source = Gio.SettingsSchemaSource.get_default()
    if source is None or source.lookup(INPUT_SOURCES_SCHEMA, True) is None:
        return None
    return [tuple(s) for s in Gio.Settings.new(INPUT_SOURCES_SCHEMA).get_value('sources').unpack()]


def _session_im_module() -> str:
    value = os.environ.get('GTK_IM_MODULE', '')
    if shutil.which('systemctl'):
        result = subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True, text=True,
                                check=False)
        for line in result.stdout.splitlines():
            if line.startswith('GTK_IM_MODULE='):
                value = line.partition('=')[2]
    return value


def _server_answers(endpoint: str) -> str | None:
    """None when the server lists its models, else the reason it does not."""
    request = urllib.request.Request(endpoint.rstrip('/') + '/v1/models')
    key = read_api_key()
    if key:
        request.add_header('Authorization', f'Bearer {key}')
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            json.load(response)
        return None
    except (urllib.error.URLError, OSError, ValueError) as error:
        return str(getattr(error, 'reason', error))


def run_checks() -> list[Check]:
    checks = []
    add = lambda status, message: checks.append(Check(status, message))  # noqa: E731

    if COMPONENT.is_file():
        add(OK, _('IBus component installed: {path}').format(path=COMPONENT))
    else:
        add(FAIL, _('IBus component missing: {path} (run install.sh)').format(path=COMPONENT))

    schema = Gio.SettingsSchemaSource.get_default()
    settings = None
    if schema is not None and schema.lookup(SCHEMA, True) is not None:
        settings = Gio.Settings.new(SCHEMA)
        add(OK, _('Settings schema found'))
    else:
        add(FAIL, _('Settings schema {schema} not found (run install.sh)').format(schema=SCHEMA))

    IBus.init()
    bus = IBus.Bus()
    if not bus.is_connected():
        add(FAIL, _('IBus is not running: log out and back in, or start it with "ibus-daemon -drx"'))
        known = []
    else:
        known = [e.get_name() for e in bus.list_engines() if e.get_name().startswith(ENGINE_PREFIX)]
        if known:
            add(OK, _('Engines known to IBus: {names}').format(names=', '.join(known)))
        else:
            add(FAIL, _('IBus lists none of the engines: run "ibus write-cache" then "ibus restart"'))

    sources = gnome_sources()
    if sources is None:
        add(WARN, _('No GNOME input sources: add an engine with "ibus-setup" (Input Method tab)'))
    else:
        layouts = enabled_layouts(sources)
        if layouts:
            add(OK, _('Input sources with suggestions: {layouts}').format(layouts=', '.join(layouts)))
        else:
            add(FAIL, _('No input source uses the engine: run "ibus-llm-assist enable"'))
        missing = [x for x in layouts if ENGINE_PREFIX + x not in known] if known else []
        if missing:
            add(FAIL, _('Input sources without an engine: {layouts} (run "ibus write-cache" then "ibus restart")')
                .format(layouts=', '.join(missing)))
        variants = [x for x in layouts if '+' in x]
        if variants and shell_reads_layout_variant() is False:
            add(FAIL, _('GNOME Shell ignores the layout variant of IBus engines, so {layouts} would type with the '
                        'plain layout: see docs/patches.md, or run "ibus-llm-assist disable"')
                .format(layouts=', '.join(variants)))

    im_module = _session_im_module()
    if im_module and im_module != 'ibus':
        add(WARN, _('GTK_IM_MODULE={value} in the session: GTK applications bypass IBus. Remove it and log out '
                    'and back in').format(value=im_module))

    if settings is not None:
        endpoint = settings.get_string('endpoint')
        reason = _server_answers(endpoint)
        if reason is None:
            add(OK, _('Language model server answers at {endpoint}').format(endpoint=endpoint))
        else:
            add(FAIL, _('No language model server at {endpoint}: {reason}').format(endpoint=endpoint, reason=reason))
        if not is_local(endpoint):
            add(WARN, _('{endpoint} is not on this machine: what you type is sent there').format(endpoint=endpoint))
    return checks
