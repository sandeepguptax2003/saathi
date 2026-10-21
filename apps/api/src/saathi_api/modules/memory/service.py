from __future__ import annotations

import uuid

from saathi_api.core.crypto import EncryptedBlob, Encryptor
from saathi_api.core.errors import NotFound
from saathi_api.core.logging import get_logger
from saathi_api.core.pagination import PageParams, encode_cursor
from saathi_api.modules.llm.service import LLMService
from saathi_api.modules.memory.models import Memory
from saathi_api.modules.memory.repository import MemoryRepository
from saathi_api.modules.memory.schemas import DeletedOut, MemoryIn, MemoryOut, MemoryPatch
from saathi_api.modules.privacy.masker import MaskSession

log = get_logger(__name__)
PURPOSE = "memory"


class MemoryService:
    def __init__(self, repo: MemoryRepository, encryptor: Encryptor, llm: LLMService) -> None:
        self.repo = repo
        self.enc = encryptor
        self.llm = llm

    def _out(self, m: Memory, score: float | None = None) -> MemoryOut:
        content = self.enc.decrypt_str(
            m.user_id, EncryptedBlob(m.content_ciphertext, m.nonce, m.key_version), purpose=PURPOSE
        )
        return MemoryOut(
            id=m.id,
            kind=m.kind,  # type: ignore[arg-type]
            content=content,
            source=m.source,
            key_version=m.key_version,
            created_at=m.created_at,
            updated_at=m.updated_at,
            score=score,
        )

    async def _embedding(self, text: str) -> list[float] | None:
        """Embed MASKED text only. Failure is non-fatal: the memory is stored without a vector."""
        masked = MaskSession().mask(text).masked_text
        try:
            return (await self.llm.embed([masked]))[0]
        except Exception as exc:
            log.warning("memory_embed_failed", error=type(exc).__name__)
            return None

    async def create(self, user_id: uuid.UUID, body: MemoryIn) -> MemoryOut:
        blob = self.enc.encrypt(user_id, body.content, purpose=PURPOSE)
        memory = Memory(
            user_id=user_id,
            kind=body.kind,
            content_ciphertext=blob.ciphertext,
            nonce=blob.nonce,
            key_version=blob.key_version,
            embedding=await self._embedding(body.content),
            source=body.source,
        )
        memory = await self.repo.add(memory)
        await self.repo.commit()
        return self._out(memory)

    async def list_page(
        self, user_id: uuid.UUID, kind: str | None, page: PageParams
    ) -> tuple[list[MemoryOut], str | None]:
        rows = await self.repo.list_page(user_id, kind, page)
        next_cursor = None
        if len(rows) > page.limit:
            rows = rows[: page.limit]
            next_cursor = encode_cursor(rows[-1].created_at, rows[-1].id)
        return [self._out(r) for r in rows], next_cursor

    async def search(
        self, user_id: uuid.UUID, q: str, kind: str | None, limit: int
    ) -> list[MemoryOut]:
        vector = await self._embedding(q)
        if vector is None:
            return []
        return [
            self._out(m, score) for m, score in await self.repo.search(user_id, vector, kind, limit)
        ]

    async def update(
        self, user_id: uuid.UUID, memory_id: uuid.UUID, patch: MemoryPatch
    ) -> MemoryOut:
        memory = await self.repo.get(user_id, memory_id)
        if memory is None:
            raise NotFound("Memory not found")
        if patch.kind is not None:
            memory.kind = patch.kind
        if patch.content is not None:
            blob = self.enc.encrypt(user_id, patch.content, purpose=PURPOSE)
            memory.content_ciphertext, memory.nonce = blob.ciphertext, blob.nonce
            memory.key_version = blob.key_version
            memory.embedding = await self._embedding(patch.content)
        await self.repo.commit()
        return self._out(memory)

    async def delete(self, user_id: uuid.UUID, memory_id: uuid.UUID, *, hard: bool) -> DeletedOut:
        if hard:
            if not await self.repo.hard_delete(user_id, memory_id):
                raise NotFound("Memory not found")
        else:
            memory = await self.repo.get(user_id, memory_id)
            if memory is None:
                raise NotFound("Memory not found")
            await self.repo.soft_delete(memory)
        await self.repo.commit()
        return DeletedOut(id=memory_id, hard=hard)
