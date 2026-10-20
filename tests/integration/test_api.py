"""FastAPI 통합 테스트 — 실제 앱을 TestClient로 띄워 계약을 확인한다.

- `/health`, `/version` 스키마
- `/chat` 응답에 metadata가 붙고, RAG 상태가 노출되는지
- 라우팅이 incident/chat으로 갈라지는지

RAG는 꺼진 상태(RAG_ENABLED=0)로 고정한다. 이유는 두 가지다.
    1) 테스트가 측정용 인덱스 캐시를 덮어쓰면 안 된다.
    2) 테스트는 네트워크(ollama)에 의존하면 안 된다.
RAG 자체의 동작은 `tests/unit/test_classifier_gate.py`가 검증한다.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("LLM_BACKEND", "fake")
os.environ.setdefault("RAG_ENABLED", "0")
os.environ.setdefault("DATA_PROFILE", "extended")

from server import app   # noqa: E402  (환경 설정 뒤에 import)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_backend_and_rag_block(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["llm_backend"] == "fake"
    assert body["supervisor_version"] == "v2"
    assert "rag" in body
    assert body["rag"]["enabled"] is False
    assert body["data_profile"]["profile"] == "extended"
    assert body["data_profile"]["system_count"] == 12


def test_version_endpoint(client):
    body = client.get("/version").json()
    assert body["supervisor_version"] == "v2"


def test_chat_returns_reply_and_metadata(client):
    # fake 라우터는 '장애|진단|다운|지연|급증|incident|티켓' 키워드로 incident 경로를 탄다
    response = client.post("/chat", json={"message": "auth-service 응답이 느려요, 원인 진단해주세요",
                                          "thread_id": "t-test-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["reply"]
    metadata = body["metadata"]
    for key in ("route", "incident_type", "classifier_source", "classifier_reason",
                "retry_count", "replan_rounds", "systems_queried", "systems_unknown"):
        assert key in metadata, f"metadata에 {key}가 없다"
    assert metadata["route"] == "incident"
    assert metadata["incident_type"] == "high-latency"
    assert metadata["classifier_source"] == "keyword"   # RAG 꺼짐 → keyword 경로
    assert metadata["systems_queried"] >= 1
    assert metadata["systems_unknown"] == []


def test_chat_route_stays_chat_for_smalltalk(client):
    response = client.post("/chat", json={"message": "안녕하세요",
                                          "thread_id": "t-test-2"})
    metadata = response.json()["metadata"]
    assert metadata["route"] == "chat"
    assert metadata["incident_type"] is None


def test_stream_emits_final_answer(client):
    with client.stream("GET", "/chat/stream",
                       params={"message": "log-service 디스크 95%예요",
                               "thread_id": "t-test-3"}) as response:
        assert response.status_code == 200
        types = []
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            payload = line[len("data: "):]
            if payload.strip() == "[DONE]":
                break
            import json
            try:
                types.append(json.loads(payload).get("type"))
            except json.JSONDecodeError:
                continue
    assert "FinalAnswer" in types
