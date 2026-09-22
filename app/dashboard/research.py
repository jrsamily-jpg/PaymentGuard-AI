"""PaymentGuard AI: Streamlit presentation with shared service and repository layers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import json
from html import escape
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text
from app.dashboard.theme import theme, hero, section, insight, chart, money, COLORS
from app.services.data import load_data, model_results
from app.services.analytics import (
    summary,
    trends,
    rule_performance,
    recommendations,
    emerging,
)
from app.services.reporting import report_html
from app.risk_engine.rules import RULES, catalog, explain
from app.risk_engine.simulation import simulate
from app.models.schemas import CaseCreate, CaseUpdate, SimulationInput
from app.repositories.cases import (
    create_case,
    update_case,
    list_cases,
    audit_history,
    review_backlog,
)
from app.database.session import Base, engine, SessionLocal
from app.api.security import identity, validate_security
from app.utils.config import ROOT, APP_MODE

st.set_page_config(
    page_title="PaymentGuard AI · Risk Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="auto",
)
theme()
px.defaults.color_discrete_sequence = COLORS
PAGES = [
    "Executive Overview",
    "Transaction Monitor",
    "Investigation Workbench",
    "Fraud Trends",
    "Rule Performance",
    "Rule Simulator",
    "Model Performance",
    "Leadership Recommendations",
    "SQL Explorer",
]
NAV_LABELS = dict(
    zip(
        PAGES,
        [
            "Overview",
            "Transactions",
            "Investigations",
            "Fraud trends",
            "Rule performance",
            "Policy simulator",
            "Model evaluation",
            "Leadership brief",
            "SQL analytics",
        ],
    )
)


def navigate(destination: str) -> None:
    st.session_state["page"] = destination


def inspect_payment(transaction_id: str) -> None:
    """Open a priority payment without inheriting unrelated monitor filters."""
    st.session_state["page"] = "Transaction Monitor"
    st.session_state["monitor_search"] = transaction_id
    st.session_state["monitor_status"] = []
    st.session_state["monitor_queue_only"] = False


def open_review_queue() -> None:
    st.session_state["page"] = "Transaction Monitor"
    st.session_state["monitor_status"] = ["review"]
    st.session_state["monitor_queue_only"] = True
    st.session_state["monitor_search"] = ""


with st.sidebar:
    st.markdown(
        '<div class="brand"><span class="brandmark"><svg width="21" height="23" viewBox="0 0 24 26" fill="none" aria-hidden="true"><path d="M12 2 21 6v7c0 5-5 9-9 11-4-2-9-6-9-11V6z" stroke="currentColor" stroke-width="1.6"/><path d="m8 12 3 3 5-6" stroke="currentColor" stroke-width="1.7"/></svg></span><span>PaymentGuard <small>AI</small></span></div><div class="eyebrow">Payment risk operations</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    page = st.radio(
        "WORKSPACE",
        PAGES,
        key="page",
        format_func=lambda value: NAV_LABELS[value],
        label_visibility="visible",
    )
    st.divider()
    if APP_MODE == "demo":
        role = st.selectbox("Demo role", ["analyst", "manager", "auditor"], index=1)
        actor = f"demo-{role}"
        st.caption(
            "Preview permissions for each role. This local demo does not require sign-in."
        )
    else:
        validate_security()
        key = st.text_input("API access key", type="password")
        if not key:
            st.info("Enter an access key to continue.")
            st.stop()
        try:
            user = identity(key)
            role = user["role"]
            actor = user["actor"]
        except Exception:
            st.error("Access denied")
            st.stop()
    st.markdown(
        '<div class="sidebar-note"><strong>Sandbox workspace</strong><br>Explore with synthetic payments.<br>No real customers or funds.</div>',
        unsafe_allow_html=True,
    )


@st.cache_data
def data():
    return load_data()


@st.cache_data
def perf():
    return pd.DataFrame(rule_performance(load_data()))


try:
    with st.spinner("Loading risk intelligence…"):
        d = data()
except FileNotFoundError:
    st.error("The synthetic dataset has not been built yet.")
    st.code("python -m scripts.bootstrap", language="bash")
    st.stop()
Base.metadata.create_all(engine)
with SessionLocal() as session:
    cases = list_cases(session)
    backlog = review_backlog(session)
s = summary(d, backlog)
head_left, head_right = st.columns([3, 2])
with head_left:
    st.markdown(
        f'<div class="eyebrow">WORKSPACE &nbsp; / &nbsp; {escape(page.upper())}</div>',
        unsafe_allow_html=True,
    )
with head_right:
    st.markdown(
        f'<div class="subtle" style="text-align:right">{d.timestamp.min()[:10]} — {d.timestamp.max()[:10]} &nbsp; · &nbsp; USD &nbsp; · &nbsp; {escape(role.title())}</div>',
        unsafe_allow_html=True,
    )


def metric_row(items):
    for col, (label, value, helptext) in zip(st.columns(len(items)), items):
        with col:
            st.metric(label, value, help=helptext)


def overview():
    hero(
        "Payment risk overview",
        "Exposure, control performance, and the payments that need your attention.",
    )
    action_a, action_b, action_c = st.columns([1.2, 1.1, 1.1])
    action_a.button(
        f"Review queue · {backlog:,}",
        type="primary",
        on_click=open_review_queue,
        width="stretch",
    )
    action_b.button(
        "Simulate policy",
        on_click=navigate,
        args=("Rule Simulator",),
        width="stretch",
        disabled=role != "manager",
        help="Available to managers",
    )
    action_c.download_button(
        "Download report",
        report_html(d, backlog),
        file_name="paymentguard-risk-brief.html",
        mime="text/html",
        width="stretch",
    )
    st.write("")
    section("Portfolio performance", "Full historical cohort · all payment rails · USD")
    metric_row(
        [
            (
                "Payment volume",
                money(s["total_volume"]),
                "Total attempted payment amount, USD",
            ),
            ("Transactions", f"{len(d):,}", "All synthetic events"),
            (
                "Fraud blocked",
                money(s["potential_fraud_prevented"]),
                "Fraud-labeled payments blocked by the synthetic policy; not realized savings",
            ),
            (
                "Fraud loss",
                money(s["confirmed_fraud_loss"]),
                "Synthetic fraud labels on settled or returned payments",
            ),
        ]
    )
    st.write("")
    left, right = st.columns([1.85, 1])
    daily = trends(d)
    with left, st.container(border=True):
        section("Payment activity", "Attempted volume · USD")
        cadence = st.segmented_control(
            "Chart interval",
            ["Daily", "Weekly"],
            default="Daily",
            selection_mode="single",
            label_visibility="collapsed",
        )
        activity = daily.copy()
        if cadence == "Weekly":
            activity["day"] = (
                pd.to_datetime(activity.day).dt.to_period("W-SUN").dt.start_time
            )
            activity = activity.groupby("day", as_index=False).volume.sum()
        fig = go.Figure(
            go.Scatter(
                x=activity.day,
                y=activity.volume,
                mode="lines",
                line=dict(color=COLORS[0], width=2.5, shape="linear"),
                fill="tozeroy",
                fillcolor="rgba(91,227,191,.10)",
                name="Volume",
            )
        )
        chart(fig, 280)
        if cadence == "Weekly":
            st.caption(
                "Weeks start Monday. The first and last weeks may contain fewer than seven days."
            )
    with right, st.container(border=True):
        section("Risk distribution", "Every payment, scored from 0 to 100")
        counts = d.risk_level.value_counts().reindex(
            ["Low", "Medium", "High", "Critical"], fill_value=0
        )
        bands = ["0–29.9", "30–59.9", "60–79.9", "80–100"]
        for level, band, color in zip(counts.index, bands, COLORS):
            count = int(counts[level])
            share = count / len(d) * 100
            st.markdown(
                f'<div class="risk-band"><div class="risk-band-top"><span><i style="background:{color}"></i>{escape(level)}<small>{band}</small></span><strong>{count:,}<small>{share:.1f}%</small></strong></div><div class="risk-track"><span style="width:{share:.4f}%;background:{color}"></span></div></div>',
                unsafe_allow_html=True,
            )
        st.caption(
            "High and critical payments require review or a block under the baseline policy."
        )
    with st.container(border=True):
        section(
            "Priority review queue",
            "Highest-scoring unresolved reviews · select Review queue above to investigate",
        )
        closed_ids = {
            case["transaction_id"] for case in cases if case["status"] == "closed"
        }
        priority = d[
            (d.status == "review") & ~d.transaction_id.isin(closed_ids)
        ].nlargest(5, "risk_score")
        if priority.empty:
            st.success("No unresolved payments in the review queue.")
        else:
            st.dataframe(
                priority[
                    [
                        "transaction_id",
                        "payment_rail",
                        "amount",
                        "risk_score",
                        "triggered_rules",
                    ]
                ],
                hide_index=True,
                width="stretch",
                column_config={
                    "transaction_id": "Transaction",
                    "payment_rail": "Payment rail",
                    "amount": st.column_config.NumberColumn(
                        "Amount · USD", format="$%.2f"
                    ),
                    "risk_score": st.column_config.ProgressColumn(
                        "Risk score", min_value=0, max_value=100, format="%.1f"
                    ),
                    "triggered_rules": "Control signals",
                },
            )
            picker, action = st.columns([3, 1])
            selected_priority = picker.selectbox(
                "Inspect priority payment",
                priority.transaction_id.tolist(),
                label_visibility="collapsed",
                format_func=lambda tx: f"{tx} · review decision evidence",
            )
            action.button(
                "Inspect payment",
                on_click=inspect_payment,
                args=(selected_priority,),
                width="stretch",
            )
    metric_row(
        [
            (
                "High-risk payments",
                f"{s['high_risk_transactions']:,}",
                "Risk score ≥60, including critical",
            ),
            (
                "Fraud-loss rate",
                f"{s['fraud_loss_rate']:.2%}",
                "Synthetic settled fraud dollars / attempted volume",
            ),
            (
                "False-positive rate",
                f"{s['false_positive_rate']:.2%}",
                "Legitimate blocked payments / all legitimate payments",
            ),
            (
                "Legitimate blocks",
                f"{s['legitimate_payments_blocked']:,}",
                "Policy blocks at score ≥80",
            ),
            (
                "Review backlog",
                str(backlog),
                "Policy-review payments without a closed case, including unassigned work",
            ),
        ]
    )
    insight(
        f"POLICY BRIEF  ·  The policy blocked {money(s['potential_fraud_prevented'])} in fraud-labeled payments while blocking {s['legitimate_payments_blocked']:,} legitimate payments. {s['review_transactions']:,} payments await policy review; review dollars are not counted as prevented loss. This brief is calculated locally from the displayed cohort."
    )
    a, b, c = st.columns([1.15, 1.15, 1])
    with a, st.container(border=True):
        section("Fraud by payment rail", "Labeled fraud events")
        grouped = (
            d[d.is_fraud].groupby("payment_rail").size().reset_index(name="events")
        )
        chart(
            px.bar(
                grouped,
                x="events",
                y="payment_rail",
                orientation="h",
                color_discrete_sequence=[COLORS[0]],
            ),
            260,
        )
    with b, st.container(border=True):
        section("Loss exposure", "Settled synthetic fraud · USD")
        chart(
            px.area(
                daily, x="day", y="fraud_loss", color_discrete_sequence=[COLORS[3]]
            ),
            260,
        )
    with c, st.container(border=True):
        section("Emerging signals", "Latest 7 days vs. prior 7 days")
        for r in emerging(d).head(4).to_dict("records"):
            st.markdown(
                f'<div class="signal"><span>{escape(r["pattern"])}<br><span class="subtle">{r["current_week"]} events this week</span></span><b>{r["change"]:+d}</b></div>',
                unsafe_allow_html=True,
            )
        st.caption("Counts are synthetic; changes are descriptive.")


def transaction_detail(tx):
    row = d[d.transaction_id == tx].iloc[0].to_dict()
    section(
        tx, f"{row['customer_id']} · {row['payment_rail']} · {row['timestamp']} UTC"
    )
    metric_row(
        [
            ("Risk score", f"{row['risk_score']:.1f} / 100", row["risk_level"]),
            ("Payment", f"${row['amount']:,.2f}", "USD"),
            (
                "Policy status",
                row["status"].title(),
                "Original synthetic policy decision",
            ),
        ]
    )
    tabs = st.tabs(
        ["Decision evidence", "Customer & device", "Event timeline", "Related accounts"]
    )
    with tabs[0]:
        signals = explain(row, row["triggered_rules"].split(","))
        if not signals:
            st.success(
                "No rule triggered. Behavioral and anomaly signals can still contribute to the score."
            )
        for signal in signals:
            with st.expander(
                f"{signal['rule_id']} · {signal['name']}  /  +{signal['weight']:.0f} rule weight",
                expanded=True,
            ):
                st.write(signal["explanation"])
                st.caption(
                    signal["description"] + ". Recommended action: " + signal["action"]
                )
        parts = json.loads(row["score_components"])
        chart(
            px.bar(
                x=list(parts.values()),
                y=list(parts.keys()),
                orientation="h",
                labels={"x": "Score contribution", "y": "Signal"},
                color_discrete_sequence=[COLORS[0]],
            ),
            240,
        )
        st.info(
            "Recommended action: "
            + (
                "Escalate and verify ownership before release."
                if row["risk_score"] >= 80
                else "Review supporting evidence and request verification."
                if row["risk_score"] >= 60
                else "Allow under baseline policy; monitor for additional signals."
            )
        )
        st.caption(
            "Anomaly detection identifies unusual behavior; it does not prove fraud. Ground-truth labels are for synthetic evaluation only."
        )
    with tabs[1]:
        hist = d[
            (d.customer_id == row["customer_id"]) & (d.timestamp <= row["timestamp"])
        ]
        st.write(
            f"Account age: {row['account_age']} days · Customer tenure: {row['customer_tenure']} days · {len(hist)} observed payments through this event"
        )
        evidence = {
            "Device": row["device_id"],
            "Device trusted": "Yes" if row["device_trusted"] else "No",
            "Observed devices": str(row["customer_devices"]),
            "IP address": row["ip_address"],
            "Multi-factor authentication": "Enabled"
            if row["mfa_enabled"]
            else "Not enabled",
            "Failed sign-ins": str(row["failed_logins"]),
            "Recent password reset": "Yes" if row["password_reset"] else "No",
            "Bank ownership": "Matched" if row["ownership_match"] else "Mismatch",
            "VPN or proxy": "Detected" if row["vpn_proxy"] else "Not detected",
        }
        st.dataframe(
            pd.DataFrame(evidence.items(), columns=["Evidence", "Observed value"]),
            hide_index=True,
            width="stretch",
        )
        st.dataframe(
            hist[["transaction_id", "timestamp", "amount", "risk_score"]].tail(20),
            hide_index=True,
            width="stretch",
        )
    with tabs[2]:
        hist = d[
            (d.customer_id == row["customer_id"]) & (d.timestamp <= row["timestamp"])
        ].tail(8)
        st.dataframe(
            hist[["timestamp", "direction", "payment_rail", "amount", "device_id"]],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            f"Upstream synthetic signals: {row['failed_logins']} failed logins; password reset: {row['password_reset']}; prior deposit {row['minutes_since_deposit']:,.0f} minutes earlier. These signals are supplied aggregates, not independently logged event timestamps."
        )
    with tabs[3]:
        related = d[
            (d.device_id == row["device_id"]) & (d.timestamp <= row["timestamp"])
        ]
        st.dataframe(
            related[["customer_id", "transaction_id", "amount", "risk_score"]].tail(
                100
            ),
            hide_index=True,
            width="stretch",
        )
    return row


def monitor():
    hero(
        "Follow the signal.",
        "Search payments, inspect decision evidence, and open an investigation.",
    )
    queue_only = st.toggle(
        "Unresolved reviews only",
        key="monitor_queue_only",
        help="Hide payments with closed investigations and focus on the review queue.",
    )
    with st.expander("Filter transactions", expanded=True):
        a, b, c, e = st.columns(4)
        search = a.text_input(
            "Transaction or customer",
            placeholder="TX-0000001 or CU-…",
            key="monitor_search",
        )
        rail = b.multiselect("Payment rail", sorted(d.payment_rail.unique()))
        risk = c.multiselect("Risk level", ["Low", "Medium", "High", "Critical"])
        status = e.multiselect(
            "Transaction status", sorted(d.status.unique()), key="monitor_status"
        )
        a, b, c, e = st.columns(4)
        dates = a.date_input(
            "Date range",
            value=(
                pd.to_datetime(d.timestamp.min()).date(),
                pd.to_datetime(d.timestamp.max()).date(),
            ),
        )
        countries = b.multiselect("Country", sorted(d.country.unique()))
        categories = c.multiselect(
            "Fraud category (synthetic truth)", sorted(d.fraud_category.unique())
        )
        rule = e.selectbox("Triggered rule", ["All"] + [r.rule_id for r in RULES])
        a, b = st.columns(2)
        low = a.number_input("Minimum amount (USD)", min_value=0.0, value=0.0)
        high = b.number_input("Maximum amount (USD)", min_value=0.0, value=100000.0)
    if low > high:
        st.warning("Minimum amount must not exceed maximum.")
        return
    mask = d.amount.between(low, high)
    if queue_only:
        closed_transactions = {
            case["transaction_id"] for case in cases if case["status"] == "closed"
        }
        mask &= (d.status == "review") & ~d.transaction_id.isin(closed_transactions)
    if search:
        mask &= d.transaction_id.str.contains(
            search, case=False, regex=False
        ) | d.customer_id.str.contains(search, case=False, regex=False)
    for col, values in [
        ("payment_rail", rail),
        ("risk_level", risk),
        ("status", status),
        ("country", countries),
        ("fraud_category", categories),
    ]:
        if values:
            mask &= d[col].isin(values)
    if rule != "All":
        mask &= d.triggered_rules.str.split(",").apply(lambda ids: rule in ids)
    if len(dates) == 2:
        mask &= d.timestamp.str[:10].between(str(dates[0]), str(dates[1]))
    view = d[mask].sort_values(["risk_score", "timestamp"], ascending=False)
    section("Transaction monitor", f"{len(view):,} matching payments · ordered by risk")
    if view.empty:
        st.info(
            "No payments match these filters. Broaden the date range or remove a filter."
        )
        return
    page_num = st.number_input(
        "Results page", min_value=1, max_value=max(1, (len(view) + 49) // 50), value=1
    )
    paged = view.iloc[(page_num - 1) * 50 : page_num * 50]
    st.dataframe(
        paged[
            [
                "transaction_id",
                "customer_id",
                "timestamp",
                "payment_rail",
                "amount",
                "risk_score",
                "risk_level",
                "status",
                "triggered_rules",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config={
            "transaction_id": "Transaction",
            "customer_id": "Customer",
            "timestamp": "Date / UTC",
            "payment_rail": "Payment rail",
            "risk_level": "Risk level",
            "status": "Status",
            "triggered_rules": "Rule signals",
            "risk_score": st.column_config.ProgressColumn(
                "Risk score", min_value=0, max_value=100, format="%.1f"
            ),
            "amount": st.column_config.NumberColumn("Amount / USD", format="$%.2f"),
        },
    )
    st.caption(
        f"Showing {(page_num - 1) * 50 + 1:,}–{min(page_num * 50, len(view)):,} of {len(view):,} payments. Select a transaction below to inspect the evidence."
    )
    st.download_button(
        "Export matching payments · CSV",
        view.head(10000)[
            [
                "transaction_id",
                "customer_id",
                "timestamp",
                "payment_rail",
                "amount",
                "risk_score",
                "risk_level",
                "status",
                "triggered_rules",
            ]
        ].to_csv(index=False),
        file_name="paymentguard-transactions.csv",
        mime="text/csv",
        help="Exports up to 10,000 matching payments in risk order.",
    )
    st.divider()
    tx = st.selectbox("Inspect a transaction", paged.transaction_id.tolist())
    transaction_detail(tx)
    if role in ["analyst", "manager"] and st.button(
        "Open investigation", type="primary"
    ):
        try:
            with SessionLocal() as session:
                case = create_case(session, CaseCreate(transaction_id=tx), actor)
            st.success(
                f"Case #{case['id']} created. Open Investigation Workbench to assign and review it."
            )
        except ValueError as error:
            st.info(str(error))


def relationship(row):
    related = (
        d[(d.device_id == row["device_id"]) & (d.timestamp <= row["timestamp"])]
        .customer_id.unique()
        .tolist()[:6]
    )
    labels = [
        row["customer_id"],
        row["device_id"],
        row["ip_address"],
        row["bank_account_id"],
        row["recipient_id"],
    ] + [x for x in related if x != row["customer_id"]]
    coords = [(0, 0), (-1, 1), (1, 1), (-1, -1), (1, -1)] + [
        (-2, 1.8 - i * 0.65) for i in range(len(labels) - 5)
    ]
    fig = go.Figure()
    for i in range(1, len(labels)):
        parent = 1 if i >= 5 else 0
        fig.add_trace(
            go.Scatter(
                x=[coords[parent][0], coords[i][0]],
                y=[coords[parent][1], coords[i][1]],
                mode="lines",
                line=dict(color="#3b6271", width=2),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=[x for x, y in coords],
            y=[y for x, y in coords],
            text=labels,
            mode="markers+text",
            textposition="bottom center",
            marker=dict(
                size=[28] + [19] * (len(labels) - 1),
                color=[COLORS[0]] + [COLORS[1]] * (len(labels) - 1),
            ),
            showlegend=False,
        )
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    chart(fig, 350)


def workbench():
    hero(
        "Connect the evidence.",
        "A persistent case record, accountable decisions, and the relationships behind each alert.",
    )
    if not cases:
        st.info(
            "No investigations yet. Start from Transaction Monitor, or create a case below."
        )
        if role in ["analyst", "manager"]:
            tx = st.selectbox(
                "Prioritize a high-risk payment",
                d.nlargest(30, "risk_score").transaction_id.tolist(),
            )
            if st.button("Create first case", type="primary"):
                with SessionLocal() as session:
                    create_case(session, CaseCreate(transaction_id=tx), actor)
                st.rerun()
        return
    st.dataframe(pd.DataFrame(cases), hide_index=True, width="stretch")
    case_id = st.selectbox(
        "Active case", [c["id"] for c in cases], format_func=lambda x: f"Case #{x}"
    )
    case = next(c for c in cases if c["id"] == case_id)
    row = d[d.transaction_id == case["transaction_id"]].iloc[0].to_dict()
    left, right = st.columns([1.2, 1])
    with left, st.container(border=True):
        section(
            "Relationship map",
            "Observed by transaction time · capped at 6 related customers",
        )
        relationship(row)
    with right, st.container(border=True):
        section("Analyst decision", f"Case #{case_id} · version {case['version']}")
        if role == "auditor":
            st.info("Auditor access is read-only.")
        else:
            with st.form("case_form"):
                assignee = st.text_input("Assign to", case["assignee"], max_chars=80)
                note = st.text_area("Investigation note", max_chars=2000)
                decision = st.selectbox(
                    "Decision",
                    [
                        "No new decision",
                        "approve",
                        "decline",
                        "escalate",
                        "request verification",
                    ],
                )
                reason = st.selectbox(
                    "Reason code",
                    [
                        "insufficient_evidence",
                        "verified_customer",
                        "suspicious_behavior",
                        "ownership_mismatch",
                        "policy_exception",
                    ],
                )
                statuses = ["open", "in review", "escalated", "closed"]
                status = st.selectbox(
                    "Case status", statuses, index=statuses.index(case["status"])
                )
                if st.form_submit_button("Save investigation", type="primary"):
                    try:
                        update = CaseUpdate(
                            version=case["version"],
                            assignee=assignee,
                            note=note or None,
                            decision=None
                            if decision == "No new decision"
                            else decision,
                            reason_code=reason,
                            status=status,
                        )
                        with SessionLocal() as session:
                            update_case(session, case_id, update, actor)
                        st.rerun()
                    except (ValueError, LookupError) as error:
                        st.error(str(error))
    with SessionLocal() as session:
        history = audit_history(session, case_id)
    with st.expander("Audit history", expanded=True):
        for event in history:
            st.write(
                f"**{event['action'].title()}** · {event['actor']} · {event['timestamp']}"
            )
            st.json(event["details"], expanded=False)
    transaction_detail(case["transaction_id"])


def fraud_trends():
    hero(
        "See what is changing.",
        "Compare fraud patterns across rails, account cohorts, geography, and authentication behavior.",
    )
    left, right = st.columns(2)
    daily = trends(d)
    with left, st.container(border=True):
        section(
            "Fraud rate over time", "Share of transactions with a synthetic fraud label"
        )
        fig = px.line(
            daily, x="day", y="fraud_rate", color_discrete_sequence=[COLORS[0]]
        )
        fig.update_yaxes(tickformat=".1%")
        chart(fig)
    with right, st.container(border=True):
        section("Fraud loss by rail", "Settled / returned synthetic fraud · USD")
        losses = (
            d[d.is_fraud & d.status.isin(["settled", "returned"])]
            .groupby("payment_rail")
            .amount.sum()
            .reset_index()
        )
        chart(
            px.bar(
                losses,
                x="payment_rail",
                y="amount",
                color_discrete_sequence=[COLORS[3]],
            )
        )
    tabs = st.tabs(
        ["Typologies", "Geography", "Account & amount", "Device & authentication"]
    )
    with tabs[0]:
        patterns = (
            d[d.is_fraud]
            .groupby("fraud_category")
            .size()
            .sort_values()
            .reset_index(name="events")
        )
        chart(
            px.bar(
                patterns,
                y="fraud_category",
                x="events",
                orientation="h",
                color_discrete_sequence=[COLORS[0]],
            ),
            470,
        )
        st.dataframe(emerging(d), hide_index=True, width="stretch")
    with tabs[1]:
        geo = (
            d.groupby("country")
            .agg(
                payments=("transaction_id", "count"),
                fraud_rate=("is_fraud", "mean"),
                fraud_events=("is_fraud", "sum"),
            )
            .reset_index()
        )
        st.dataframe(geo, hide_index=True, width="stretch")
        fig = px.bar(
            geo, x="country", y="fraud_rate", color_discrete_sequence=[COLORS[1]]
        )
        fig.update_yaxes(tickformat=".1%")
        chart(fig)
    with tabs[2]:
        x = d.copy()
        x["Account age"] = pd.cut(
            x.account_age,
            [-1, 29, 179, 364, 10000],
            labels=["<30d", "30–179d", "180–364d", "365d+"],
        )
        x["Amount band"] = pd.cut(
            x.amount,
            [0, 10, 100, 1000, 10000, 100001],
            labels=["<$10", "$10–99", "$100–999", "$1k–10k", ">$10k"],
        )
        a, b = st.columns(2)
        for col, field in [(a, "Account age"), (b, "Amount band")]:
            with col:
                grouped = x.groupby(field, observed=True).is_fraud.mean().reset_index()
                fig = px.bar(
                    grouped, x=field, y="is_fraud", color_discrete_sequence=[COLORS[2]]
                )
                fig.update_yaxes(tickformat=".0%", title="Fraud rate")
                chart(fig)
    with tabs[3]:
        a, b = st.columns(2)
        with a:
            grouped = (
                d.groupby(d.shared_accounts.clip(upper=6)).is_fraud.mean().reset_index()
            )
            fig = px.bar(grouped, x="shared_accounts", y="is_fraud")
            fig.update_yaxes(tickformat=".0%", title="Fraud rate")
            chart(fig)
            st.caption("Distinct accounts observed by event time; 6 includes 6+.")
        with b:
            grouped = (
                d.groupby(d.failed_logins.clip(upper=6)).is_fraud.mean().reset_index()
            )
            fig = px.bar(
                grouped,
                x="failed_logins",
                y="is_fraud",
                color_discrete_sequence=[COLORS[3]],
            )
            fig.update_yaxes(tickformat=".0%", title="Fraud rate")
            chart(fig)
            st.caption("Failed logins from upstream synthetic signals; 6 includes 6+.")


def rule_page():
    hero(
        "Challenge every control.",
        "Find the rules that catch fraud—and the rules that create unnecessary customer friction.",
    )
    p = perf()
    metric_row(
        [
            ("Active controls", str(len(p)), "Configurable rule catalog"),
            (
                "Rules to tune",
                str((p.recommendation == "tune").sum()),
                "Precision below 40% and at least one true positive",
            ),
            (
                "Rules to retain",
                str((p.recommendation == "retain").sum()),
                "Precision at least 70%",
            ),
        ]
    )
    a, b = st.columns(2)
    with a, st.container(border=True):
        section("Precision by control", "True fraud / all alerts")
        fig = px.bar(
            p,
            x="rule_id",
            y="precision",
            color="recommendation",
            color_discrete_map={
                "retain": COLORS[0],
                "monitor": COLORS[1],
                "tune": COLORS[2],
                "retire": COLORS[3],
            },
        )
        fig.update_yaxes(tickformat=".0%")
        chart(fig)
    with b, st.container(border=True):
        section("Customer friction", "Legitimate alerts · overlapping rules")
        chart(px.bar(p, x="rule_id", y="fp", color_discrete_sequence=[COLORS[2]]))
    st.dataframe(
        p[
            [
                "rule_id",
                "name",
                "triggered",
                "tp",
                "fp",
                "precision",
                "recall",
                "false_positive_rate",
                "fraud_dollars_detected",
                "legitimate_dollars_blocked",
                "friction_cost",
                "recommendation",
            ]
        ],
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Each rule is evaluated independently across the full cohort. Captures overlap. 'Legitimate dollars blocked' here means counterfactual exposure if every hit were blocked. Estimated friction: $8 per false alert."
    )
    with st.expander("Control definitions & thresholds"):
        st.dataframe(pd.DataFrame(catalog()), hide_index=True, width="stretch")


def simulator_page():
    hero(
        "Test before you decide.",
        "Compare a proposed policy with the baseline. Measure detection, customer friction, and the financial tradeoff.",
    )
    if role != "manager":
        st.info(
            "Simulation requires the manager role. Change the local demo role in the sidebar."
        )
        return
    with st.form("simulation"):
        a, b, c = st.columns(3)
        overrides = {}
        for i, r in enumerate(RULES):
            with [a, b, c][i % 3]:
                overrides[r.rule_id] = st.number_input(
                    f"{r.rule_id} · {r.name} ({r.unit})",
                    min_value=float(r.minimum),
                    max_value=float(r.maximum),
                    value=float(r.threshold),
                    step=1.0,
                )
        a, b = st.columns(2)
        threshold = a.slider(
            "Proposed decision threshold", min_value=1, max_value=100, value=60
        )
        cost = b.number_input(
            "Assumed friction cost per false alert (USD)",
            min_value=0.0,
            max_value=1000.0,
            value=8.0,
        )
        confirmed = st.checkbox(
            "I confirm these settings for a simulation. Baseline policy will remain unchanged."
        )
        run = st.form_submit_button("Run policy simulation", type="primary")
    if run:
        try:
            with st.spinner("Re-scoring the synthetic cohort…"):
                st.session_state["simulation_result"] = simulate(
                    d,
                    SimulationInput(
                        thresholds=overrides,
                        decision_threshold=threshold,
                        friction_cost=cost,
                        confirmed=confirmed,
                    ),
                )
        except ValueError as error:
            st.error(str(error))
    if result := st.session_state.get("simulation_result"):
        section(
            "Last confirmed simulation",
            "Results use the saved settings below, not unsaved form edits",
        )
        with st.expander("Saved simulation settings"):
            st.json(result["settings"])
        delta = result["delta"]
        metric_row(
            [
                (
                    "Additional fraud detected",
                    f"{delta['tp']:+,}",
                    "Change in true positives",
                ),
                (
                    "Additional legitimate alerts",
                    f"{delta['fp']:+,}",
                    "Change in false positives",
                ),
                (
                    "Estimated net impact",
                    money(delta["net_financial_impact"]),
                    "Change in captured fraud dollars minus assumed friction cost",
                ),
            ]
        )
        comparison = pd.DataFrame(
            {"Current policy": result["current"], "Proposed policy": result["proposed"]}
        )
        st.dataframe(
            comparison.loc[
                [
                    "tp",
                    "fp",
                    "precision",
                    "recall",
                    "fraud_dollars_detected",
                    "legitimate_dollars_blocked",
                    "friction_cost",
                ]
            ],
            width="stretch",
        )
        insight(
            f"Estimated fraud savings change by {money(delta['fraud_dollars_detected'])}; friction cost changes by {money(delta['friction_cost'])}. This assumes every flagged fraudulent dollar is preventable. It excludes recoveries, operational capacity, and customer lifetime value."
        )
        st.caption(
            "Simulation only. No endpoint or dashboard control promotes these settings to a live policy."
        )


def model_page():
    hero(
        "Measure the tradeoff.",
        "Rules, anomalies, and a combined score—evaluated on later transactions the model did not train on.",
    )
    results = model_results()
    evaluation = pd.DataFrame(results["evaluation"]).T
    st.caption(
        f"Chronological split: {results['model']['train_rows']:,} training events / {results['model']['test_rows']:,} holdout events. Rules-only threshold 30; ML percentile 97%; combined review threshold 60. Thresholds are not fitted to holdout labels."
    )
    st.dataframe(
        evaluation[
            [
                "precision",
                "recall",
                "f1",
                "roc_auc",
                "false_positive_rate",
                "false_negative_rate",
                "fraud_dollars_detected",
                "fraud_dollars_missed",
                "legitimate_dollars_blocked",
            ]
        ],
        width="stretch",
    )
    for col, (name, m) in zip(st.columns(3), results["evaluation"].items()):
        with col, st.container(border=True):
            section(name, "Confusion matrix · holdout")
            fig = px.imshow(
                [[m["tn"], m["fp"]], [m["fn"], m["tp"]]],
                x=["Allow", "Flag"],
                y=["Legitimate", "Fraud"],
                text_auto=True,
                color_continuous_scale=[[0, "#10222c"], [1, "#4fbdab"]],
                labels=dict(x="Predicted", y="Actual"),
            )
            fig.update_layout(coloraxis_showscale=False)
            chart(fig, 260)
    curve = pd.DataFrame(results["threshold_curve"])
    a, b = st.columns(2)
    with a, st.container(border=True):
        section("Threshold performance", "Combined score · holdout")
        fig = px.line(
            curve,
            x="threshold",
            y=["precision", "recall"],
            color_discrete_sequence=COLORS,
        )
        fig.update_yaxes(tickformat=".0%")
        chart(fig)
    with b, st.container(border=True):
        section(
            "Precision–recall tradeoff", "Each point is a tested decision threshold"
        )
        fig = px.scatter(
            curve,
            x="recall",
            y="precision",
            color="threshold",
            hover_data=["fp", "tp"],
            color_continuous_scale="Teal",
        )
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(tickformat=".0%")
        chart(fig)
    st.subheader("Interpretable anomaly drivers")
    drivers = d[d.evaluation_split == "test"].nlargest(10, "anomaly_score")
    st.dataframe(
        drivers[
            [
                "transaction_id",
                "anomaly_score",
                "amount_ratio",
                "tx_count_1h",
                "distance_km",
                "failed_logins",
                "shared_accounts",
                "customer_devices",
            ]
        ],
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "These are observed input drivers for unusual transactions, not causal feature importances or SHAP values."
    )
    st.info(
        "Model limitations: synthetic typologies reflect generator assumptions; feature signals and labels share a simulated cause. Real-world performance is unknown. Anomaly percentiles are not fraud probabilities. No protected-attribute targeting, automated production decisions, or external AI calls."
    )


def leadership_page():
    hero(
        "From evidence to action.",
        "A leadership brief grounded in the numbers, with explicit assumptions and clear next steps.",
    )
    for index, r in enumerate(recommendations(d), 1):
        with st.container(border=True):
            st.subheader(f"0{index} / {r['title']}")
            st.write(r["evidence"])
            st.caption(r["action"])
    st.download_button(
        "Download leadership report · HTML",
        data=report_html(d, backlog),
        file_name="paymentguard-risk-brief.html",
        mime="text/html",
        type="primary",
    )
    st.caption("Self-contained report. Open in a browser to read or print to PDF.")


def sql_page():
    hero(
        "Show the work.",
        "Documented SQL behind the metrics. Inspect the query, then inspect the result.",
    )
    files = sorted((ROOT / "sql").glob("*.sql"))
    selected = st.selectbox(
        "Analytics query",
        files,
        format_func=lambda p: p.stem[3:].replace("_", " ").title(),
    )
    query = selected.read_text()
    st.code(query, language="sql")
    with engine.connect() as connection:
        result = pd.read_sql(text(query), connection)
    st.dataframe(result, hide_index=True, width="stretch")
    st.caption(
        f"{len(result):,} result rows. Only checked-in read-only queries can run. Transaction searches use parameterized SQLAlchemy statements."
    )


{
    "Executive Overview": overview,
    "Transaction Monitor": monitor,
    "Investigation Workbench": workbench,
    "Fraud Trends": fraud_trends,
    "Rule Performance": rule_page,
    "Rule Simulator": simulator_page,
    "Model Performance": model_page,
    "Leadership Recommendations": leadership_page,
    "SQL Explorer": sql_page,
}[page]()
st.divider()
st.caption(
    "PaymentGuard AI  /  Synthetic research environment  /  Independent portfolio project  /  Anomaly ≠ proof of fraud"
)
