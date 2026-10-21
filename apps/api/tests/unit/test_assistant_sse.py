from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi.testclient import TestClient

from tests.fakes import Store


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def turn(
    client: TestClient, auth: dict[str, str], text: str, **extra: Any
) -> list[tuple[str, dict[str, Any]]]:
    r = client.post("/api/v1/assistant/turns", json={"text": text, **extra}, headers=auth)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def test_chat_turn_streams_masks_and_persists_masked_only(
    client: TestClient, auth: dict[str, str], store: Store
) -> None:
    events = turn(client, auth, "Namaste, mera number 98765 43210 hai", inputMode="voice")
    names = [e for e, _ in events]
    assert names[0] == "meta" and names[1] == "privacy" and names[-1] == "done"
    assert "token" in names and "error" not in names
    assert events[1][1]["entityCounts"]["phone"] == 1

    reply = "".join(d["delta"] for e, d in events if e == "token")
    assert "98765 43210" in reply  # unmasked locally for the user
    usage = events[-1][1]["usage"]
    assert usage["tokensIn"] > 0 and usage["costUsd"] > 0 and usage["model"]

    stored = [m.content_masked for m in store.assistant.messages]
    assert len(stored) == 2
    assert all("98765" not in s for s in stored)
    assert "<PHONE_1>" in stored[0] and "<PHONE_1>" in stored[1]
    assert store.privacy.rows[0].entity_counts["phone"] == 1
    assert len(store.budget.rows) == 2  # router call + reply stream


def test_bill_pay_turn_creates_pending_action_not_payment(
    client: TestClient, auth: dict[str, str], store: Store
) -> None:
    events = turn(client, auth, "Bijli ka bill pay kar do")
    tools = [d for e, d in events if e == "tool"]
    assert tools == [{"skill": "bills", "status": "running"}, {"skill": "bills", "status": "done"}]
    pending = [d for e, d in events if e == "pending_action"]
    assert len(pending) == 1 and "₹" in pending[0]["summary"]
    action = store.approvals.rows[uuid.UUID(pending[0]["id"])]
    assert action.status == "pending" and action.action_type == "bill_payment"

    r = client.post(
        f"/api/v1/pending-actions/{pending[0]['id']}/approve",
        headers={**auth, "Idempotency-Key": "approve-test-0001"},
    )
    assert r.status_code == 200 and r.headers["Idempotent-Replayed"] == "false"
    assert r.json()["data"]["action"]["status"] == "executed"
    assert r.json()["data"]["result"]["simulated"] is True
    replay = client.post(
        f"/api/v1/pending-actions/{pending[0]['id']}/approve",
        headers={**auth, "Idempotency-Key": "approve-test-0001"},
    )
    assert replay.status_code == 200 and replay.headers["Idempotent-Replayed"] == "true"
    no_key = client.post(f"/api/v1/pending-actions/{pending[0]['id']}/approve", headers=auth)
    assert no_key.status_code == 400


def test_follow_up_turn_reuses_conversation(client: TestClient, auth: dict[str, str]) -> None:
    first = turn(client, auth, "hello")
    conv_id = first[0][1]["conversationId"]
    second = turn(client, auth, "aur batao", conversationId=conv_id)
    assert second[0][1]["conversationId"] == conv_id
    convs = client.get("/api/v1/conversations", headers=auth).json()["data"]
    assert [c["id"] for c in convs] == [conv_id]
    msgs = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth).json()["data"]
    assert len(msgs) == 4


def test_unknown_conversation_is_json_404_before_stream(
    client: TestClient, auth: dict[str, str]
) -> None:
    r = client.post(
        "/api/v1/assistant/turns",
        json={"text": "hi", "conversationId": str(uuid.uuid4())},
        headers=auth,
    )
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_budget_exhausted_turn_is_429_before_stream(
    client: TestClient, auth: dict[str, str], store: Store
) -> None:
    client.app.state.services.settings.daily_budget_usd = 0.000001  # type: ignore[attr-defined]
    turn(client, auth, "hello")  # spends a little
    r = client.post("/api/v1/assistant/turns", json={"text": "phir se"}, headers=auth)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "budget_exceeded"
    assert "Retry-After" in r.headers


def test_llm_outage_mid_turn_emits_error_event(client: TestClient, auth: dict[str, str]) -> None:
    llm = client.app.state.services.llm  # type: ignore[attr-defined]
    for _ in range(llm.settings.circuit_failure_threshold):
        llm.breaker.record_failure()
    events = turn(client, auth, "hello")
    assert events[-1][0] == "error"
    assert events[-1][1]["code"] == "llm_unavailable"
