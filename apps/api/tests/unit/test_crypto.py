from __future__ import annotations

import uuid

import pytest

from saathi_api.core.crypto import DecryptionError, Encryptor

P1 = b"p" * 40
P2 = b"q" * 40


def test_roundtrip_and_nonce_uniqueness() -> None:
    enc = Encryptor({1: P1}, 1)
    uid = uuid.uuid4()
    a = enc.encrypt(uid, "Maa ka birthday 12 March", purpose="memory")
    b = enc.encrypt(uid, "Maa ka birthday 12 March", purpose="memory")
    assert a.nonce != b.nonce and a.ciphertext != b.ciphertext
    assert len(a.nonce) == 12 and a.key_version == 1
    assert enc.decrypt_str(uid, a, purpose="memory") == "Maa ka birthday 12 March"


def test_per_user_keys_and_purpose_binding() -> None:
    enc = Encryptor({1: P1}, 1)
    alice, bob = uuid.uuid4(), uuid.uuid4()
    blob = enc.encrypt(alice, "secret", purpose="memory")
    with pytest.raises(DecryptionError):
        enc.decrypt(bob, blob, purpose="memory")
    with pytest.raises(DecryptionError):
        enc.decrypt(alice, blob, purpose="reminder")


def test_tamper_detected() -> None:
    enc = Encryptor({1: P1}, 1)
    uid = uuid.uuid4()
    blob = enc.encrypt(uid, "x", purpose="memory")
    bad = type(blob)(
        bytes([blob.ciphertext[0] ^ 1]) + blob.ciphertext[1:], blob.nonce, blob.key_version
    )
    with pytest.raises(DecryptionError):
        enc.decrypt(uid, bad, purpose="memory")


def test_key_rotation_reads_old_writes_new() -> None:
    uid = uuid.uuid4()
    old = Encryptor({1: P1}, 1).encrypt(uid, "old data", purpose="memory")
    rotated = Encryptor({1: P1, 2: P2}, 2)
    assert rotated.decrypt_str(uid, old, purpose="memory") == "old data"
    assert rotated.needs_rotation(old.key_version)
    assert rotated.encrypt(uid, "new", purpose="memory").key_version == 2
    with pytest.raises(DecryptionError):
        Encryptor({2: P2}, 2).decrypt(uid, old, purpose="memory")


def test_seal_open_packs_version() -> None:
    uid = uuid.uuid4()
    enc = Encryptor({1: P1, 3: P2}, 3)
    sealed = enc.seal(uid, '{"amountInr": 1249}', purpose="pending_action")
    assert enc.open(uid, sealed, purpose="pending_action") == b'{"amountInr": 1249}'
    with pytest.raises(DecryptionError):
        enc.open(uid, b"short", purpose="pending_action")


def test_current_version_requires_pepper() -> None:
    with pytest.raises(ValueError, match="no pepper"):
        Encryptor({1: P1}, 2)
