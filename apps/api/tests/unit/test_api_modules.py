from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import make_token
from tests.fakes import Store


def test_privacy_preview(client: TestClient, auth: dict[str, str]) -> None:
    r = client.post(
        "/api/v1/privacy/preview",
        json={"text": "PAN ABCPE1234F, UPI priya@okaxis", "knownNames": []},
        headers=auth,
    )
    data = r.json()["data"]
    assert data["maskedText"] == "PAN <PAN_1>, UPI <UPI_1>"
    assert data["totalMasked"] == 2


def test_me_patch_and_budget_limit(client: TestClient, auth: dict[str, str]) -> None:
    r = client.patch("/api/v1/me", json={"locale": "en-IN", "dailyBudgetUsd": 0.5}, headers=auth)
    assert r.status_code == 200
    assert r.json()["data"]["locale"] == "en-IN" and r.json()["data"]["dailyBudgetUsd"] == 0.5
    assert client.patch("/api/v1/me", json={"dailyBudgetUsd": 50}, headers=auth).status_code == 400
    assert (
        client.patch("/api/v1/me", json={"timezone": "Mars/Base"}, headers=auth).status_code == 400
    )
    usage = client.get("/api/v1/budget/usage?range=week", headers=auth).json()["data"]
    assert usage["range"] == "week" and usage["capUsd"] == 3.5


def test_memories_crud_encrypted(client: TestClient, auth: dict[str, str], store: Store) -> None:
    r = client.post(
        "/api/v1/memories",
        json={"kind": "person", "content": "Maa ka number 98765 43210"},
        headers=auth,
    )
    assert r.status_code == 201
    mem = r.json()["data"]
    assert mem["content"] == "Maa ka number 98765 43210"
    row = next(iter(store.memory.rows.values()))
    assert b"98765" not in row.content_ciphertext and row.embedding is not None

    found = client.get("/api/v1/memories?q=maa number", headers=auth).json()["data"]
    assert found[0]["id"] == mem["id"] and found[0]["score"] > 0

    upd = client.patch(
        f"/api/v1/memories/{mem['id']}", json={"content": "Maa: Sunita"}, headers=auth
    )
    assert upd.json()["data"]["content"] == "Maa: Sunita"
    assert (
        client.delete(f"/api/v1/memories/{mem['id']}", headers=auth).json()["data"]["hard"] is False
    )
    assert client.get("/api/v1/memories", headers=auth).json()["data"] == []
    assert client.delete(f"/api/v1/memories/{mem['id']}?hard=true", headers=auth).status_code == 200


def test_skills_list_and_run(client: TestClient, auth: dict[str, str]) -> None:
    skills = {s["name"]: s for s in client.get("/api/v1/skills", headers=auth).json()["data"]}
    assert {"daily-brief", "email-triage", "bills", "reminders", "calendar"} <= set(skills)
    assert skills["bills"]["requiresApproval"] is True

    brief = client.post("/api/v1/skills/daily-brief/run", json={}, headers=auth).json()["data"]
    assert "bills due" in brief["summary"] and brief["data"]["calendar"]["events"]
    triage = client.post(
        "/api/v1/skills/email-triage/run", json={"args": {"action": "reply"}}, headers=auth
    ).json()["data"]
    assert triage["pendingActions"][0]["actionType"] == "send_email"
    assert client.post("/api/v1/skills/calendar/run", json={}, headers=auth).status_code == 403
    assert client.post("/api/v1/skills/nope/run", json={}, headers=auth).status_code == 404
    bad = client.post("/api/v1/skills/bills/run", json={"args": {"action": "steal"}}, headers=auth)
    assert bad.status_code == 400


def test_reminders_crud(client: TestClient, auth: dict[str, str], store: Store) -> None:
    r = client.post(
        "/api/v1/reminders",
        json={"text": "Bill pay karna", "dueAt": "2026-10-22T09:00:00+05:30"},
        headers=auth,
    )
    assert r.status_code == 201
    rid = r.json()["data"]["id"]
    assert b"Bill" not in store.skills.reminders[next(iter(store.skills.reminders))].text_ciphertext
    assert (
        client.patch(f"/api/v1/reminders/{rid}", json={"status": "done"}, headers=auth).json()[
            "data"
        ]["status"]
        == "done"
    )
    assert len(client.get("/api/v1/reminders", headers=auth).json()["data"]) == 1
    assert client.delete(f"/api/v1/reminders/{rid}", headers=auth).status_code == 200
    naive = client.post(
        "/api/v1/reminders", json={"text": "x", "dueAt": "2026-10-22T09:00:00"}, headers=auth
    )
    assert naive.status_code == 400


def test_demo_reset_only_for_demo_users(client: TestClient, auth: dict[str, str]) -> None:
    client.post("/api/v1/skills/bills/run", json={"args": {"action": "pay"}}, headers=auth)
    r = client.post("/api/v1/demo/reset", headers=auth)
    assert r.status_code == 200
    assert r.json()["data"]["cleared"]["pendingActions"] == 1
    assert r.json()["data"]["seeded"] == {"inbox": 6, "calendar": 6, "bills": 5}
    real = {"Authorization": f"Bearer {make_token(anonymous=False)}"}
    assert client.post("/api/v1/demo/reset", headers=real).status_code == 403


def test_pending_actions_list_filter(client: TestClient, auth: dict[str, str]) -> None:
    client.post("/api/v1/skills/bills/run", json={"args": {"action": "pay"}}, headers=auth)
    items = client.get("/api/v1/pending-actions?status=pending", headers=auth).json()["data"]
    assert len(items) == 1 and items[0]["status"] == "pending"
    assert client.get("/api/v1/pending-actions?status=bogus", headers=auth).status_code == 400
