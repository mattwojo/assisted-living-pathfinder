# Security Review

## Scope

The repository was reviewed for exposed API keys, access tokens, passwords,
private keys, and secret-bearing configuration.

## Findings

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| 1 | ⚪ LOW | `backend/app/seed.py`; `backend/app/routes/accounts.py` | 13; 48-50 | An intentionally documented demo credential is hard-coded and returned for local sample accounts. It is unsafe if reused outside local development. | 10/10 |

No real API keys, access tokens, private keys, or production secrets were found
in tracked files or reachable Git history.

The application README explicitly identifies the credential as development-only
and warns not to deploy the prototype as-is or enter sensitive information.
