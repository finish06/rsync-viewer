# Implementation Plan: OIDC Signature Verification

**Spec Version:** 0.1.0
**Spec:** specs/oidc-signature-verification.md
**Created:** 2026-03-15
**Team Size:** Solo (agent)
**Estimated Duration:** 1-2 hours

## Overview

Replace `verify_signature: False` in `decode_id_token()` with proper JWKS-based verification using `authlib`. Add a JWKS cache with configurable TTL alongside the existing discovery cache.

## Implementation Phases

### Phase 1: Setup (AC-001, AC-008)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-001 | Add `authlib` to `requirements.txt` | 2min | None |
| TASK-002 | Add `oidc_jwks_cache_ttl_seconds: int = 3600` to `app/config.py` | 2min | None |

### Phase 2: JWKS Fetching + Caching (AC-002, AC-007, AC-011)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-003 | Add JWKS fetch function with TTL cache to `app/services/oidc.py` | 20min | TASK-001 |

**Approach:** Mirror the existing `_discovery_cache` pattern. Add `_jwks_cache: dict[str, tuple[JsonWebKey, float]]` at module level. New function:

```python
async def fetch_jwks(jwks_uri: str) -> JsonWebKey:
    """Fetch and cache JWKS from provider. TTL from config."""
```

- Uses `authlib.jose.JsonWebKey.import_key_set()` to parse the JWKS response
- 10-second timeout (AC-011)
- Cache keyed by `jwks_uri`, TTL from `settings.oidc_jwks_cache_ttl_seconds`
- Add `clear_jwks_cache()` for testing

### Phase 3: Signature Verification (AC-003, AC-004, AC-005, AC-006, AC-009, AC-010, AC-014)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-004 | Rewrite `decode_id_token()` to verify signature via JWKS | 30min | TASK-003 |

**Approach:** Replace `pyjwt.decode(verify_signature=False)` with:

1. Extract `kid` from token header (unverified decode of header only)
2. Fetch JWKS via `fetch_jwks()` (uses discovery doc's `jwks_uri`)
3. Use `authlib.jose.jwt.decode()` with the JWKS key set for full verification
4. Validate `iss`, `aud`, `exp`, `nonce` claims
5. On any failure (fetch error, invalid sig, bad claims): raise `ValueError` → caller redirects to `/login?error=oidc_failed`

**Key change:** The function signature gains a `jwks_uri` parameter (from discovery doc), or we pass the discovery doc itself.

### Phase 4: Integration (AC-012, AC-013)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-005 | Update `app/routes/auth.py` OIDC callback to pass `jwks_uri` to `decode_id_token()` | 10min | TASK-004 |

The callback already calls `fetch_discovery()` then `decode_id_token()`. We add the `jwks_uri` from the discovery doc to the call.

### Phase 5: Tests (all ACs)

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-006 | Write/update tests in `tests/test_oidc_auth.py` | 30min | TASK-004 |

Tests needed:
- Valid token with correct signature → accepted (TC-001)
- Token with wrong signature → rejected (TC-002, AC-010)
- JWKS fetch failure → rejected with redirect (TC-003, AC-009)
- JWKS caching works (TC-004, AC-007)
- Expired token → rejected (TC-005, AC-006)
- Wrong issuer → rejected (AC-004)
- Wrong audience → rejected (AC-005)
- Unsupported algorithm (`none`) → rejected (edge case)

**Mock strategy:** Use `authlib.jose.jwt.encode()` to create real signed test tokens with a test RSA key pair. Mock the JWKS endpoint to return the test public key.

### Phase 6: Verify

| Task ID | Description | Effort | Dependencies |
|---------|-------------|--------|--------------|
| TASK-007 | Run full test suite, mypy, ruff | 5min | TASK-006 |

## Effort Summary

| Phase | Tasks | Effort |
|-------|-------|--------|
| Setup | 2 | 5 min |
| JWKS fetch + cache | 1 | 20 min |
| Signature verification | 1 | 30 min |
| Integration | 1 | 10 min |
| Tests | 1 | 30 min |
| Verify | 1 | 5 min |
| **Total** | **7** | **~100 min** |

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| `authlib` API differs from expected | Low | Medium | Read authlib docs; well-documented library |
| Existing OIDC tests break | Medium | Low | Tests use `pyjwt.decode` mocks — update mocks to match new flow |
| Provider-specific JWKS quirks | Low | Medium | Test with standard RSA keys; edge cases in spec |

## File Changes

| File | Change |
|------|--------|
| `requirements.txt` | Add `authlib>=1.3.0` |
| `app/config.py` | Add `oidc_jwks_cache_ttl_seconds` field |
| `app/services/oidc.py` | Add `fetch_jwks()`, rewrite `decode_id_token()` |
| `app/routes/auth.py` | Pass discovery doc to `decode_id_token()` |
| `tests/test_oidc_auth.py` | Update/add signature verification tests |

## Next Steps

1. Approve this plan
2. Implement directly or via `/add:tdd-cycle`
