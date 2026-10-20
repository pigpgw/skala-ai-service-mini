"""라우터 단위 테스트 — incident/chat 분기를 고정한다.

왜 테스트가 필요한가
    라우팅은 파이프라인 전체의 입구다. keyword 판정(RAG)이 무엇을 고르든
    라우팅이 chat이면 장애 파이프라인이 아예 돌지 않는다. 그래서 분기를 고정한다.

기준
    - `doc/regression_test_queries.md`의 10개 질의: 1~8은 incident, 9·10은 chat
    - 잡담·일반 질문은 chat ("확인해줘" 같은 넓은 단어는 incident로 잡지 않는다)
"""
from __future__ import annotations

import pytest

from agent.fake_llm import FastLLM

ROUTER = FastLLM("test-router", usd_per_1k_tokens=0.0)

REGRESSION_QUERIES = [
    ("payments-service 결제 응답이 느려지고 CPU가 치솟았어요, 원인 확인해주세요", "incident"),
    ("cache-service 메모리 사용률이 계속 올라가고 있어요", "incident"),
    ("log-service 디스크 공간이 부족하다는 알림이 왔어요", "incident"),
    ("gateway-service에서 payments-service로 가는 요청이 타임아웃 나고 있어요", "incident"),
    ("web-01 CPU 급증, auth-service 커넥션 풀도 같이 확인해줘", "incident"),
    ("payments-service랑 cache-service 둘 다 저하됐는데 공통 원인이 있는지 분석해줘", "incident"),
    ("로그인 응답이 느려요, 원인 확인해주세요", "incident"),
    ("billing-service 응답이 느려요", "incident"),
    ("안녕, 너는 누구야?", "chat"),
    ("제 이름은 민수입니다", "chat"),
]

CHAT_QUERIES = [
    "안녕하세요, 오늘 뭐 해요?",
    "날씨 확인해줘",
    "오늘 일정 알려줘",
    "파이썬 리스트랑 튜플 차이가 뭐야",
]


@pytest.mark.parametrize("query,expected", REGRESSION_QUERIES)
def test_regression_queries_route(query: str, expected: str):
    result, _ = ROUTER.route(query)
    assert result["route"] == expected


@pytest.mark.parametrize("query", CHAT_QUERIES)
def test_casual_queries_stay_chat(query: str):
    result, _ = ROUTER.route(query)
    assert result["route"] == "chat"


def test_route_never_raises_needs_analysis():
    result, _ = ROUTER.route("payments-service 응답이 느려요")
    assert result["needs_analysis"] is False
