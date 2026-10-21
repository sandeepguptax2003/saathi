"""Loads demo JSON and materializes relative dates against 'now' in the user's timezone."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from importlib import resources
from typing import Any, cast
from zoneinfo import ZoneInfo


@dataclass(frozen=True, slots=True)
class DemoEmail:
    id: str
    sender: str
    sender_name: str
    subject: str
    snippet: str
    received_at: datetime
    labels: tuple[str, ...]
    unread: bool
    needs_reply: bool


@dataclass(frozen=True, slots=True)
class DemoEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    location: str


@dataclass(frozen=True, slots=True)
class DemoBill:
    id: str
    biller: str
    category: str
    amount_inr: int
    due_date: date
    account_ref: str
    payee: str


@lru_cache(maxsize=8)
def _raw(name: str) -> list[dict[str, Any]]:
    text = resources.files("saathi_api.seed.demo").joinpath(f"{name}.json").read_text("utf-8")
    return cast(list[dict[str, Any]], json.loads(text))


def demo_counts() -> dict[str, int]:
    return {
        "inbox": len(_raw("inbox")),
        "calendar": len(_raw("calendar")),
        "bills": len(_raw("bills")),
    }


def inbox(now: datetime) -> list[DemoEmail]:
    return [
        DemoEmail(
            id=e["id"],
            sender=e["from"],
            sender_name=e["fromName"],
            subject=e["subject"],
            snippet=e["snippet"],
            received_at=now - timedelta(hours=int(e["receivedHoursAgo"])),
            labels=tuple(e.get("labels", [])),
            unread=bool(e.get("unread", False)),
            needs_reply=bool(e.get("needsReply", False)),
        )
        for e in _raw("inbox")
    ]


def calendar(now: datetime, tz: str) -> list[DemoEvent]:
    zone = ZoneInfo(tz)
    today = now.astimezone(zone).date()
    events = []
    for e in _raw("calendar"):
        day = today + timedelta(days=int(e["dayOffset"]))
        hh, mm = (int(x) for x in str(e["start"]).split(":"))
        start = datetime.combine(day, time(hh, mm), tzinfo=zone)
        events.append(
            DemoEvent(
                e["id"],
                e["title"],
                start,
                start + timedelta(minutes=int(e["durationMin"])),
                e["location"],
            )
        )
    return sorted(events, key=lambda ev: ev.start)


def bills(now: datetime, tz: str) -> list[DemoBill]:
    today = now.astimezone(ZoneInfo(tz)).date()
    return sorted(
        (
            DemoBill(
                id=b["id"],
                biller=b["biller"],
                category=b["category"],
                amount_inr=int(b["amountInr"]),
                due_date=today + timedelta(days=int(b["dueInDays"])),
                account_ref=b["accountRef"],
                payee=b["payee"],
            )
            for b in _raw("bills")
        ),
        key=lambda b: b.due_date,
    )


def format_inr(amount: int) -> str:
    """Indian digit grouping: 1234567 -> ₹12,34,567."""
    s = str(amount)
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    groups: list[str] = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return "₹" + ",".join(groups) + "," + tail
