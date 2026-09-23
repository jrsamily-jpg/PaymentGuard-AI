"""Original visual system: midnight surfaces, cobalt accents and crypto-security artwork."""

from html import escape
from pathlib import Path

import streamlit as st

ART = Path(__file__).parent / "assets" / "workspace-observatory-v1.png"
SIGNIN_ART = Path(__file__).parent / "assets" / "welcome-security-v1.png"
COLORS = ["#5d91ff", "#70c8f4", "#b3a3ff", "#f0bd73", "#f28da3", "#a9bddb"]


def theme():
    """Load the local visual system without requiring remote fonts."""
    css = (Path(__file__).parent / "style.css").read_text()
    active_art = (
        SIGNIN_ART
        if st.session_state.get("workspace_page") == "Data & access"
        and not st.session_state.get("workspace_token")
        else ART
    )
    st.markdown(
        f"<style>:root{{--pg-art:url(/app/static/{active_art.name});}}{css}</style>",
        unsafe_allow_html=True,
    )


def hero(title, subtitle, kicker="PAYMENT RISK INTELLIGENCE"):
    """Use a spacious overview hero and compact headers for operational work."""
    overview = (
        st.session_state.get("page", "Executive Overview") == "Executive Overview"
    )
    title_html = escape(title).replace("\n", "<br>")
    if overview:
        markup = f'<div class="hero" style="background-image:linear-gradient(90deg,rgba(9,17,25,.28),transparent),url(/app/static/{ART.name})"><div class="hero-content"><div class="eyebrow">{escape(kicker)}</div><h1>{title_html}</h1><p>{escape(subtitle)}</p></div><span class="hero-caption">PAYMENTGUARD / INTELLIGENCE IN FOCUS</span></div>'
    else:
        page = st.session_state.get("page", title)
        markup = f'<div class="page-heading"><div><div class="eyebrow">PAYMENTGUARD / WORKSPACE</div><h1>{escape(page)}</h1><p>{escape(subtitle)}</p></div><img class="mini-art" src="/app/static/{ART.name}" alt="" aria-hidden="true"></div>'
    st.markdown(markup, unsafe_allow_html=True)


def section(title, subtitle=""):
    st.markdown(
        f'<div class="section-title">{escape(title)}</div><div class="subtle">{escape(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def insight(text):
    st.markdown(f'<div class="insight">{escape(text)}</div>', unsafe_allow_html=True)


def chart(fig, height=290):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Arial, sans-serif", "color": "#afbfcb", "size": 12},
        height=height,
        margin={"l": 12, "r": 16, "t": 24, "b": 25},
        colorway=COLORS,
        legend={"orientation": "h", "y": -0.15, "x": 0, "title": None},
    )
    fig.update_xaxes(gridcolor="#22313d", zeroline=False, title=None, automargin=True)
    fig.update_yaxes(gridcolor="#22313d", zeroline=False, automargin=True)
    # Translate internal column names before displaying chart axes to analysts.
    fig.for_each_yaxis(
        lambda axis: axis.update(
            title_text=(axis.title.text or "").replace("_", " ").capitalize()
        )
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def money(n):
    return (
        f"${n / 1e6:,.2f}M"
        if abs(n) >= 1e6
        else f"${n / 1000:,.1f}K"
        if abs(n) >= 1000
        else f"${n:,.0f}"
    )
