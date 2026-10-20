"""ibus-engine-llm-assist: started by ibus-daemon with --ibus to serve the engines, or with --xml to list them."""
import itertools
import logging
import sys

import gi

gi.require_version('IBus', '1.0')
from gi.repository import Gio, GLib, IBus  # noqa: E402

from . import __version__  # noqa: E402
from .config import SCHEMA, is_local, server_config  # noqa: E402
from .engine import LlmAssistEngine  # noqa: E402
from .layouts import engines_xml, read_registry, user_layouts  # noqa: E402
from .llm import LlmClient  # noqa: E402

BUS_NAME = 'io.github.maximeallanic.IBusLlmAssist'
OBJECT_PATH = '/io/github/maximeallanic/IBusLlmAssist/Engine'
LOG = logging.getLogger('ibus-llm-assist')


def serve() -> int:
    IBus.init()
    bus = IBus.Bus()
    if not bus.is_connected():
        LOG.error('No IBus daemon to connect to')
        return 1
    loop = GLib.MainLoop()
    bus.connect('disconnected', lambda *_: loop.quit())
    settings, serial = Gio.Settings.new(SCHEMA), itertools.count()
    llm = LlmClient()

    def configure(*_args) -> None:
        config = server_config(settings)
        if not is_local(config.endpoint):
            LOG.warning('The language model server %s is not on this machine: what you type is sent there',
                        config.endpoint)
        llm.configure(config)

    configure()
    for key in ('endpoint', 'server-api', 'model'):
        settings.connect(f'changed::{key}', configure)
    engines = []

    def create_engine(factory: IBus.Factory, name: str) -> IBus.Engine:
        engine = LlmAssistEngine(llm, settings, engine_name=name, connection=bus.get_connection(),
                                 object_path=f'{OBJECT_PATH}/{next(serial)}')
        engines.append(engine)  # IBus keeps no Python reference
        engine.connect('destroy', engines.remove)
        return engine

    factory = IBus.Factory.new(bus.get_connection())
    factory.connect('create-engine', create_engine)
    bus.request_name(BUS_NAME, 0)
    loop.run()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    logging.basicConfig(level=logging.INFO, format='%(name)s: %(message)s')
    if argv == ['--xml']:
        print(engines_xml(user_layouts(), read_registry()))
        return 0
    if argv == ['--ibus']:
        return serve()
    if argv == ['--version']:
        print(__version__)
        return 0
    print('Started by ibus-daemon: ibus-engine-llm-assist --ibus | --xml', file=sys.stderr)
    return 2
