"""MCP ops 서버 통합 테스트 — stdio subprocess로 실제 Tool·Resource를 호출한다.

`agent/mcp_client.py`가 `mcp_server.py`를 **subprocess로 띄워** 통신하므로,
이 테스트는 프로세스 경계(환경변수 상속 포함)를 실제로 지난다.
"""
from __future__ import annotations

import asyncio

import pytest

from agent.mcp_client import MCPClient


async def _with_client(action):
    client = MCPClient(flaky_first_tool_call=False)   # 데모용 지연 주입은 제외
    await client.start()
    try:
        return await action(client)
    finally:
        await client.stop()


def _call_tool(client, name, arguments):
    return client.call_tool(name, arguments)


def test_monitoring_tool_returns_known_system(monkeypatch):
    monkeypatch.setenv("DATA_PROFILE", "extended")

    async def scenario():
        return await _with_client(lambda client: _call_tool(
            client, "get_monitoring_status", {"system_name": "auth-service"}))

    data = asyncio.run(scenario())
    assert data["system_name"] == "auth-service"
    assert data["status"] == "degraded"
    assert data["alerts"]


def test_monitoring_tool_returns_unknown_for_unlisted_system(monkeypatch):
    """회귀 질의 #8 — 목록에 없는 시스템은 unknown으로 답한다."""
    monkeypatch.setenv("DATA_PROFILE", "extended")

    async def scenario():
        return await _with_client(lambda client: _call_tool(
            client, "get_monitoring_status", {"system_name": "billing-service"}))

    data = asyncio.run(scenario())
    assert data["status"] == "unknown"
    assert any("not found" in alert for alert in data["alerts"])


def test_data_profile_reaches_the_mcp_subprocess(monkeypatch):
    """프로파일 값이 subprocess까지 전달되는지 확인한다."""
    monkeypatch.setenv("DATA_PROFILE", "extended")

    async def scenario():
        return await _with_client(lambda client: _call_tool(
            client, "get_monitoring_status", {"system_name": "search-service"}))

    extended = asyncio.run(scenario())
    assert extended["status"] == "degraded"

    monkeypatch.setenv("DATA_PROFILE", "base")

    async def base_scenario():
        return await _with_client(lambda client: _call_tool(
            client, "get_monitoring_status", {"system_name": "search-service"}))

    base = asyncio.run(base_scenario())
    assert base["status"] == "unknown"


def test_runbook_resource_is_readable(monkeypatch):
    monkeypatch.setenv("DATA_PROFILE", "extended")

    async def scenario():
        async def action(client):
            server, template = await client.find_resource_template("get_incident_runbook")
            assert template.startswith("runbook://")
            return await client.read_resource(
                template.format(incident_type="high-latency"), server=server)
        return await _with_client(action)

    body = asyncio.run(scenario())
    assert "Runbook" in body or "runbook" in body.lower()


def test_prompt_is_available(monkeypatch):
    monkeypatch.setenv("DATA_PROFILE", "extended")

    async def scenario():
        async def action(client):
            server = await client.find_prompt("incident_analysis_prompt")
            return await client.get_prompt(
                "incident_analysis_prompt",
                {"system_name": "auth-service", "symptom": "응답 지연"},
                server=server)
        return await _with_client(action)

    text = asyncio.run(scenario())
    assert "auth-service" in text
