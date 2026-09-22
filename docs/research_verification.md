# Verification record

Local implementation completed September 21, 2026. Python 3.13.13, SQLite, synthetic seed 42. No public deployment or real customer data.

## Results
- **46 tests passed** with **100% core-risk-engine statement and branch coverage** (119 statements, 28 branches); 80% gate enforced.
- **All nine Streamlit pages** rendered through Streamlit AppTest without exceptions. Tests exercised a confirmed simulation, an empty search, case creation, assignment, verification decision, note persistence and two audit events. Tests run in an isolated temporary DB/cohort.
- **16/16 SQL queries** executed on the 100,000-row SQLite cohort.
- **100,000 synthetic transactions** persisted with 2,642 fraud labels. Isolation Forest fit on 70,000 earlier rows and evaluated on 30,000 later rows.
- Full-cohort API smoke checks include health, list/detail/explanation, summary/trends, rules/performance, cases, model results, recommendations, HTML report and OpenAPI schema. Automated API tests cover create/update, validation, unknown IDs, duplicate cases, role restrictions and stale writes.
- Ruff undefined-name/unused-import checks passed; all Python source formatted.
- `scripts.ensure_data` recognized the existing cohort without overwriting it. Documentation and case-study results were generated from measured outputs.
- Docker Compose configuration parsed successfully with a non-secret validation-only password value.

## Limits of verification
The initial build could not be visually inspected because the browser policy check was unavailable. On September 22, browser access worked after restarting the local server. The redesigned overview was inspected at desktop and 390×844 phone dimensions, and the review-queue shortcut was verified in the live browser. The README image is labelled artwork, not a screenshot. These checks are not an exhaustive cross-browser accessibility audit.

Docker is installed, but its daemon was not running. **Container startup and live PostgreSQL execution were not locally tested.** A PostgreSQL CI job and Python 3.11/3.12/3.13 matrix are provided but have not run on GitHub. This local run tested Python 3.13 only. Two dependency deprecation warnings occurred in Starlette/TestClient; no test failed.

Core coverage describes tested code paths, not guarantees about real fraud detection, security, or production behavior. Synthetic-data and threat-model limitations remain explicit in the README.

## Implementation phases and files
1. **Foundation:** `app/database/`, `app/models/schemas.py`, `app/services/generation.py`, environment/dependency setup and bootstrap; reproducibility, validation and DB/API tests passed.
2. **Risk intelligence:** `app/risk_engine/`, analytics, 16 files in `sql/`, 100,000-row build and chronological model evaluation; initial 25 tests passed at 100% engine statement coverage.
3. **Product experience:** `app/api/`, `app/dashboard/`, original `app/dashboard/assets/network-art.png`; all nine pages plus investigation and simulation interaction checks passed.
4. **Security and reporting:** role-key checks, bounded synthetic CSV validation, transactional audit/concurrency, report generation and threat model; expanded security/invalid-input tests passed.
5. **Portfolio polish:** complete README, seven requested documentation files, art specification, report, case study, résumé bullets, Docker/Compose/CI, formatting and final 46-test suite. Visual/browser and container limitations recorded above.

## September 22 design and usability refinement

- New original orbital artwork, preserved alongside the first version. Local stylesheet and system fonts, consistent graphite/emerald palette, compact operational headers, clearer navigation and shorter metric labels.
- Overview shortcuts to unresolved reviews, manager-only simulation and report export. Review filtering excludes closed investigations. Transaction CSV export follows active filters with a disclosed 10,000-row cap.
- Structured customer/device evidence table, exact transaction dollar amounts and one-decimal scores preserve meaningful policy boundaries.
- 46 tests passed again with 100% core-engine statement and branch coverage; the dashboard test now verifies the review shortcut and selected review filter as well as all nine pages and persistent case decisions. Ruff checks passed.
- Live browser showed 879 review payments after using the shortcut. Desktop and phone-sized screenshots were inspected; mobile sidebar collapse was verified and the temporary viewport override was reset.

## Operational presentation refinement
Replaced the promotional overview with a compact operational heading, restrained the existing artwork, tightened card and action styling, simplified navigation visuals while preserving native keyboard-accessible inputs, and added five highest-scoring unresolved reviews to the overview. Narrow desktop windows wrap metric cards into two columns and stack chart panels. The existing dashboard interaction test passed again across all nine pages, queue navigation, simulation and case updates. Core risk logic was unchanged.

## Overview usability update
Added an exact-count risk distribution with percentages and score bands, daily/weekly activity aggregation with partial-week disclosure, and a priority-payment shortcut that opens the selected payment in Transaction Monitor. The dashboard test now checks the selected transaction survives navigation, then exercises queue filtering, all pages, simulation and case history. The updated dashboard test passed; weekly aggregation and the risk summary were also checked in the browser.
