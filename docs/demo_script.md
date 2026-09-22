# Two-minute demonstration

**0:00–0:20 — The business question.** Open Executive Overview. “Payment risk is a tradeoff: stop fraudulent transfers while preserving legitimate customer access. These 100,000 events are entirely synthetic.” Point to payment volume, potential prevented exposure, confirmed loss and legitimate blocks. Explain that review dollars are not counted as prevented.

**0:20–0:45 — Explain a suspicious payment.** Open Transaction Monitor, select Critical risk, inspect a transaction. Show the rule explanations and score contributions. “An anomaly is unusual behavior, not proof of fraud.” Review customer/device evidence and event timeline. Click Open investigation.

**0:45–1:05 — Make an accountable decision.** Open Investigation Workbench. Assign the case to Demo Analyst, add an evidence-based note, choose Request verification and a reason code, and set In review. Save. Show the persisted audit history and links among customer, device, IP, bank and recipient.

**1:05–1:30 — Challenge the policy.** Open Rule Performance. Highlight false alerts and overlapping captures. Switch to Rule Simulator as manager. Set R01=2500, R11=5, R12=10, decision threshold=55. Confirm settings and run. Explain the measured changes, including the increase in legitimate-dollar exposure even when false-alert count decreases. No baseline policy changes.

**1:30–1:45 — Be honest about the model.** Open Model Performance. “This is a chronological 70/30 split. The combined score ranks better by ROC-AUC, but at the default threshold it has lower recall than rules alone. That is why the interface shows customer friction and operating points.”

**1:45–2:00 — Translate to leadership.** Show SQL Explorer's rule-performance join, then Leadership Recommendations and download the HTML report. “Every recommendation cites a metric. Next step: validate on untouched data and test additional verification, not blindly ship a block rule.”
