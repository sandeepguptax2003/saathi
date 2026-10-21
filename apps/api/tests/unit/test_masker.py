from __future__ import annotations

import pytest

from saathi_api.modules.privacy.masker import (
    MaskSession,
    StreamUnmasker,
    luhn_ok,
    mask_text,
    unmask,
)


@pytest.mark.parametrize(
    ("text", "entity", "token"),
    [
        ("Call me on +91 98765 43210 please", "phone", "<PHONE_1>"),
        ("mera number 9876543210 hai", "phone", "<PHONE_1>"),
        ("Aadhaar 2345 6789 0123 hai", "aadhaar", "<AADHAAR_1>"),
        ("aadhaar 234567890123", "aadhaar", "<AADHAAR_1>"),
        ("PAN ABCPE1234F submit karo", "pan", "<PAN_1>"),
        ("mail priya.sharma@example.com", "email", "<EMAIL_1>"),
        ("UPI pe bhejo priya@okhdfcbank", "upi", "<UPI_1>"),
        ("card 4111 1111 1111 1111 se", "card", "<CARD_1>"),
        ("IFSC HDFC0001234 hai", "ifsc", "<IFSC_1>"),
        ("account no. 123456789012 me", "account", "<ACCOUNT_1>"),
    ],
)
def test_masks_each_indian_pii_type(text: str, entity: str, token: str) -> None:
    result, mapping = mask_text(text)
    assert token in result.masked_text
    assert result.entity_counts[entity] == 1
    assert unmask(result.masked_text, mapping) == text


def test_email_is_not_double_counted_as_upi() -> None:
    result, _ = mask_text("write to a.b@gmail.com and pay a.b@okaxis")
    assert result.entity_counts["email"] == 1
    assert result.entity_counts["upi"] == 1


def test_invalid_luhn_long_number_is_not_a_card() -> None:
    assert not luhn_ok("4111111111111112")
    result, _ = mask_text("order id 4111111111111112")
    assert result.entity_counts["card"] == 0


def test_same_value_reuses_token_and_counts_occurrences() -> None:
    s = MaskSession()
    r = s.mask("9876543210 aur phir se 98765-43210, naya 9123456780")
    assert r.masked_text.count("<PHONE_1>") == 2
    assert "<PHONE_2>" in r.masked_text
    assert r.entity_counts["phone"] == 3


def test_tokens_stay_stable_across_calls_in_one_session() -> None:
    s = MaskSession()
    s.mask("Pay 9876543210")
    second = s.mask("Remind 9876543210 again")
    assert "<PHONE_1>" in second.masked_text


def test_known_names_are_masked_case_insensitively() -> None:
    r, mapping = mask_text("Sunita aunty ko bolo, sunita ji aayengi", known_names=["Sunita"])
    assert r.entity_counts["name"] == 2
    assert "sunita" not in r.masked_text.lower()
    assert mapping["<NAME_1>"] == "Sunita"


def test_plain_text_and_amounts_untouched() -> None:
    text = "Kal subah 9 baje ₹1,249 ka bill yaad dilana, 2026-10-21 ko"
    r, _ = mask_text(text)
    assert r.masked_text == text
    assert sum(r.entity_counts.values()) == 0


def test_unmask_leaves_unknown_placeholders() -> None:
    assert unmask("hi <PHONE_9>", {"<PHONE_1>": "x"}) == "hi <PHONE_9>"


def test_stream_unmasker_handles_split_placeholders() -> None:
    um = StreamUnmasker({"<PHONE_1>": "98765 43210"})
    out = "".join(um.feed(c) for c in ["Call ", "<PHO", "NE_", "1> now", " <"]) + um.flush()
    assert out == "Call 98765 43210 now <"
