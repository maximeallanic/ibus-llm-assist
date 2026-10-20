"""Driver of run.sh, run inside the nested session: opens the client, types, takes screenshots, checks the text.

Scenario (scenarios.py): type a text beginning and pause (a suggestion shows), Ctrl+Tab (it is accepted), type a
sentence with a mistake (it is corrected at its end), Ctrl+Z (it comes back as typed), then the dead keys, if any;
last, open the keyboard menu of the top bar (the engine's switches).

The run stops before typing unless the client window has the focus and the scenario's engine is the active one.
The GTK client writes its text to OUT/text-<step>.txt, checked at the end; exit 1 on any failure. With --record,
frames are taken all along (OUT/frames, for make-media.sh).

    driver.py LANG OUT [--record] [--endpoint URL]
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import gi

gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from llm_assist.layouts import ENGINE_PREFIX  # noqa: E402
from llm_assist.llm import DEFAULT_ENDPOINT, LlmClient, ServerConfig  # noqa: E402
from scenarios import SCENARIOS, TITLE  # noqa: E402

CONTROL_L, TAB, Z = 0xffe3, 0xff09, 0x7a
KEY_Z = 44  # Linux input code of the QWERTY Z key
WINDOW_READY_S = 9      # the client maps and takes the focus
ANSWER_S = 6            # time given to the model for a suggestion or a correction


def call(bus, name, path, iface, method, args=None, reply=None):
    return bus.call_sync(name, path, iface, method, args, reply and GLib.VariantType(reply),
                         Gio.DBusCallFlags.NONE, 30000, None)


def shell_eval(bus, script):
    # Eval runs outside the Shell's modules: the libraries come from imports.gi.
    script = 'const {Clutter, GLib, Meta} = imports.gi; ' + script
    ok, result = call(bus, 'org.gnome.Shell', '/org/gnome/Shell', 'org.gnome.Shell', 'Eval',
                      GLib.Variant('(s)', (script,)), '(bs)').unpack()
    if not ok:
        sys.exit(f'Shell Eval failed: {result}')
    return result


def wait_for_shell(bus):
    for _ in range(120):
        try:
            call(bus, 'org.gnome.Shell', '/org/gnome/Shell', 'org.freedesktop.DBus.Peer', 'Ping')
            return
        except GLib.Error:
            time.sleep(0.5)
    sys.exit('the nested Shell did not come up')


def screenshot_area(bus, area, path: Path):
    ok, _path = call(bus, 'org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot', 'org.gnome.Shell.Screenshot',
                     'ScreenshotArea', GLib.Variant('(iiiibs)', (*area, False, str(path))), '(bs)').unpack()
    if not ok:
        sys.exit(f'screenshot {path.name} failed')


def screenshot(bus, path: Path):
    ok, _path = call(bus, 'org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot', 'org.gnome.Shell.Screenshot',
                     'Screenshot', GLib.Variant('(bbs)', (False, False, str(path))), '(bs)').unpack()
    if not ok:
        sys.exit(f'screenshot {path.name} failed')


class Session:
    """The nested Shell: a virtual keyboard of its own seat (unsafe mode), screenshots, optional frames."""

    def __init__(self, bus, out: Path, record: bool, area):
        self.bus, self.out, self.record, self.area = bus, out, record, area
        self.frames = out / 'frames'
        self.frame_times = []
        shell_eval(bus, 'global._e2eKeyboard = global.stage.context.get_backend().get_default_seat()'
                        '.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE); 0')
        if record:
            self.frames.mkdir(exist_ok=True)

    def key(self, keysym, pressed):
        state = 'PRESSED' if pressed else 'RELEASED'
        shell_eval(self.bus, f'global._e2eKeyboard.notify_keyval(GLib.get_monotonic_time(), {keysym}, '
                             f'Clutter.KeyState.{state}); 0')

    def tap(self, keysym):
        self.key(keysym, True)
        time.sleep(0.02)
        self.key(keysym, False)

    def type(self, text):
        for char in text:
            self.tap(IBus.unicode_to_keyval(char))
            time.sleep(0.06)
            self.frame()

    def ctrl(self, keysym):
        self.key(CONTROL_L, True)
        self.tap(keysym)
        self.key(CONTROL_L, False)

    def ctrl_key_code(self, code):
        """Ctrl with a physical key (Linux input code), whatever it types in the layout."""
        self.key(CONTROL_L, True)
        for state in ('PRESSED', 'RELEASED'):
            shell_eval(self.bus, f'global._e2eKeyboard.notify_key(GLib.get_monotonic_time(), {code}, '
                                 f'Clutter.KeyState.{state}); 0')
            time.sleep(0.02)
        self.key(CONTROL_L, False)

    def frame(self):
        if self.record:
            self.frame_times.append(time.monotonic())
            screenshot_area(self.bus, self.area, self.frames / f'{len(self.frame_times):04d}.png')

    def wait(self, seconds):
        """Sleep, taking frames when recording."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.record:
                self.frame()
            else:
                time.sleep(min(0.25, end - time.monotonic()))

    def shoot(self, name):
        self.frame()
        screenshot(self.bus, self.out / f'{name}.png')
        text = self.out / 'text.txt'
        if text.exists():
            (self.out / f'text-{name}.txt').write_text(text.read_text())

    def finish(self):
        if self.record:
            (self.out / 'frames.txt').write_text(''.join(f'{t - self.frame_times[0]:.3f}\n' for t in self.frame_times))


def warm_up(endpoint):
    """Wake the model: llama-server unloads it when idle (--sleep-idle-seconds), and reloading it takes longer than
    ANSWER_S, so the first suggestion would come too late and the run would judge the load instead of the engine."""
    loop, out = GLib.MainLoop(), {}

    def done(text):
        out['text'] = text
        loop.quit()

    LlmClient(ServerConfig(endpoint=endpoint)).ask('Answer with one word.', 'Ready?', 2, done)
    loop.run()
    if out['text'] is None:
        sys.exit(f'the language model server at {endpoint} did not answer')


def focus_client(bus):
    # The Shell starts in the overview, whose search entry would take the keys. It ignores hide() while its startup
    # animation runs, and leaving it focuses no window.
    for _ in range(40):
        if shell_eval(bus, 'Main.layoutManager._startingUp') == 'false':
            break
        time.sleep(0.5)
    shell_eval(bus, 'Main.overview.hide(); 0')
    for _ in range(40):
        if shell_eval(bus, 'Main.overview.visible') == 'false':
            break
        time.sleep(0.5)
    shell_eval(bus, 'global.get_window_actors().map(a => a.meta_window)'
                    '.filter(w => w.get_window_type() === Meta.WindowType.NORMAL).pop()'
                    '?.activate(global.get_current_time()); 0')
    time.sleep(1)
    focus = shell_eval(bus, 'global.display.focus_window?.get_title() ?? ""')
    if focus != json.dumps(TITLE):
        sys.exit(f'the client window does not have the focus (focus: {focus})')
    # A Shell modal dialog (a keyring prompt, say) would take the keys while the window keeps the focus.
    if shell_eval(bus, 'Main.modalCount') != '0':
        sys.exit('a Shell modal dialog is open over the client')


def geometry(bus):
    """Where the window and, once open, the keyboard menu are, for cropping the screenshots; 'frame' is the window
    with a margin for its shadow, even-sized for the video encoders, which the recorded frames cover."""
    window = shell_eval(bus, 'const r = global.display.focus_window.get_frame_rect(); '
                             'JSON.stringify([r.x, r.y, r.width, r.height])')
    x, y, w, h = json.loads(json.loads(window))
    margin = 24
    return {'window': [x, y, w, h],
            'frame': [x - margin, y - margin, (w + 2 * margin) // 2 * 2, (h + 2 * margin) // 2 * 2]}


def menu_geometry(bus):
    box = shell_eval(bus, 'const a = Main.panel.statusArea.keyboard.menu.actor; const [x, y] = '
                          'a.get_transformed_position(); const [w, h] = a.get_transformed_size(); '
                          'JSON.stringify([x, y, w, h].map(Math.round))')
    return json.loads(json.loads(box))


def check_texts(out, scenario):
    texts = {}
    steps = ['2-accepted', '3-corrected', '4-undone'] + (['5-dead-keys'] if scenario.dead_keys else [])
    for step in steps:
        path = out / f'text-{step}.txt'
        if not path.exists():
            return [f'{path.name} missing: nothing reached the client']
        texts[step] = path.read_text()
    accepted, corrected, undone = texts['2-accepted'], texts['3-corrected'], texts['4-undone']
    # The accepted suggestion may end a sentence, which is then corrected too: what precedes the last sentence is
    # read from the text, not assumed.
    before = undone[:-len(scenario.faulty)] if undone.endswith(scenario.faulty) else None
    failures = []
    if not accepted.startswith(scenario.beginning) or accepted == scenario.beginning:
        failures.append(f'no suggestion accepted: {accepted!r}')
    if before is None or not corrected.startswith(before):
        failures.append(f'Ctrl+Z did not restore {scenario.faulty!r}: {undone!r} (corrected: {corrected!r})')
    elif corrected == before + scenario.faulty:
        failures.append(f'sentence not corrected: {corrected!r}')
    if scenario.dead_keys and not texts['5-dead-keys'].endswith(scenario.composed):
        failures.append(f'dead keys not composed: {texts["5-dead-keys"]!r}')
    return failures


def run(session, bus, scenario):
    session.wait(0.5)
    session.type(scenario.beginning)
    session.wait(ANSWER_S)
    session.shoot('1-suggestion')
    session.ctrl(TAB)
    session.wait(1)
    session.shoot('2-accepted')
    session.type(scenario.faulty)
    session.wait(ANSWER_S)
    session.shoot('3-corrected')
    if scenario.latin:
        session.ctrl(Z)
    else:
        session.ctrl_key_code(KEY_Z)
    session.wait(1)
    session.shoot('4-undone')
    if scenario.dead_keys:
        for keysym in scenario.dead_keys:
            session.tap(keysym)
            time.sleep(0.06)
        session.wait(1)
        session.shoot('5-dead-keys')
    shell_eval(bus, 'Main.panel.statusArea.keyboard.menu.open(); 0')
    time.sleep(1.5)
    screenshot(bus, session.out / '6-menu.png')
    return menu_geometry(bus)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('lang', choices=sorted(SCENARIOS))
    parser.add_argument('out', type=Path)
    parser.add_argument('--record', action='store_true')
    parser.add_argument('--endpoint', default=DEFAULT_ENDPOINT)
    args = parser.parse_args()
    scenario = SCENARIOS[args.lang]
    bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    wait_for_shell(bus)
    app = subprocess.Popen([sys.executable, str(HERE / 'app.py'), str(args.out)])
    try:
        time.sleep(WINDOW_READY_S)
        focus_client(bus)
        engine = subprocess.run(['ibus', 'engine'], capture_output=True, text=True).stdout.strip()
        if engine != ENGINE_PREFIX + scenario.layout:
            known = subprocess.run(['ibus', 'list-engine', '--name-only'], capture_output=True, text=True).stdout
            ours = [n for n in known.split() if n.startswith(ENGINE_PREFIX)]
            sys.exit(f'IBus engine {engine!r}, expected {ENGINE_PREFIX + scenario.layout!r}; '
                     f'engines of this project known to IBus: {ours}')
        warm_up(args.endpoint)
        shapes = geometry(bus)
        session = Session(bus, args.out, args.record, shapes['frame'])
        shapes['menu'] = run(session, bus, scenario)
        session.finish()
        (args.out / 'geometry.json').write_text(json.dumps(shapes))
    finally:
        app.terminate()
        app.wait()
    failures = check_texts(args.out, scenario)
    for failure in failures:
        print('FAIL', failure, file=sys.stderr)
    print('texts:', {p.stem: p.read_text() for p in sorted(args.out.glob('text-*.txt'))}, file=sys.stderr)
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
