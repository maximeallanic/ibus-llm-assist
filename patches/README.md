# Optional patches

| Directory | Package | Version it applies to | Needed for |
|---|---|---|---|
| `gnome-shell/` | GNOME Shell | 51.0 | keyboard layouts with a variant (`us+intl`…) |
| `gtk4/` | GTK 4 | 4.24.1 | translucent suggestions in multi-line fields (GtkTextView) |

Each is a `-p1` patch with a DEP-3 header saying what it fixes and why. They are not upstream. What works without
them, and how to build them in: [docs/patches.md](../docs/patches.md).
