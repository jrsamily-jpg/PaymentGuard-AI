# SQL analytics library
These 16 checked-in, read-only queries drive the dashboard SQL Explorer. Both SQLite and PostgreSQL support the used `SUBSTR`, CTE, CASE, window and aggregation expressions. No user-authored SQL is executed. Full-cohort investigation queries deliberately describe historical relationships; scoring features only use relationships observed at event time.

01–03: volume, fraud rate and realized synthetic loss. 04: ranked customers. 05: prior-event window plus synthetic upstream velocity. 06–07: device and geographic investigation. 08: synthetic ACH returns. 09–10: cohort bands. 11: rule hits joined to labels. 12–13: legitimate-customer friction. 14: difference from the previous *observed* day per fraud category; missing dates are not zero-filled. 15: unassigned or unresolved reviews. 16: authentication cohorts.

Money is USD and sums do not cross currencies. Rule captures overlap and must never be added to infer distinct captured dollars. False-positive rate divides false alerts by all legitimate payments, while precision divides true alerts by all alerts. SQL truth labels exist for demo evaluation only.
