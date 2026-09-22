# Operational security boundaries

The default application uses individual accounts and an independent operational database. Browser → Streamlit or authenticated API → owner-scoped services → database. Local machine and database administrators remain trusted. Historical synthetic research runs separately and is not consulted by this runtime.

| Threat | Implemented control | Remaining boundary |
|---|---|---|
| Cross-user disclosure | Owner comes from a hashed, expiring bearer session; every data query and mutation filters by owner; caller owner fields rejected | Application-level isolation, not PostgreSQL row-level security; add organization tenancy and independent review before multi-organization deployment |
| Password or token theft | Salted scrypt; constant-time verification; session tokens stored only as SHA-256 hashes; logout revocation; 12-hour expiry | Configure TLS, managed SSO/MFA, recovery, session inventory and deployment secrets; local SQLite is not encrypted by this application |
| Credential guessing | Five failures per username within 15 minutes | Distributed edge rate limiting, registration limits, abuse monitoring, and anti-lockout design needed; concurrent attempt throttling is not a security certification |
| Incorrect or fabricated results | No default events; unknown outcomes remain unknown; missing evidence is unevaluated; no synthetic ML scores | Submitted statuses/evidence are trusted assertions, not independently verified settlement or fraud findings |
| Import corruption | Bounded, typed inputs; two-decimal amounts stored as integer cents; per-owner unique references; atomic batches and audit | Source reconciliation, signed provenance, correction workflows, and provider idempotency integration remain future work |
| Injection | SQLAlchemy parameter binding; HTML escaping; constrained references; CSV uses a fixed schema | Review every new free-text export and third-party integration; do not upload credentials or unnecessary personal data |
| Lost case updates | Version-conditional update and audit committed together | Database administrators can edit audit records; use independently retained append-only audit export for higher assurance |
| Resource exhaustion | 2 MB CSV/5,000-event import bounds; 5 MB API body limit including missing Content-Length; bounded API pagination and field lengths | All-owner analytics and simulations run in memory; add quotas, job isolation, timeouts and incremental aggregation for scale |
| Unintended payment action | Analysis and recorded case decisions only; no payment execution integration | Real-world transaction enforcement requires a separate reviewed, authorized integration |
| Operational loss | Persistent separate database; Docker PostgreSQL volume; container services run non-root and bind published ports to loopback | Migrations, encrypted backups, restore tests, monitoring, and incident procedures must be established before public production use |

No compliance certification, independent security assessment, Coinbase endorsement, or production payment connectivity is asserted. Existing tests establish specific local behavior, not universal security guarantees. The historical role-key research runtime has separate limitations and must not be deployed publicly as the operational product.
