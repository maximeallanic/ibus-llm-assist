"""Reads GNOME Shell's own JavaScript out of its library, to tell whether it applies an IBus engine's layout variant.

GNOME Shell compiles its JavaScript into libshell as GResources, one ELF section per bundle (.gresource.<name>).
The gresource tool reads them too, but Fedora ships it only in glib2-devel; the section table is simple enough to
read here.
"""
import struct
from pathlib import Path

from gi.repository import Gio, GLib

KEYBOARD_JS = '/org/gnome/shell/ui/status/keyboard.js'
LIB_DIRS = ('/usr/lib/gnome-shell', '/usr/lib64/gnome-shell', '/usr/lib/x86_64-linux-gnu/gnome-shell',
            '/usr/lib/aarch64-linux-gnu/gnome-shell')


def gresource_sections(path: Path) -> list[bytes]:
    """Contents of the .gresource.* sections of a 64-bit little-endian ELF file; [] for anything else."""
    data = path.read_bytes()
    if data[:4] != b'\x7fELF' or data[4] != 2 or data[5] != 1:
        return []
    shoff, = struct.unpack_from('<Q', data, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', data, 0x3a)

    def header(i: int) -> tuple[int, int, int]:
        name, _type, _flags, _addr, offset, size = struct.unpack_from('<IIQQQQ', data, shoff + i * shentsize)
        return name, offset, size

    _, names_offset, _ = header(shstrndx)
    sections = []
    for i in range(shnum):
        name, offset, size = header(i)
        end = data.index(b'\0', names_offset + name)
        if data[names_offset + name:end].startswith(b'.gresource.'):
            sections.append(data[offset:offset + size])
    return sections


def resource_text(lib: Path, resource_path: str) -> str | None:
    for section in gresource_sections(lib):
        try:
            resource = Gio.Resource.new_from_data(GLib.Bytes.new(section))
            return resource.lookup_data(resource_path, Gio.ResourceLookupFlags.NONE).get_data().decode()
        except GLib.Error:
            continue
    return None


def shell_libraries() -> list[Path]:
    return [p for d in LIB_DIRS if Path(d).is_dir() for p in sorted(Path(d).glob('libshell-*.so'))]


def shell_reads_layout_variant() -> bool | None:
    """Whether GNOME Shell applies the variant of an IBus engine's layout; None without GNOME Shell.

    GNOME Shell up to 51 at least reads engineDesc.variant, which IBus.EngineDesc does not have, and applies the
    plain layout (patches/gnome-shell). This reads the code of the installed Shell rather than its version, so a
    distribution that carries the fix is recognised.
    """
    libs = shell_libraries()
    if not libs:
        return None
    for lib in libs:
        code = resource_text(lib, KEYBOARD_JS)
        if code is not None:
            return 'engineDesc.layout_variant' in code
    return None
