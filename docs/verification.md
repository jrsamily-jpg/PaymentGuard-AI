# Operational verification — September 22, 2026

73 tests passed on Python 3.13.13 with SQLite. This includes 27 operational tests and 46 retained research tests. Operational tests use temporary databases and do not create users or payments in the live workspace.

Verified behavior:

- New accounts have zero volume, payments, losses, blocked fraud and cases. Unavailable rates and model metrics remain unknown.
- Two-account isolation covers payment detail and explanations, cases, updates, audit records, rail analytics and reports. Shared external references are allowed across different owners.
- Password hashes, hashed sessions, expiry, logout revocation, return-user persistence, invalid-token rejection and login throttling.
- Atomic duplicate rejection; strict field validation; money precision; CSV bounds; API pagination and request-body size checks.
- All twelve operational rules trigger from supplied evidence. Missing evidence stays unevaluated and unknown outcomes are never treated as legitimate labels.
- All nine operational pages render before and after a payment is entered. Dashboard tests create an account, record a payment, open and update an investigation, verify a second user remains empty, and sign out back to $0.
- The live API returned HTTP 200 for health and HTTP 401 for anonymous transaction access.
- Read-only inspection of the actual operational store found zero accounts, zero payment events and zero investigations. Historical research data is stored separately.
- Original shield artwork, $0 dashboard and account screen were visually inspected in the in-app browser. Form-button contrast was corrected. These checks are not a comprehensive accessibility audit.
- Ruff checks passed for the operational implementation and tests. Docker Compose configuration validated. Default launch and container paths no longer generate synthetic payments; operational storage is excluded from Docker builds.

Core research risk-engine statement coverage remains 100% (119 statements). That number does not describe operational workspace coverage or certify fraud effectiveness. The operational checks listed above are separate behavior tests.

Limits: container startup and live PostgreSQL were not exercised locally; the GitHub Python-version matrix has not been run here. Two TestClient dependency deprecation warnings occurred without failures. No payment processor is connected, no operational machine-learning model is evaluated, and no public production deployment or independent security certification is claimed. Deployment requirements are documented in README and the threat model.

Prior synthetic-only verification is retained in [the research archive](research_verification.md).
