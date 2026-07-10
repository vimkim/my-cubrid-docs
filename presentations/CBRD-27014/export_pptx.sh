#!/usr/bin/env bash
# Regenerate pptA-oos-review.pptx from pptA-oos-review.html (+ deck.css/deck.js).
# Renders each slide (?flat=1&slide=N) at 2x with Playwright's cached headless
# Chromium, then assembles a 16:9 PPTX (one full-bleed image per slide).
# Usage: bash export_pptx.sh [source.html] [output.pptx]  (or: just pptx)
set -euo pipefail
cd "$(dirname "$0")"

SHELL_BIN=$(ls ~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell | head -1)
SOURCE=${1:-pptA-oos-review.html}
OUTPUT=${2:-pptA-oos-review.pptx}
SLIDES=$(grep -c '<section class="slide' "$SOURCE")
SHOTS=$(mktemp -d)
trap 'rm -rf "$SHOTS"' EXIT

for i in $(seq 1 $SLIDES); do
  n=$(printf '%02d' "$i")
  "$SHELL_BIN" --headless --disable-gpu --no-sandbox \
    --force-device-scale-factor=2 --window-size=1280,720 \
    --screenshot="$SHOTS/s$n.png" \
    "file://$PWD/$SOURCE?flat=1&slide=$i" >/dev/null 2>&1
done

uv run --quiet --with python-pptx python - "$SHOTS" "$OUTPUT" <<'EOF'
import glob, sys
from pptx import Presentation
from pptx.util import Inches

shots_dir, out_path = sys.argv[1], sys.argv[2]
prs = Presentation()
# 16:9

prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
for png in sorted(glob.glob(f"{shots_dir}/s*.png")):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.shapes.add_picture(png, 0, 0, width=prs.slide_width, height=prs.slide_height)
prs.save(out_path)
print(f"wrote {out_path}")
EOF
echo done
