"""Settings of the engine: the GSettings schema and the server it talks to."""
import ipaddress
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from .llm import ServerConfig

SCHEMA = 'io.github.maximeallanic.IBusLlmAssist'
LOG = logging.getLogger('ibus-llm-assist')


def api_key_file() -> Path:
    """Optional bearer token for a server that asks for one: the file's first line. Kept out of dconf, which any
    program of the session can read, and readable only by its owner."""
    base = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    return Path(base) / 'ibus-llm-assist' / 'api-key'


def read_api_key(path: Path | None = None) -> str:
    path = path or api_key_file()
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except FileNotFoundError:
        return ''
    if path.stat().st_mode & 0o077:
        LOG.warning('%s is readable by other users: ignored (chmod 600 it)', path)
        return ''
    return lines[0].strip() if lines else ''


def server_config(settings) -> ServerConfig:
    return ServerConfig(endpoint=settings.get_string('endpoint'), api=settings.get_string('server-api'),
                        model=settings.get_string('model'), api_key=read_api_key())


def is_local(endpoint: str) -> bool:
    """Whether endpoint is on this machine: a loopback address, or localhost."""
    host = urlsplit(endpoint).hostname or ''
    if host == 'localhost' or host.endswith('.localhost'):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False
