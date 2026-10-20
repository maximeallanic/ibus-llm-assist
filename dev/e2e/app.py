"""GTK 4 client of the end-to-end run: a window with one text view that has the focus. Its whole text goes to
OUT/text.txt at every change, for the driver to check."""
import sys
from pathlib import Path

import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gio, Gtk  # noqa: E402

from scenarios import TITLE  # noqa: E402


def activate(app, out: Path):
    view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD, left_margin=28, top_margin=24, right_margin=28)
    css = Gtk.CssProvider()
    css.load_from_string('textview { font-size: 22px; }')
    view.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    buffer = view.get_buffer()
    buffer.connect('changed', lambda b: out.write_text(b.get_text(b.get_start_iter(), b.get_end_iter(), False)))
    window = Gtk.ApplicationWindow(application=app, title=TITLE, default_width=960, default_height=300, child=view)
    window.present()
    window.set_focus(view)


def main():
    # Not registered on the bus: the nested session has no accessibility registry to activate.
    app = Gtk.Application(application_id='io.github.maximeallanic.IBusLlmAssist.E2e',
                          flags=Gio.ApplicationFlags.NON_UNIQUE)
    app.connect('activate', activate, Path(sys.argv[1]) / 'text.txt')
    app.run([])


if __name__ == '__main__':
    main()
