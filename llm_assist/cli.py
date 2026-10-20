"""ibus-llm-assist enable | disable | status: per-person setup, run as yourself in your desktop session."""
import argparse
import shutil
import subprocess
import sys
import time

import gi

gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus  # noqa: E402

from . import __version__  # noqa: E402
from .doctor import FAIL, OK, WARN, gnome_sources, run_checks  # noqa: E402
from .shellcode import shell_reads_layout_variant  # noqa: E402
from .i18n import _  # noqa: E402
from .layouts import ENGINE_PREFIX, INPUT_SOURCES_SCHEMA, read_registry  # noqa: E402
from .sources import disable, enable, enabled_layouts  # noqa: E402


def _ibus(*args: str) -> bool:
    if not shutil.which('ibus'):
        print(_('The "ibus" command is missing: install IBus first.'), file=sys.stderr)
        return False
    return subprocess.run(['ibus', *args], check=False).returncode == 0


def _wait_for_engines(names: set[str], timeout_s: float = 20) -> bool:
    """Whether the restarted ibus-daemon lists every engine in names within timeout_s."""
    IBus.init()
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        bus = IBus.Bus()
        if bus.is_connected() and names <= {e.get_name() for e in bus.list_engines()}:
            return True
        time.sleep(0.5)
    return False


def _set_sources(sources: list[tuple[str, str]]) -> None:
    settings = Gio.Settings.new(INPUT_SOURCES_SCHEMA)
    settings.set_value('sources', GLib.Variant('a(ss)', sources))
    Gio.Settings.sync()


def cmd_enable(layouts: list[str]) -> int:
    sources = gnome_sources()
    if sources is None:
        print(_('No GNOME input sources here. Add the engine with "ibus-setup" (Input Method tab, '
                '"… with suggestions").'))
        return 1
    registry = read_registry()
    plain = [name for kind, name in sources if kind == 'xkb']
    unknown = [x for x in layouts if x not in plain]
    if unknown:
        print(_('Not among your keyboard layouts: {layouts}. Yours: {yours}').format(
            layouts=', '.join(unknown), yours=', '.join(plain) or '-'), file=sys.stderr)
        return 1
    variant_ok = shell_reads_layout_variant() is not False
    skipped = []

    def wanted(xkb_id: str) -> bool:
        if layouts and xkb_id not in layouts:
            return False
        if xkb_id not in registry:
            skipped.append((xkb_id, _('not in the XKB registry')))
            return False
        if '+' in xkb_id and not variant_ok:
            skipped.append((xkb_id, _('this GNOME Shell would drop the variant (see docs/patches.md)')))
            return False
        return True

    new = enable(sources, wanted)
    for xkb_id, reason in skipped:
        print(_('Skipped {layout}: {reason}').format(layout=xkb_id, reason=reason))
    if new == sources:
        print(_('Nothing to change: {layouts}').format(layouts=', '.join(enabled_layouts(sources)) or '-'))
        return 0 if enabled_layouts(sources) else 1
    # ibus-daemon must list the engines before the desktop is asked to switch to them.
    names = {ENGINE_PREFIX + x for x in enabled_layouts(new)}
    if not (_ibus('write-cache') and _ibus('restart') and _wait_for_engines(names)):
        print(_('IBus did not load the engines: the input sources were left as they were. '
                'See "ibus-llm-assist status".'), file=sys.stderr)
        return 1
    _set_sources(new)
    print(_('Suggestions are on for: {layouts}').format(layouts=', '.join(enabled_layouts(new))))
    return 0


def cmd_disable() -> int:
    sources = gnome_sources()
    if sources is None:
        print(_('No GNOME input sources here: remove the engine in "ibus-setup".'))
        return 0
    new = disable(sources)
    if new != sources:
        _set_sources(new)
    print(_('Input sources: {sources}').format(sources=', '.join(name for _kind, name in new) or '-'))
    return 0


def cmd_status() -> int:
    marks = {OK: _('OK  '), WARN: _('NOTE'), FAIL: _('FAIL')}
    checks = run_checks()
    for check in checks:
        print(f'{marks[check.status]}  {check.message}')
    return 1 if any(c.status == FAIL for c in checks) else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='ibus-llm-assist',
                                     description=_('Suggestions and corrections from a local language model, '
                                                   'in every application.'))
    parser.add_argument('--version', action='version', version=__version__)
    sub = parser.add_subparsers(dest='command', required=True)
    on = sub.add_parser('enable', help=_('use the engine in place of your keyboard layouts'))
    on.add_argument('--layout', action='append', default=[], metavar='XKB_ID',
                    help=_('only this layout, such as "fr" or "us+intl" (repeatable)'))
    sub.add_parser('disable', help=_('put your plain keyboard layouts back'))
    sub.add_parser('status', help=_('check the setup'))
    args = parser.parse_args(argv)
    if args.command == 'enable':
        return cmd_enable(args.layout)
    if args.command == 'disable':
        return cmd_disable()
    return cmd_status()
