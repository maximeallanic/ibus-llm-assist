#!/usr/bin/env bash
# Turns the output of a run.sh run into the README pictures: the window cropped out of each screenshot, the
# keyboard menu with the top bar, and, after a --record run, an animated GIF made of the frames at the times they
# were taken (nothing is drawn or retouched).
#
#   dev/e2e/make-media.sh OUT DEST NAME      e.g. dev/e2e/make-media.sh out/en screenshots en
set -euo pipefail
OUT=${1:?run output}
DEST=${2:?destination folder}
NAME=${3:?name prefix}
mkdir -p "$DEST"
command -v ffmpeg >/dev/null || { echo "ffmpeg is needed" >&2; exit 1; }

# The window with a margin for its shadow (the area the recorded frames cover), then the menu with the top bar.
read -r WX WY WW WH < <(python3 -I -c 'import json, sys
print(*json.load(open(sys.argv[1]))["frame"])' "$OUT/geometry.json")
read -r MX MY MW MH < <(python3 -I -c 'import json, sys
x, y, w, h = json.load(open(sys.argv[1]))["menu"]
m = 16
print(x - m - 80, 0, (w + 2 * m + 80) // 2 * 2, (y + h + m) // 2 * 2)' "$OUT/geometry.json")

crop() {  # SRC DEST X Y W H
    ffmpeg -loglevel error -y -i "$1" -vf "crop=$5:$6:$3:$4" "$2"
}
for shot in 1-suggestion 2-accepted 3-corrected 4-undone 5-dead-keys; do
    [ -f "$OUT/$shot.png" ] && crop "$OUT/$shot.png" "$DEST/$NAME-${shot#*-}.png" "$WX" "$WY" "$WW" "$WH"
done
crop "$OUT/6-menu.png" "$DEST/$NAME-menu.png" "$MX" "$MY" "$MW" "$MH"

if [ -f "$OUT/frames.txt" ]; then
    list=$OUT/frames.ffconcat
    python3 -I - "$OUT" >"$list" <<'PY'
import sys
from pathlib import Path
out = Path(sys.argv[1])
times = [float(t) for t in (out / 'frames.txt').read_text().split()]
print('ffconcat version 1.0')
for i, t in enumerate(times):
    duration = (times[i + 1] - t) if i + 1 < len(times) else 2.5   # hold the last frame
    print(f"file '{out / 'frames' / f'{i + 1:04d}.png'}'\nduration {duration:.3f}")
print(f"file '{out / 'frames' / f'{len(times):04d}.png'}'")
PY
    filters="fps=12,scale=$((WW * 3 / 4 / 2 * 2)):-2:flags=lanczos"
    ffmpeg -loglevel error -y -f concat -safe 0 -i "$list" \
        -vf "$filters,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
        -loop 0 "$DEST/$NAME-demo.gif"
fi
ls -l "$DEST"/"$NAME"-*
