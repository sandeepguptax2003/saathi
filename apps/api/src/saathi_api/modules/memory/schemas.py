from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from saathi_api.core.schemas import CamelModel

MemoryKind = Literal["fact", "preference", "person", "note"]
MemorySource = Literal["user", "assistant", "import"]


class MemoryIn(CamelModel):
    kind: MemoryKind
    content: str = Field(min_length=1, max_length=2000)
    source: MemorySource = "user"


class MemoryPatch(CamelModel):
    kind: MemoryKind | None = None
    content: str | None = Field(default=None, min_length=1, max_length=2000)


class MemoryOut(CamelModel):
    id: uuid.UUID
    kind: MemoryKind
    content: str
    source: str | None
    key_version: int
    created_at: datetime
    updated_at: datetime
    score: float | None = None


class DeletedOut(CamelModel):
    id: uuid.UUID
    deleted: bool = True
    hard: bool
