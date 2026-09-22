"""First-visit welcome screen; artwork is decorative, never account activity."""

import base64
from pathlib import Path

import streamlit as st


@st.cache_data
def welcome_art():
    return base64.b64encode(
        (Path(__file__).parent / "assets" / "welcome-security-v1.png").read_bytes()
    ).decode()


def enter_workspace(page="Overview", action=None):
    st.session_state["workspace_entered"] = True
    st.session_state["workspace_page"] = page
    if action:
        st.session_state["workspace_auth_mode"] = action


def return_to_welcome():
    st.session_state["workspace_entered"] = False


def welcome():
    st.markdown(
        '<div class="welcome-shell"><div class="welcome-brand"><span class="welcome-mark">◈</span> PaymentGuard <span class="welcome-tag">PAYMENT RISK INTELLIGENCE</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""<section class="welcome-hero" style="background-image:url(data:image/png;base64,{welcome_art()})">
<div class="welcome-copy"><div class="welcome-eyebrow">CLARITY. CONTROL. CONFIDENCE.</div><h1>A clearer view.<br>A smarter next move.</h1><p>Bring your payment activity into focus. Understand risk signals and investigate with the evidence in front of you.</p><div class="welcome-pill">YOUR DATA. YOUR WORKSPACE.</div></div></section>""",
        unsafe_allow_html=True,
    )
    a, b, c = st.columns([1, 1, 1])
    a.button(
        "Create account",
        type="primary",
        width="stretch",
        on_click=enter_workspace,
        args=("Data & access", "Create account"),
    )
    b.button(
        "Sign in",
        width="stretch",
        on_click=enter_workspace,
        args=("Data & access", "Sign in"),
    )
    c.button("Explore workspace", width="stretch", on_click=enter_workspace)
    st.markdown(
        """<div class="welcome-features">
<article><span>01 / VISIBILITY</span><h3>See the full picture.</h3><p>Organize the payment events you provide in one focused workspace.</p></article>
<article><span>02 / INTELLIGENCE</span><h3>Understand the signal.</h3><p>Review explainable rules grounded in available evidence.</p></article>
<article><span>03 / CONTROL</span><h3>Make the next move.</h3><p>Keep investigations, decisions, and their history together.</p></article>
</div><div class="welcome-footnote">New accounts start at $0 with no payment activity. Crypto and chart artwork is illustrative; no payment source is connected.<br>PaymentGuard is independent software and is not affiliated with Coinbase.</div>""",
        unsafe_allow_html=True,
    )
