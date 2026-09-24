# GitHub Pages browser edition

Open https://jrsamily-jpg.github.io/PaymentGuard-AI/workspace.html. No local Python process, server account, or installation is required.

The browser edition supports manual payment entry, previewed CSV imports, payment search and status filters, activity charts, twelve evidence-only risk checks, investigation notes and history, CSV exports, and full JSON backup/restore. New browser profiles start with zero records. The welcome page opens this workspace directly.

Records use localStorage on the GitHub Pages origin. There is no authentication, encryption at rest provided by this application, cloud storage, or device synchronization. Users sharing a browser profile share its records. Browser privacy settings, storage limits, or clearing site data can prevent saving or remove records. Download backups regularly. Concurrent-tab changes prevent saves until reload. Imports reject duplicate references and invalid rows before saving the batch. Full restore and clearing require confirmation.

Limits: 5,000 rows / 2 MB per CSV import, 10,000 payments per browser workspace, 20 MB per backup input (actual browser storage may be smaller). No payment processing, independent verification of reported evidence, operational ML model, or tamper-proof audit trail is provided. Manual entry exposes common evidence fields; JSON evidence supports the complete rule set shown in Risk controls.

The Python/FastAPI/Streamlit edition remains separate and unchanged. Its accounts and existing records are not automatically migrated to this browser edition.

Verification: `node --test tests/browser.test.mjs` checks integer cents, missing evidence, all 12 rules, invalid inputs, duplicate import rejection, CSV quoting, safe CSV output, and backup restoration above 5,000 records. Browser UI checks covered empty totals, manual entry, investigation notes, persistence across reload, and the mobile data page. Test records were created only on the temporary preview origin, not on the public site.
