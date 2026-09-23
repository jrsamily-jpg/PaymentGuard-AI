"""Operational presentation: empty by default, persistent only within an authenticated owner."""

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html import escape

import pandas as pd
import plotly.express as px
import streamlit as st
from pydantic import ValidationError

from app.dashboard.theme import COLORS, chart, hero, section, theme
from app.dashboard.welcome import return_to_welcome, welcome
from app.risk_engine.rules import RULES
from app.workspace import auth, service
from app.workspace.database import Session, initialize
from app.workspace.schemas import (
    CaseChange,
    Credentials,
    Evidence,
    PaymentInput,
    SimulationRequest,
)

PAGES = [
    "Overview",
    "Payments",
    "Investigations",
    "Trends",
    "Controls",
    "Policy simulator",
    "Model evaluation",
    "Reports",
    "Data & access",
]


def route(page: str, account_action: str | None = None) -> None:
    st.session_state["workspace_page"] = page
    st.session_state["workspace_entered"] = True
    if account_action:
        st.session_state["workspace_auth_mode"] = account_action


def empty(title: str, body: str) -> None:
    st.markdown(
        f'<div class="workspace-empty"><span class="empty-icon">◇</span><h3>{escape(title)}</h3><p>{escape(body)}</p></div>',
        unsafe_allow_html=True,
    )


def metric(label: str, value: str, help_text: str) -> None:
    st.metric(label, value, help=help_text)


def money(value: float) -> str:
    return f"${value:,.2f}" if value else "$0"


def signout() -> None:
    token = st.session_state.get("workspace_token")
    if token:
        with Session() as session:
            auth.logout(session, token)
    st.session_state.clear()
    st.session_state["workspace_page"] = "Overview"


def form_error(error: Exception) -> str:
    """Readable validation without echoing submitted values, including passwords."""
    if isinstance(error, ValidationError):
        labels = {
            "external_id": "Payment reference",
            "customer_ref": "Customer reference",
            "occurred_at": "Payment time",
        }
        return "Please check: " + "; ".join(
            f"{labels.get(str(item['loc'][-1]), str(item['loc'][-1]).replace('_', ' ').capitalize())}: {item['msg']}"
            for item in error.errors(
                include_input=False, include_context=False, include_url=False
            )[:4]
        )
    if isinstance(error, InvalidOperation):
        return "Enter an amount in USD, such as 25.50."
    if isinstance(error, json.JSONDecodeError):
        return (
            "Risk context must be a valid JSON object. Leave it blank if unavailable."
        )
    return str(error)


def account_forms() -> None:
    st.subheader("Your account, your data")
    st.caption(
        "New accounts start empty. Returning users see only their saved payments and investigations."
    )
    mode = st.radio(
        "Account action",
        ["Sign in", "Create account"],
        horizontal=True,
        key="workspace_auth_mode",
    )
    with st.form("workspace_auth", clear_on_submit=False):
        username = st.text_input(
            "Username",
            max_chars=64,
            help="3–64 characters: letters, numbers, dots, underscores or hyphens.",
        )
        password = st.text_input(
            "Password",
            type="password",
            max_chars=128,
            help="At least 12 characters. Use a unique password.",
        )
        confirmation = (
            st.text_input("Confirm password", type="password", max_chars=128)
            if mode == "Create account"
            else None
        )
        submit = st.form_submit_button(mode, type="primary")
    if submit:
        try:
            if confirmation is not None and password != confirmation:
                raise ValueError("Passwords do not match.")
            credentials = Credentials(username=username, password=password)
            with Session() as session:
                result = (
                    auth.register(session, credentials)
                    if mode == "Create account"
                    else auth.login(session, credentials)
                )
            st.session_state.clear()
            st.session_state["workspace_token"] = result["access_token"]
            st.session_state["workspace_page"] = "Overview"
            st.rerun()
        except ValueError as error:
            st.error(form_error(error))


def overview(rows, case_rows, owner):
    totals = service.summary(rows, case_rows)
    st.session_state["page"] = "Executive Overview"
    hero(
        "Clarity for every\npayment.",
        "Payment activity, risk signals, and investigations. One focused workspace.",
        "PAYMENTGUARD / OPERATIONS",
    )
    cols = st.columns([1.1, 1, 1])
    cols[0].button(
        "Add payment data" if owner else "Create account",
        on_click=route,
        args=("Data & access", None if owner else "Create account"),
        type="primary",
        width="stretch",
    )
    cols[1].button("View payments", on_click=route, args=("Payments",), width="stretch")
    cols[2].download_button(
        "Download report",
        service.report(rows, case_rows),
        file_name="paymentguard-report.html",
        mime="text/html",
        width="stretch",
    )
    st.write("")
    section(
        "Workspace overview",
        "User-submitted events · USD" if rows else "No payment activity recorded",
    )
    for col, item in zip(
        st.columns(4),
        [
            (
                "Payment volume",
                money(totals["payment_volume"]),
                "Total submitted event amounts. PaymentGuard does not move or settle funds.",
            ),
            (
                "Payments",
                f"{totals['transactions']:,}",
                "Events submitted to this user's workspace.",
            ),
            (
                "Confirmed fraud loss",
                money(totals["confirmed_fraud_loss"]),
                "Settled or returned amounts explicitly labeled as fraud by your source.",
            ),
            (
                "Blocked fraud amount",
                money(totals["blocked_fraud_amount"]),
                "Source-reported blocked events explicitly labeled as fraud. Not verified savings.",
            ),
        ],
    ):
        with col:
            metric(*item)
    st.write("")
    left, right = st.columns([1.55, 1])
    with left, st.container(border=True):
        section("Payment activity", "Daily submitted amounts · USD")
        if not rows:
            empty(
                "Your timeline starts with your first payment",
                "Add payment events to see volume and trends. No estimates or sample activity are included.",
            )
        else:
            data = pd.DataFrame(rows)
            data["day"] = pd.to_datetime(data.occurred_at).dt.strftime("%Y-%m-%d")
            data["amount"] = data.amount_minor / 100
            daily = data.groupby("day", as_index=False).amount.sum()
            chart(
                px.area(
                    daily, x="day", y="amount", color_discrete_sequence=[COLORS[0]]
                ),
                280,
            )
    with right, st.container(border=True):
        section("Operational status", "What needs attention")
        statuses = [
            ("Open investigations", str(totals["open_cases"])),
            ("Payments with signals", str(totals["flagged_transactions"])),
            ("Awaiting risk evidence", str(totals["unassessed_transactions"])),
            ("Confirmed outcomes", str(totals["confirmed_outcomes"])),
        ]
        for label, value in statuses:
            st.markdown(
                f'<div class="signal"><span>{escape(label)}</span><strong>{value}</strong></div>',
                unsafe_allow_html=True,
            )
        st.caption(
            "No payment processor connected. Uploaded or manually entered events are the only data source."
        )
    with st.container(border=True):
        section("Next action", "A workspace that begins with your own information")
        if not owner:
            st.write(
                "Create your account to save payment events, assess available risk evidence, and keep an investigation history."
            )
        elif not rows:
            st.write(
                "Download the empty CSV template, fill it with your payment events, and import it—or record one payment manually."
            )
        elif totals["unassessed_transactions"]:
            st.write(
                f"{totals['unassessed_transactions']:,} payments have no risk context. Include source-provided evidence with future imports. Existing events are preserved as submitted."
            )
        else:
            st.write(
                f"{totals['flagged_transactions']:,} payments contain rule signals. Review the evidence before making a decision."
            )


def payments_page(rows, owner):
    if not rows:
        empty(
            "No payments yet",
            "Only events you add to your account appear here. New users begin with an empty workspace.",
        )
        st.button(
            "Add payment data", on_click=route, args=("Data & access",), type="primary"
        )
        return
    data = pd.DataFrame(rows)
    a, b = st.columns([2, 1])
    search = a.text_input(
        "Search payment or customer",
        placeholder="Payment reference or customer reference",
    )
    statuses = b.multiselect("Status", sorted(data.status.unique()))
    selected = data.copy()
    if search:
        selected = selected[
            selected.external_id.str.contains(search, case=False, regex=False)
            | selected.customer_ref.str.contains(search, case=False, regex=False)
        ]
    if statuses:
        selected = selected[selected.status.isin(statuses)]
    if selected.empty:
        st.info("No payments match these filters.")
        return
    view = selected[
        [
            "external_id",
            "occurred_at",
            "amount",
            "status",
            "score",
            "evaluated_rules",
        ]
    ].rename(
        columns={
            "external_id": "Payment",
            "occurred_at": "Occurred / UTC",
            "amount": "Amount / USD",
            "status": "Source status",
            "score": "Risk score",
            "evaluated_rules": "Rules evaluated",
        }
    )
    st.dataframe(view, hide_index=True, width="stretch")
    st.caption(
        "A blank score means insufficient evidence. A zero score only means no evaluated rule fired; missing evidence remains unknown."
    )
    st.download_button(
        "Export current view",
        view.to_csv(index=False),
        file_name="payments.csv",
        mime="text/csv",
    )
    ref = st.selectbox("Inspect payment", selected.external_id.tolist())
    payment = next(row for row in rows if row["external_id"] == ref)
    with st.container(border=True):
        section(
            payment["external_id"],
            f"{payment['customer_ref']} · {payment['occurred_at']}",
        )
        a, b, c = st.columns(3)
        a.metric("Amount", money(payment["amount_minor"] / 100))
        b.metric(
            "Rules score",
            "Not assessed" if payment["score"] is None else str(payment["score"]),
        )
        c.metric("Evidence coverage", f"{payment['evaluated_rules']} / 12 rules")
        if payment["signals"]:
            for signal in payment["signals"]:
                st.write(
                    f"**{signal['rule_id']} · {signal['name']}** — {signal['description']}"
                )
                st.dataframe(
                    pd.DataFrame(
                        [
                            {"Evidence": k.replace("_", " ").title(), "Value": str(v)}
                            for k, v in signal["evidence"].items()
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
        else:
            st.info(
                "No rule signals recorded. This does not establish that the payment is safe."
            )
        with st.expander("Source evidence"):
            if payment["evidence"]:
                st.json(payment["evidence"])
            else:
                st.write("No risk context supplied.")
        st.caption(
            "This score uses explicit rules only. No machine-learning model is deployed for this workspace."
        )
        if st.button("Open investigation", type="primary"):
            try:
                with Session() as session:
                    service.create_case(session, owner["id"], payment["id"])
                st.success(
                    "Investigation created. Open Investigations to assign and review it."
                )
            except ValueError as error:
                st.info(str(error))


def investigations_page(case_rows, rows, owner):
    if not case_rows:
        empty(
            "No investigations open",
            "Select a payment and choose Open investigation to start a traceable review.",
        )
        return
    refs = {row["id"]: row["external_id"] for row in rows}
    selected = st.selectbox(
        "Investigation",
        [case["id"] for case in case_rows],
        format_func=lambda value: refs.get(
            next(c["payment_id"] for c in case_rows if c["id"] == value), value
        ),
    )
    current = next(c for c in case_rows if c["id"] == selected)
    snapshot = st.session_state.get("workspace_case_snapshot")
    if not snapshot or snapshot["id"] != selected:
        st.session_state["workspace_case_snapshot"] = dict(current)
    case = st.session_state["workspace_case_snapshot"]
    st.caption(
        f"Recorded decision: {case['decision'] or 'Not decided'} · Version {case['version']}"
    )
    if st.button("Reload investigation"):
        st.session_state.pop("workspace_case_snapshot", None)
        st.rerun()
    with st.form(f"case_change_{selected}_{case['version']}"):
        a, b = st.columns(2)
        assignee = a.text_input("Assigned to", case["assignee"], max_chars=80)
        options = ["open", "in review", "escalated", "closed"]
        status = b.selectbox(
            "Case status", options, index=options.index(case["status"])
        )
        a, b = st.columns(2)
        decision = a.selectbox(
            "Decision",
            [
                "No new decision",
                "approve",
                "decline",
                "escalate",
                "request verification",
            ],
        )
        reason = b.selectbox(
            "Reason",
            [
                "insufficient evidence",
                "verified customer",
                "suspicious behavior",
                "ownership mismatch",
                "policy exception",
            ],
        )
        note = st.text_area("Investigation note", max_chars=2000)
        save = st.form_submit_button("Save investigation", type="primary")
    if save:
        try:
            change = CaseChange(
                version=case["version"],
                assignee=assignee,
                status=status,
                decision=None if decision == "No new decision" else decision,
                reason=None if decision == "No new decision" else reason,
                note=note,
            )
            with Session() as session:
                service.update_case(session, owner["id"], selected, change)
            st.session_state.pop("workspace_case_snapshot", None)
            st.rerun()
        except ValueError as error:
            st.error(form_error(error))
    st.caption(
        "Investigation decisions are recorded here; they do not approve, decline, or transfer funds at a payment provider."
    )
    with Session() as session:
        history = service.audit(session, owner["id"], selected)
    section("Audit history", "Recorded with your account identity")
    for item in history:
        with st.expander(
            f"{datetime.fromtimestamp(item['timestamp'], UTC):%Y-%m-%d %H:%M UTC} · {item['action'].replace('_', ' ')}"
        ):
            st.json(item["details"])


def trends_page(rows, owner):
    if not rows:
        empty(
            "Trends need payment activity",
            "Charts will populate from your own submitted payment events.",
        )
        return
    data = pd.DataFrame(rows)
    data["amount"] = data.amount_minor / 100
    a, b = st.columns(2)
    with a, st.container(border=True):
        section("Volume by direction", "Submitted USD amounts")
        chart(
            px.bar(
                data.groupby("direction", as_index=False).amount.sum(),
                x="direction",
                y="amount",
                color_discrete_sequence=[COLORS[0]],
            )
        )
    with b, st.container(border=True):
        section("Source status", "Status supplied with each event")
        grouped = data.groupby("status").size().reset_index(name="payments")
        chart(
            px.bar(
                grouped, x="status", y="payments", color_discrete_sequence=[COLORS[1]]
            )
        )
    outcomes = [row for row in rows if row["confirmed_fraud"] is not None]
    if not outcomes:
        st.info(
            "No confirmed fraud outcomes have been supplied. Fraud rates and detection accuracy are not available."
        )


def controls_page(rows):
    section(
        "Control library",
        "12 transparent rules · evaluated only when their required evidence is present",
    )
    st.caption(
        "Signals support investigation. They never prove fraud or execute a financial action."
    )
    for rule in RULES:
        with st.expander(f"{rule.rule_id} · {rule.name}"):
            st.write(rule.description)
            a, b = st.columns(2)
            a.metric("Threshold", f"{rule.threshold:g} {rule.unit}")
            b.metric("Risk weight", f"{rule.weight:g}")
    section(
        "Observed rule performance", "Only your events and explicitly supplied outcomes"
    )
    if not rows:
        empty(
            "No controls evaluated yet",
            "Your first payment with risk context will populate rule activity.",
        )
    else:
        st.dataframe(service.rule_performance(rows), hide_index=True, width="stretch")


def simulator_page(rows):
    if not rows:
        empty(
            "Add payments before testing a policy",
            "Simulation compares rule thresholds against your own events. It never changes a payment status or a baseline policy.",
        )
        return
    with st.form("workspace_simulation"):
        # Keep all controls visible in the form so threshold bounds do not depend on an unsubmitted selection.
        st.caption("Set each proposed value below. All baseline values are prefilled.")
        thresholds = {}
        cols = st.columns(3)
        for i, rule in enumerate(RULES):
            thresholds[rule.rule_id] = cols[i % 3].number_input(
                f"{rule.rule_id} · {rule.unit}",
                min_value=float(rule.minimum),
                max_value=float(rule.maximum),
                value=float(rule.threshold),
            )
        threshold = st.slider("Proposed flag threshold", 1, 100, 60)
        confirmed = st.checkbox("I confirm these settings for a simulation only.")
        run = st.form_submit_button("Run simulation", type="primary")
    if run:
        try:
            result = service.simulate(
                rows,
                SimulationRequest(
                    thresholds=thresholds,
                    decision_threshold=threshold,
                    confirmed=confirmed,
                ),
            )
            st.session_state["workspace_simulation_result"] = result
        except ValueError as error:
            st.error(form_error(error))
    result = st.session_state.get("workspace_simulation_result")
    if result:
        st.dataframe(
            pd.DataFrame(
                {"Current": result["current"], "Proposed": result["proposed"]}
            ),
            width="stretch",
        )
        st.caption(result["note"])
        with st.expander("Last confirmed settings"):
            st.json(result["settings"])


def model_page():
    empty(
        "No evaluated model yet",
        "A model must be trained and validated on appropriate data before performance metrics can be shown. No synthetic benchmark is presented as live performance.",
    )
    with st.container(border=True):
        section(
            "Current assessment method",
            "Explainable controls, with explicit evidence coverage",
        )
        st.write(
            "PaymentGuard evaluates up to 12 rules using the context supplied with each payment. Missing device, authentication, recipient, or behavioral evidence is left unknown. No anomaly score or model-accuracy result is fabricated."
        )
        st.caption(
            "Model deployment, drift monitoring, and production calibration are not configured."
        )


def reports_page(rows, case_rows):
    totals = service.summary(rows, case_rows)
    if not rows:
        empty(
            "Your report starts at $0",
            "Export an empty workspace report now, or add payments to produce an evidence-based summary.",
        )
    else:
        section("Workspace findings", "Calculated from your own records")
        st.write(
            f"{totals['transactions']:,} submitted payments total {money(totals['payment_volume'])}. {totals['flagged_transactions']:,} have rule signals and {totals['open_cases']:,} investigations remain open."
        )
        if totals["unassessed_transactions"]:
            st.info(
                f"Add source evidence for {totals['unassessed_transactions']:,} unassessed payments before making risk comparisons."
            )
        if not totals["confirmed_outcomes"]:
            st.info(
                "Add confirmed outcomes before evaluating false positives, fraud recall, or financial benefit."
            )
    st.download_button(
        "Download workspace report",
        service.report(rows, case_rows),
        file_name="paymentguard-report.html",
        mime="text/html",
        type="primary",
    )


def data_page(owner):
    if not owner:
        account_forms()
        return
    st.success(
        f"Signed in as {owner['username']}. Payment and case records are isolated to this account."
    )
    st.info(
        "No bank, exchange, or payment processor is connected. Import source events or enter one manually. Do not include payment credentials, account numbers, passwords, or unnecessary personal information."
    )
    upload_tab, manual_tab, access_tab = st.tabs(
        ["Import payments", "Record a payment", "Account & integration"]
    )
    with upload_tab:
        st.write(
            "Upload your payment-event export. Imports are validated in full before any records are saved."
        )
        st.download_button(
            "Download empty CSV template",
            service.csv_template(),
            file_name="paymentguard-import-template.csv",
            mime="text/csv",
        )
        st.caption(
            "Required: external_id, customer_ref, occurred_at with timezone, amount, direction. USD only. Up to 5,000 rows / 2 MB. Optional confirmed_fraud stays unknown when omitted. Optional evidence is a JSON object."
        )
        file = st.file_uploader("Payment events · CSV", type=["csv"], max_upload_size=2)
        if file:
            try:
                batch = service.parse_csv(file.getvalue())
                st.write(f"{len(batch):,} valid payments ready to import.")
                st.dataframe(
                    [
                        {
                            "Payment": p.external_id,
                            "Amount / USD": str(p.amount),
                            "Status": p.status,
                        }
                        for p in batch[:10]
                    ],
                    hide_index=True,
                    width="stretch",
                )
                if st.button("Import into my workspace", type="primary"):
                    with Session() as session:
                        service.ingest(session, owner["id"], batch)
                    st.session_state.pop("workspace_simulation_result", None)
                    st.success(
                        f"Imported {len(batch):,} payments. Open Overview to see your activity."
                    )
            except ValueError as error:
                st.error(form_error(error))
    with manual_tab:
        with st.form(
            f"manual_payment_{st.session_state.get('payment_form_revision', 0)}",
            clear_on_submit=False,
        ):
            a, b = st.columns(2)
            external = a.text_input("Payment reference", max_chars=80)
            customer = b.text_input("Customer reference", max_chars=80)
            a, b = st.columns(2)
            amount = a.text_input("Amount · USD", placeholder="0.00")
            occurred = b.text_input(
                "Occurred at · ISO 8601", placeholder="YYYY-MM-DDTHH:MM:SS+00:00"
            )
            a, b = st.columns(2)
            direction = a.selectbox("Direction", ["deposit", "withdrawal"])
            status = b.selectbox(
                "Source status", ["pending", "settled", "blocked", "returned"]
            )
            outcome = st.selectbox(
                "Confirmed fraud outcome",
                ["Unknown", "Confirmed fraud", "Confirmed legitimate"],
            )
            evidence = st.text_area(
                "Source-provided risk context · optional JSON",
                placeholder='{"failed_logins": 5, "ownership_match": false}',
            )
            st.caption(
                "Omit unavailable evidence. A manual entry records an event; it does not initiate or settle a payment."
            )
            save = st.form_submit_button("Record payment", type="primary")
        if save:
            try:
                payment = PaymentInput(
                    external_id=external,
                    customer_ref=customer,
                    amount=Decimal(amount),
                    occurred_at=occurred,
                    direction=direction,
                    status=status,
                    confirmed_fraud={
                        "Unknown": None,
                        "Confirmed fraud": True,
                        "Confirmed legitimate": False,
                    }[outcome],
                    evidence=Evidence.model_validate(
                        json.loads(evidence) if evidence.strip() else {}
                    ),
                )
                with Session() as session:
                    service.ingest(session, owner["id"], [payment])
                st.session_state.pop("workspace_simulation_result", None)
                st.session_state["payment_form_revision"] = (
                    st.session_state.get("payment_form_revision", 0) + 1
                )
                st.session_state["workspace_notice"] = (
                    "Payment recorded. Your workspace totals are up to date."
                )
                st.rerun()
            except (ValueError, ArithmeticError) as error:
                st.error(form_error(error))
    with access_tab:
        section("Account scope", owner["username"])
        st.write(
            "Your account starts with no payments. Sign-out clears this browser session; it does not delete your saved records. Other accounts cannot access your payment events, cases, audit history, or reports."
        )
        st.write(
            "For integrations, authenticate through /auth/login and submit validated event batches to /transactions/import using the returned bearer token. No source is connected automatically."
        )
        st.code(
            "POST /auth/login\nPOST /transactions/import\nGET /analytics/summary",
            language="text",
        )
        st.caption(
            "Before exposing this service publicly: configure TLS, hardened identity and recovery, request limits, database permissions, migrations, backups, and a security review. These deployment controls are not established by the local interface."
        )


def render():
    st.set_page_config(
        page_title="PaymentGuard · Payment Risk Operations",
        page_icon="🔒",
        layout="wide",
        initial_sidebar_state="auto",
    )
    theme()
    px.defaults.color_discrete_sequence = COLORS
    initialize()
    owner = None
    token = st.session_state.get("workspace_token")
    if token:
        try:
            with Session() as session:
                owner = auth.authenticate(session, token)
        except auth.AuthenticationError:
            st.session_state.clear()
            st.session_state["workspace_page"] = "Data & access"
            st.warning("Your session has expired. Sign in again.")
    if owner is None and not st.session_state.get("workspace_entered"):
        welcome()
        return
    # No shared analytics caches, fixture files, generated data or synthetic labels are read.
    rows = []
    case_rows = []
    if owner:
        with Session() as session:
            rows = service.events(session, owner["id"])
            case_rows = service.cases(session, owner["id"])
    with st.sidebar:
        if not owner:
            st.button("Back to welcome", on_click=return_to_welcome)
        st.markdown(
            '<div class="brand"><span class="picture-logo" role="img" aria-label="PaymentGuard blue glass lock"></span><span>PaymentGuard</span></div><div class="eyebrow">PAYMENT RISK OPERATIONS</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        page = st.radio(
            "WORKSPACE", PAGES, key="workspace_page", label_visibility="visible"
        )
        st.divider()
        st.markdown(
            f'<div class="sidebar-note"><strong>{escape(owner["username"]) if owner else "New workspace"}</strong><br>{"Individual account" if owner else "Sign in to save your activity"}<br>No payment source connected</div>',
            unsafe_allow_html=True,
        )
        if owner:
            st.button("Sign out", on_click=signout, width="stretch")
        else:
            st.button(
                "Sign in / Create account",
                on_click=route,
                args=("Data & access",),
                width="stretch",
            )
    st.markdown(
        f'<div class="workspace-topline"><span>WORKSPACE / {escape(page.upper())}</span><span class="connection-status">○ NO SOURCE CONNECTED</span></div>',
        unsafe_allow_html=True,
    )
    if page != "Overview":
        st.markdown(
            f'<div class="page-heading"><div><div class="eyebrow">PAYMENTGUARD</div><h1>{escape(page)}</h1><p>Your account’s payment operations, grounded in the events you provide.</p></div></div>',
            unsafe_allow_html=True,
        )
    actions = {
        "Overview": lambda: overview(rows, case_rows, owner),
        "Payments": lambda: payments_page(rows, owner),
        "Investigations": lambda: investigations_page(case_rows, rows, owner),
        "Trends": lambda: trends_page(rows, owner),
        "Controls": lambda: controls_page(rows),
        "Policy simulator": lambda: simulator_page(rows),
        "Model evaluation": model_page,
        "Reports": lambda: reports_page(rows, case_rows),
        "Data & access": lambda: data_page(owner),
    }
    if message := st.session_state.pop("workspace_notice", None):
        st.success(message)
    actions[page]()
    st.divider()
    st.caption(
        "PaymentGuard · Independent payment-risk software · Analysis supports human review and does not execute financial transactions."
    )
