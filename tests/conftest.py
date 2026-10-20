"""테스트 공통 설정 — `agent`·`eval` 모듈을 임포트할 수 있게 경로를 넣는다.

pytest는 루트(`python -m pytest`)에서 실행한다. `pytest.ini`의 testpaths가
`tests/`를 가리킨다.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "eval"

for _path in (str(REPO_ROOT), str(EVAL_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)
