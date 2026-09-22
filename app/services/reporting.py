"""Self-contained escaped HTML reports generated from verified metrics."""

from html import escape
import pandas as pd
from app.services.analytics import summary, recommendations


def report_html(d: pd.DataFrame, backlog: int | None = None) -> str:
    s = summary(d, backlog)
    cards = "".join(
        f"<div><small>{escape(k.replace('_', ' ').title())}</small><strong>{v:,.2f}</strong></div>"
        for k, v in s.items()
        if isinstance(v, (int, float)) and not isinstance(v, bool)
    )
    recs = "".join(
        f"<article><h3>{escape(r['title'])}</h3><p>{escape(r['evidence'])}</p><p>{escape(r['action'])}</p></article>"
        for r in recommendations(d)
    )
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>PaymentGuard AI · Risk brief</title><style>body{{font:16px system-ui;max-width:1000px;margin:60px auto;padding:24px;color:#153035}}h1{{font-size:44px}}small{{display:block;color:#566}}strong{{font-size:24px}}section{{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}}article{{border-top:1px solid #ccd;padding:15px 0}}@media print{{body{{margin:10px}}}}</style><p>PAYMENTGUARD AI / LEADERSHIP BRIEF</p><h1>Payment risk, explained.</h1><p>{escape(s["start"])} — {escape(s["end"])} · USD</p><p>All customers, transactions and fraud events are synthetic. Counterfactual prevented dollars are not realized savings. Review is not counted as prevention.</p><section>{cards}</section><h2>Recommended next steps</h2>{recs}<p>Loss rate and false-positive rate above are fractions. Friction assumes $8 per legitimate flagged payment; it is not measured customer lifetime value.</p></html>"""
