"""Translations of the user-facing strings (gettext domain ibus-llm-assist).

The catalogues sit in <prefix>/share/locale next to the installed package (<prefix>/lib/ibus-llm-assist/), in
build/locale in a checkout where install.sh ran, or in IBUS_LLM_ASSIST_LOCALEDIR when set. Without a catalogue for the
user's language, English.
"""
import gettext
import os
from pathlib import Path

DOMAIN = 'ibus-llm-assist'


def _locale_dir() -> str | None:
    override = os.environ.get('IBUS_LLM_ASSIST_LOCALEDIR')
    if override:
        return override
    package = Path(__file__).resolve().parent
    # Installed: <prefix>/lib/ibus-llm-assist/llm_assist.
    if package.parent.name == 'ibus-llm-assist' and package.parent.parent.name == 'lib':
        return str(package.parent.parent.parent / 'share' / 'locale')
    # A checkout: install.sh compiles the catalogues into build/locale.
    built = package.parent / 'build' / 'locale'
    return str(built) if built.is_dir() else None   # None: gettext's default directory


_translation = gettext.translation(DOMAIN, _locale_dir(), fallback=True)
_ = _translation.gettext
ngettext = _translation.ngettext
