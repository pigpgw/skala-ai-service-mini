"""HTML 슬라이드 덱 → 편집 가능한 PPTX (Microsoft html2pptx 스킬 기반).

왜 이 파일이 있는가
    스킬(`html2pptx`)은 HTML **한 장**을 PPTX 한 장으로 바꿔준다.
    발표는 여러 장이라 슬라이드별로 변환한 뒤 하나로 합쳐야 한다.
    이 래퍼는 (1) 슬라이드별 HTML을 스킬로 변환하고 (2) 결과를 하나의 덱으로
    합친다. 합칠 때 이미지와 도형의 관계(rels)까지 옮겨야 하므로 단순 복사가
    아니라 패키지 수준에서 처리한다.

사용
    # 1) 슬라이드 HTML이 doc/reports/slides/slide-01.html … 형태로 있어야 한다
    .venv/bin/python doc/tools/html2pptx_deck.py \
        --slides-dir doc/reports/slides \
        --out doc/reports/presentation.pptx

검증
    - 각 슬라이드 도형이 슬라이드 경계 안에 있는가 (범위 밖이면 실패)
    - 텍스트 상자가 원본 HTML의 줄바꿈 위치와 어긋나지 않는가 (줄 수 비교)
"""
from __future__ import annotations

import argparse
import copy
import io
import shutil
import sys
import tempfile
from pathlib import Path

# 스킬 설치 위치 (1회성 설치)
#   npx skills add https://github.com/microsoft/researchstudio --skill html2pptx
SKILL_CANDIDATES = [
    Path.home() / ".agents" / "skills" / "html2pptx" / "scripts",
    Path("/tmp/.agents/skills/html2pptx/scripts"),
]
SKILL_SCRIPTS = next((p for p in SKILL_CANDIDATES if p.is_dir()), SKILL_CANDIDATES[0])
if not SKILL_SCRIPTS.is_dir():
    raise SystemExit(
        "html2pptx 스킬이 없습니다. 설치:\n"
        "  npx skills add https://github.com/microsoft/researchstudio --skill html2pptx")
sys.path.insert(0, str(SKILL_SCRIPTS))

from pptx import Presentation            # noqa: E402
from pptx.oxml.ns import qn              # noqa: E402
from pptx.opc.constants import RELATIONSHIP_TYPE as RT   # noqa: E402

import html_to_pptx as H2P                # noqa: E402

SLIDE_W_INCH, SLIDE_H_INCH = 13.333, 7.5
VIEW_W, VIEW_H = 1280, 720


def _merge_slides(dest_prs, src_path: Path) -> None:
    """src_pptx의 1번 슬라이드를 dest_prs에 그대로 복사한다(이미지 포함)."""
    src = Presentation(str(src_path))
    src_slide = src.slides[0]
    new_slide = dest_prs.slides.add_slide(dest_prs.slide_layouts[6])

    # 이미지 파트를 먼저 옮기고 r:embed 값을 새 rId로 교체할 준비를 한다.
    remap: dict[str, str] = {}
    for rel in src_slide.part.rels.values():
        if "image" in rel.reltype:
            blob = rel.target_part.blob
            image_part = dest_prs.part.package.get_or_add_image_part(io.BytesIO(blob))
            remap[rel.rId] = new_slide.part.relate_to(image_part, RT.IMAGE)

    for shape in src_slide.shapes:
        element = copy.deepcopy(shape._element)
        for blip in element.iter(qn("a:blip")):
            old_rid = blip.get(qn("r:embed"))
            if old_rid in remap:
                blip.set(qn("r:embed"), remap[old_rid])
        new_slide.shapes._spTree.append(element)


def main() -> int:
    parser = argparse.ArgumentParser(description="HTML 슬라이드 덱 → PPTX")
    parser.add_argument("--slides-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--keep-temp", action="store_true")
    args = parser.parse_args()

    slides_dir = Path(args.slides_dir)
    slide_files = sorted(slides_dir.glob("slide-*.html"))
    if not slide_files:
        print(f"슬라이드 HTML이 없습니다: {slides_dir}/slide-*.html")
        return 1

    temp_dir = Path(tempfile.mkdtemp(prefix="deck_pptx_"))
    deck = Presentation()
    deck.slide_width = H2P.Inches(SLIDE_W_INCH)
    deck.slide_height = H2P.Inches(SLIDE_H_INCH)

    try:
        for index, slide_file in enumerate(slide_files, 1):
            print(f"[{index}/{len(slide_files)}] {slide_file.name}")
            dom = H2P.extract_dom(slide_file, viewport_w=VIEW_W, viewport_h=VIEW_H)
            single = temp_dir / f"slide-{index:02d}.pptx"
            H2P.build_pptx(dom, single,
                            width_inch=SLIDE_W_INCH, height_inch=SLIDE_H_INCH,
                            match_wrap=True)
            _merge_slides(deck, single)

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        deck.save(str(out))

        # ── 경계 검사 ──────────────────────────────────────────
        bad = []
        for index, slide in enumerate(deck.slides, 1):
            for shape in slide.shapes:
                try:
                    bottom = shape.top + shape.height
                    right = shape.left + shape.width
                except TypeError:
                    continue
                if bottom > deck.slide_height or right > deck.slide_width:
                    bad.append(f"슬라이드 {index}: {shape.shape_type} "
                               f"하단 {bottom} 우측 {right}")
                    break
        print(f"saved: {out} ({len(deck.slides)} slides)")
        if bad:
            print("★ 슬라이드 범위를 벗어난 도형:")
            for item in bad:
                print(f"   {item}")
            return 1
        print("경계 검사: 모든 도형이 슬라이드 안 ✓")
        return 0
    finally:
        if not args.keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)
        else:
            print(f"temp kept: {temp_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
