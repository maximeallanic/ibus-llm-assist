# Patches

The engine works on stock GNOME Shell 51 and GTK 4.24. Two small patches, shipped in [`patches/`](../patches), remove
the two limits left. Both are optional and independent. They are **not upstream**: nothing here has been submitted
to GNOME yet, so a distribution update brings back the stock package and its limit until you rebuild.

| Patch | Needed for | Without it |
|---|---|---|
| [`gnome-shell/status-keyboard-Read-the-layout-variant-of-IBus-engines.patch`](../patches/gnome-shell/status-keyboard-Read-the-layout-variant-of-IBus-engines.patch) | layouts with a variant (`us+intl`, `fr+bepo`, `de+neo`…) | GNOME Shell types with the plain layout (`us` instead of `us+intl`: no dead keys). The installer skips these layouts and `ibus-llm-assist status` says why |
| [`gtk4/textlayout-Apply-the-alpha-of-preedit-colors.patch`](../patches/gtk4/textlayout-Apply-the-alpha-of-preedit-colors.patch) | translucent ghost text in multi-line fields (GtkTextView) | the suggestion stays in italic at full opacity there; single-line fields are fine |

## GNOME Shell: the layout variant of IBus engines

With an IBus input source, GNOME Shell applies the keymap the engine declares. `InputSource._getXkbId()`
(`js/ui/status/keyboard.js`) reads `engineDesc.variant`, a property `IBus.EngineDesc` does not have (it is
`layout_variant` in GJS), so the variant is always dropped. This affects every IBus engine that declares a variant.
The patch reads `layout_variant`. It is two lines and applies to GNOME Shell 51.0; the same code is on upstream main.

`ibus-llm-assist status` and `enable` detect whether the running Shell has the fix by reading its compiled
JavaScript, so a patched Shell is used as soon as it is installed.

## GTK 4: alpha of pre-edit colours in GtkTextView

GTK's Wayland input method styles a pre-edit segment from its CSS node (`preedit.prediction`) and passes a translucent
colour as a colour plus a separate alpha attribute. `GtkTextLayout` (used by GtkTextView) ignored the alpha
attributes, so translucent pre-edit text was drawn opaque. GtkText (single-line fields) lays the text out with Pango
directly and was not affected. The patch reads both alpha attributes. It applies to GTK 4.24.1.

## Building

These are ordinary patches (`-p1`, DEP-3 headers). Rebuild the package of your distribution with the patch added, and
install it over the stock one. On Debian and Ubuntu (the way they were tested, GNOME Shell 51.0-2 and GTK
4.24.1+ds-1):

```sh
sudo apt-get build-dep gnome-shell          # or gtk4
apt-get source gnome-shell                  # needs deb-src lines in your APT sources
cd gnome-shell-51.0
cp /path/to/ibus-llm-assist/patches/gnome-shell/*.patch debian/patches/
echo status-keyboard-Read-the-layout-variant-of-IBus-engines.patch >> debian/patches/series
dch --local "+~llmassist" "Read the layout variant of IBus engines."
dpkg-buildpackage -b -us -uc
sudo apt install ../gnome-shell_*+~llmassist*.deb ../gnome-shell-common_*+~llmassist*.deb
```

For GTK 4, install every binary package the build produces that you already have (at least `libgtk-4-1`,
`libgtk-4-common`, `libgtk-4-bin`, `gir1.2-gtk-4.0`) so that their versions match. Log out and back in afterwards.

- **Fedora**: add the patch to the spec file's `Patch` lines (`fedpkg clone -a gnome-shell`, then
  `fedpkg local`). Untested.
- **Arch**: add it to the `PKGBUILD` of `gnome-shell` or `gtk4` (`pkgctl repo clone`), in `source` and `prepare()`,
  then `makepkg -si`. Untested.

A rebuilt package is replaced at the next update of the distribution's package; rebuild it then. The version suffix
used above (`+~llmassist1`) sorts above the stock version and below anything Debian appends to it (a rebuild `+b1`,
a stable update `+deb14u1`, a new revision), so updates still arrive.
