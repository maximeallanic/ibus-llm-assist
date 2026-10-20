# Third-party software

This repository contains only ibus-llm-assist's own code (MIT, see [LICENSE](LICENSE)) and two patches to GNOME
projects, distributed under the licences of the projects they apply to:

| Path | Project | Licence |
|---|---|---|
| `patches/gnome-shell/` | GNOME Shell | GPL-2.0-or-later |
| `patches/gtk4/` | GTK | LGPL-2.1-or-later |

The installer can download, on your request, software that is not part of this repository and keeps its own
licence:

| What | Version | Source | Licence |
|---|---|---|---|
| llama.cpp (`llama-server`, Vulkan build) | b11714 | https://github.com/ggml-org/llama.cpp/releases/tag/b11714 | MIT |
| Gemma 4 E2B instruction-tuned, QAT q4_0 GGUF | revision 675cff42a74c774d6cb76f76d8eacb49b48c9b93 | https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf | Apache 2.0 |

At run time the engine uses IBus (LGPL-2.1-or-later), GLib, Pango and libsoup (LGPL-2.1-or-later) and PyGObject
(LGPL-2.1-or-later) from your distribution.
