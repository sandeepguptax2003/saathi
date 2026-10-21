"""Indian PII masker. Replaces PII with stable placeholders like <PHONE_1> before any model call.

Order matters: email -> UPI -> card (Luhn) -> bank account (keyword anchored) -> phone ->
Aadhaar -> PAN -> IFSC -> names from memory. Placeholders never match later patterns.
Over-masking is preferred to under-masking (12-digit numbers are treated as Aadhaar without a
Verhoeff check on purpose).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import StrEnum


class Entity(StrEnum):
    EMAIL = "email"
    UPI = "upi"
    CARD = "card"
    ACCOUNT = "account"
    PHONE = "phone"
    AADHAAR = "aadhaar"
    PAN = "pan"
    IFSC = "ifsc"
    NAME = "name"


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@dataclass(frozen=True, slots=True)
class _Rule:
    entity: Entity
    pattern: re.Pattern[str]
    group: int = 0
    accept: Callable[[str], bool] | None = None


def _card_accept(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return 13 <= len(digits) <= 19 and luhn_ok(digits)


_RULES: tuple[_Rule, ...] = (
    _Rule(
        Entity.EMAIL,
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}\b"),
    ),
    _Rule(
        Entity.UPI,
        re.compile(r"\b[A-Za-z0-9][A-Za-z0-9._-]{1,255}@[A-Za-z][A-Za-z0-9]{1,63}\b(?!\.[A-Za-z])"),
    ),
    _Rule(Entity.CARD, re.compile(r"(?<![\d<])\d(?:[ -]?\d){12,18}(?!\d)"), accept=_card_accept),
    _Rule(
        Entity.ACCOUNT,
        re.compile(
            r"(?i)\b(?:a/?c|acc(?:oun)?t|acct|khata)\s*(?:no\.?|number|num|#)?\s*[:#-]?\s*(\d{9,18})\b"
        ),
        group=1,
    ),
    _Rule(Entity.PHONE, re.compile(r"(?<![\d<])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")),
    _Rule(Entity.AADHAAR, re.compile(r"(?<![\d<])[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")),
    _Rule(Entity.PAN, re.compile(r"(?i)\b[A-Z]{3}[ABCFGHLJPT][A-Z]\d{4}[A-Z]\b")),
    _Rule(Entity.IFSC, re.compile(r"(?i)\b[A-Z]{4}0[A-Z0-9]{6}\b")),
)

PLACEHOLDER_RE = re.compile(r"<([A-Z]+)_(\d+)>")


@dataclass(frozen=True, slots=True)
class MaskResult:
    masked_text: str
    entity_counts: dict[str, int]


@dataclass
class MaskSession:
    """Holds the placeholder map for one turn so the same value always gets the same token."""

    known_names: tuple[str, ...] = ()
    mapping: dict[str, str] = field(default_factory=dict)  # token -> original
    _reverse: dict[tuple[Entity, str], str] = field(default_factory=dict)
    _counters: dict[Entity, int] = field(default_factory=dict)

    def _token_for(self, entity: Entity, value: str) -> str:
        norm = re.sub(r"[\s-]", "", value).lower()
        key = (entity, norm)
        existing = self._reverse.get(key)
        if existing is not None:
            return existing
        n = self._counters.get(entity, 0) + 1
        self._counters[entity] = n
        token = f"<{entity.value.upper()}_{n}>"
        self._reverse[key] = token
        self.mapping[token] = value
        return token

    def mask(self, text: str) -> MaskResult:
        counts = {e.value: 0 for e in Entity}
        out = text
        for rule in _RULES:
            out = self._apply(rule, out, counts)
        out = self._mask_names(out, counts)
        return MaskResult(masked_text=out, entity_counts=counts)

    def _apply(self, rule: _Rule, text: str, counts: dict[str, int]) -> str:
        def repl(m: re.Match[str]) -> str:
            value = m.group(rule.group)
            if rule.accept is not None and not rule.accept(value):
                return m.group(0)
            counts[rule.entity.value] += 1
            token = self._token_for(rule.entity, value)
            if rule.group == 0:
                return token
            start, end = m.span(rule.group)
            whole_start = m.start(0)
            g0 = m.group(0)
            return g0[: start - whole_start] + token + g0[end - whole_start :]

        return rule.pattern.sub(repl, text)

    def _mask_names(self, text: str, counts: dict[str, int]) -> str:
        names = sorted(
            {n.strip() for n in self.known_names if len(n.strip()) >= 2}, key=len, reverse=True
        )
        for name in names:
            pattern = re.compile(rf"(?i)(?<![\w<]){re.escape(name)}(?![\w>])")

            def repl(_m: re.Match[str], _name: str = name) -> str:
                counts[Entity.NAME.value] += 1
                return self._token_for(Entity.NAME, _name)

            text = pattern.sub(repl, text)
        return text

    def unmask(self, text: str) -> str:
        return unmask(text, self.mapping)


def mask_text(text: str, known_names: Iterable[str] = ()) -> tuple[MaskResult, dict[str, str]]:
    session = MaskSession(known_names=tuple(known_names))
    result = session.mask(text)
    return result, session.mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


class StreamUnmasker:
    """Unmasks a token stream whose placeholders may be split across chunks."""

    _MAX_PLACEHOLDER = 24

    def __init__(self, mapping: dict[str, str]) -> None:
        self._mapping = mapping
        self._buf = ""

    def feed(self, delta: str) -> str:
        self._buf += delta
        cut = self._buf.rfind("<")
        if (
            cut != -1
            and ">" not in self._buf[cut:]
            and len(self._buf) - cut <= self._MAX_PLACEHOLDER
        ):
            ready, self._buf = self._buf[:cut], self._buf[cut:]
        else:
            ready, self._buf = self._buf, ""
        return unmask(ready, self._mapping)

    def flush(self) -> str:
        ready, self._buf = self._buf, ""
        return unmask(ready, self._mapping)
