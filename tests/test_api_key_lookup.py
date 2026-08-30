"""AC-004 (specs/security-hardening-v2.md): legacy API-key fallback is bounded.

An unknown 8-char prefix must trigger bcrypt only against keys that have no
stored prefix (legacy rows), never against every active key; successful
legacy auth logs a rotation warning.
"""

import logging
from unittest.mock import patch

import pytest
from sqlmodel import Session

from app.api.deps import _lookup_and_verify_api_key
from app.models.sync_log import ApiKey
from app.services.auth import hash_password


def _add_key(db_session: Session, name: str, raw: str, prefix: str) -> ApiKey:
    key = ApiKey(
        name=name,
        key_hash=hash_password(raw),
        key_prefix=prefix,
        is_active=True,
    )
    db_session.add(key)
    db_session.flush()
    return key


@pytest.fixture()
def keys(db_session):
    _add_key(db_session, "prefixed-1", "rsv_aaaa_secret1", "rsv_aaaa")
    _add_key(db_session, "prefixed-2", "rsv_bbbb_secret2", "rsv_bbbb")
    legacy = _add_key(db_session, "legacy-key", "old-style-key-123", "")
    # Pre-prefix rows can also carry NULL instead of "".
    null_prefix = ApiKey(
        name="legacy-null",
        key_hash=hash_password("null-style-key-456"),
        key_prefix=None,
        is_active=True,
    )
    db_session.add(null_prefix)
    db_session.commit()
    return legacy


class TestAC004LegacyFallback:
    def test_ac004_unknown_prefix_only_checks_legacy_keys(self, db_session, keys):
        with patch(
            "app.api.deps.verify_api_key_hash", return_value=False
        ) as verify_mock:
            result = _lookup_and_verify_api_key("zzzzzzzz-unknown", db_session)
        assert result is None
        # Only the legacy (empty/NULL prefix) keys were checked.
        assert verify_mock.call_count == 2

    def test_ac004_known_prefix_never_scans_other_keys(self, db_session, keys):
        with patch(
            "app.api.deps.verify_api_key_hash", return_value=False
        ) as verify_mock:
            _lookup_and_verify_api_key("rsv_aaaa_wrong-secret", db_session)
        assert verify_mock.call_count == 1

    def test_ac004_legacy_key_auth_logs_warning(self, db_session, keys, caplog):
        with caplog.at_level(logging.WARNING, logger="app.api.deps"):
            result = _lookup_and_verify_api_key("old-style-key-123", db_session)
        assert result is not None
        assert result.name == "legacy-key"
        assert any("legacy API key" in r.message for r in caplog.records)

    def test_ac004_prefixed_key_auth_has_no_warning(self, db_session, keys, caplog):
        with caplog.at_level(logging.WARNING, logger="app.api.deps"):
            result = _lookup_and_verify_api_key("rsv_aaaa_secret1", db_session)
        assert result is not None
        assert not any("legacy API key" in r.message for r in caplog.records)
