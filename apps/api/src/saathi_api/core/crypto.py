"""AES-256-GCM field encryption with per-user keys derived via HKDF-SHA256.

key = HKDF(ikm=ENCRYPTION_PEPPER[v], salt="saathi:data-key:v{v}", info="saathi:user:" + user_id)
AAD binds every ciphertext to (purpose, user_id) so rows cannot be swapped between users/tables.
`seal()` packs version|nonce|ciphertext into one blob for single-column storage.
"""

from __future__ import annotations

import os
import struct
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

NONCE_LEN = 12
_PACK_MAGIC = 0x53  # "S"
_HEADER = struct.Struct(">BH")  # magic, key_version


class DecryptionError(Exception):
    """Ciphertext failed authentication or its key version is unknown."""


@dataclass(frozen=True, slots=True)
class EncryptedBlob:
    ciphertext: bytes
    nonce: bytes
    key_version: int


class Encryptor:
    def __init__(self, peppers: Mapping[int, bytes], current_version: int) -> None:
        if current_version not in peppers:
            raise ValueError("current key version has no pepper")
        self._peppers = dict(peppers)
        self.current_version = current_version
        self._derive = lru_cache(maxsize=4096)(self._derive_uncached)

    def _derive_uncached(self, user_id: uuid.UUID, version: int) -> bytes:
        pepper = self._peppers.get(version)
        if pepper is None:
            raise DecryptionError(f"unknown key version {version}")
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=f"saathi:data-key:v{version}".encode(),
            info=b"saathi:user:" + user_id.bytes,
        )
        return hkdf.derive(pepper)

    @staticmethod
    def _aad(user_id: uuid.UUID, purpose: str) -> bytes:
        return purpose.encode() + b"|" + user_id.bytes

    def encrypt(self, user_id: uuid.UUID, plaintext: str | bytes, *, purpose: str) -> EncryptedBlob:
        data = plaintext.encode() if isinstance(plaintext, str) else plaintext
        nonce = os.urandom(NONCE_LEN)
        key = self._derive(user_id, self.current_version)
        ct = AESGCM(key).encrypt(nonce, data, self._aad(user_id, purpose))
        return EncryptedBlob(ciphertext=ct, nonce=nonce, key_version=self.current_version)

    def decrypt(self, user_id: uuid.UUID, blob: EncryptedBlob, *, purpose: str) -> bytes:
        key = self._derive(user_id, blob.key_version)
        try:
            return AESGCM(key).decrypt(blob.nonce, blob.ciphertext, self._aad(user_id, purpose))
        except InvalidTag as exc:
            raise DecryptionError("ciphertext authentication failed") from exc

    def decrypt_str(self, user_id: uuid.UUID, blob: EncryptedBlob, *, purpose: str) -> str:
        return self.decrypt(user_id, blob, purpose=purpose).decode()

    def seal(self, user_id: uuid.UUID, plaintext: str | bytes, *, purpose: str) -> bytes:
        blob = self.encrypt(user_id, plaintext, purpose=purpose)
        return _HEADER.pack(_PACK_MAGIC, blob.key_version) + blob.nonce + blob.ciphertext

    def open(self, user_id: uuid.UUID, sealed: bytes, *, purpose: str) -> bytes:
        if len(sealed) < _HEADER.size + NONCE_LEN + 16:
            raise DecryptionError("sealed blob too short")
        magic, version = _HEADER.unpack_from(sealed)
        if magic != _PACK_MAGIC:
            raise DecryptionError("bad sealed blob header")
        nonce = sealed[_HEADER.size : _HEADER.size + NONCE_LEN]
        ct = sealed[_HEADER.size + NONCE_LEN :]
        return self.decrypt(user_id, EncryptedBlob(ct, nonce, version), purpose=purpose)

    def needs_rotation(self, key_version: int) -> bool:
        return key_version != self.current_version
