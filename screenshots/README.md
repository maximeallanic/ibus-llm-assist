# Screenshots

Every picture here is a real capture of a headless nested GNOME Shell 51 session, taken by `dev/e2e/run.sh` (GNOME
Shell's screenshot D-Bus API) and cropped by `dev/e2e/make-media.sh`. Nothing is drawn or retouched. The session is
a fresh one: default wallpaper and settings, a GTK 4 test window, made-up text. The suggestions and corrections are the
real answers of Gemma 4 E2B served by llama.cpp on the capture machine.

| Files | Run |
|---|---|
| `en-*` | `dev/e2e/run.sh en OUT --record`, layout `us`, English interface |
| `fr-*` | `dev/e2e/run.sh fr OUT --record`, layout `fr`, French interface |
| `ar-*` | `dev/e2e/run.sh ar OUT --record`, layout `ara`, Arabic interface (the engine's own strings have no Arabic translation yet) |

`*-demo.gif` is made of the frames taken during the run, each shown for the time that passed until the next one; the
typing pace is that of the test's virtual keyboard while it took frames.

The capture machine runs GNOME Shell and GTK 4 with the two [patches](../docs/patches.md), and the test window uses the
[CSS rule](../docs/configuration.md#look-of-the-suggestion) for translucent suggestions. On stock GTK, the multi-line
field shown here would draw the suggestion in italic at full opacity.
