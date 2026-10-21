#!/usr/bin/env bash
# PPTX를 실제 PowerPoint으로 열어 PDF로 내보내 슬라이드 PNG로 바꿔 눈으로 확인한다.
# (LibreOffice가 없는 이 환경에서 PowerPoint가 유일한 정밀 렌더 경로)
set -euo pipefail
cd "$(dirname "$0")/../.."
PPTX="${1:-doc/reports/presentation.pptx}"
OUT="${2:-/tmp/ppt_pages}"
rm -rf "$OUT"; mkdir -p "$OUT"
rm -f ~/Desktop/ppt_export.pdf
osascript <<AS >/dev/null
tell application "Microsoft PowerPoint"
    launch
    open POSIX file "$(pwd)/$PPTX"
    delay 4
    set p to active presentation
    save p in POSIX file "$HOME/Desktop/ppt_export.pdf" as save as PDF
    delay 3
    close p saving no
end tell
AS
.venv/bin/python - "$OUT" <<'PY'
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter
out = Path(sys.argv[1])
reader = PdfReader(str(Path.home() / "Desktop" / "ppt_export.pdf"))
for index, page in enumerate(reader.pages, 1):
    writer = PdfWriter(); writer.add_page(page)
    with open(out / f"p{index}.pdf", "wb") as handle:
        writer.write(handle)
print(f"분리 {len(reader.pages)}쪽 → {out}")
PY
for f in "$OUT"/p*.pdf; do sips -s format png -Z 1400 "$f" --out "${f%.pdf}.png" >/dev/null 2>&1; done
rm -f ~/Desktop/ppt_export.pdf
echo "PNG: $(ls "$OUT"/*.png | wc -l | tr -d ' ')장 → $OUT"
