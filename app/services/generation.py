"""Reproducible synthetic events; identities are artificial and IPs use documentation ranges."""

import numpy as np
import pandas as pd

CATEGORIES = [
    "Account takeover",
    "Stolen credentials",
    "New-account fraud",
    "Card testing",
    "ACH return abuse",
    "Rapid cash-out",
    "Velocity abuse",
    "Shared device",
    "Device hopping",
    "Impossible travel",
    "Proxy abuse",
    "Unusual amount",
    "Risky recipient",
    "Mule account",
    "Authentication attack",
    "Crypto off-ramp",
]


def generate_transactions(n: int = 100_000, seed: int = 42) -> pd.DataFrame:
    if n < 100:
        raise ValueError("Generate at least 100 transactions")
    rng = np.random.default_rng(seed)
    customer = rng.integers(1, max(50, n // 7), n)
    base = rng.lognormal(4.9, 0.65, max(51, n // 7) + 1)
    # Fixed timestamps make independent builds comparable.
    times = pd.Timestamp("2026-07-01") + pd.to_timedelta(
        np.sort(rng.integers(0, 60 * 86400, n)), unit="s"
    )
    fraud = rng.random(n) < 0.027
    categories = np.where(fraud, rng.choice(CATEGORIES, n), "Legitimate")
    # Emerging account-takeover concentration in the final week.
    recent = times >= pd.Timestamp("2026-08-23")
    categories = np.where(
        fraud & recent & (rng.random(n) < 0.40), "Account takeover", categories
    )
    age = rng.integers(5, 1500, n)
    d = pd.DataFrame(
        {
            "transaction_id": [f"TX-{i + 1:07d}" for i in range(n)],
            "customer_id": [f"CU-{c:06d}" for c in customer],
            "timestamp": times.astype(str),
            "amount": np.round(
                np.clip(base[customer] * rng.lognormal(0, 0.75, n), 1, 45000), 2
            ),
            "customer_avg_amount": np.round(base[customer], 2),
            "currency": "USD",
            "payment_rail": rng.choice(
                [
                    "ACH",
                    "Debit card",
                    "Credit card",
                    "Wire",
                    "Real-time payment",
                    "Crypto",
                ],
                n,
                p=[0.30, 0.24, 0.16, 0.06, 0.15, 0.09],
            ),
            "direction": rng.choice(["deposit", "withdrawal"], n, p=[0.56, 0.44]),
            "account_age": age,
            "customer_tenure": age + rng.integers(0, 200, n),
            "country": rng.choice(
                ["US", "GB", "CA", "DE", "SG", "BR"],
                n,
                p=[0.67, 0.10, 0.09, 0.06, 0.04, 0.04],
            ),
            "region": rng.choice(["Region A", "Region B", "Region C"], n),
            "ip_address": [f"192.0.2.{1 + c % 254}" for c in customer],
            "device_id": [f"DV-{c:06d}" for c in customer],
            "bank_account_id": [f"BANK-{c:06d}" for c in customer],
            "recipient_id": [
                f"RC-{v:06d}" for v in rng.integers(1, max(30, n // 15), n)
            ],
            "device_trusted": rng.random(n) > 0.075,
            "email_domain_age": rng.integers(10, 6000, n),
            "tx_count_1h": rng.poisson(1.5, n),
            "tx_count_24h": rng.poisson(7, n) + 4,
            "amount_24h": np.round(base[customer] * rng.uniform(2, 12, n), 2),
            "failed_logins": rng.poisson(0.22, n),
            "password_reset": rng.random(n) < 0.018,
            "mfa_enabled": rng.random(n) > 0.05,
            "vpn_proxy": rng.random(n) < 0.07,
            "distance_km": np.round(rng.exponential(65, n), 1),
            "new_payment_method": rng.random(n) < 0.06,
            "recent_method_change": rng.random(n) < 0.03,
            "ownership_match": rng.random(n) > 0.015,
            "prior_chargebacks": rng.binomial(3, 0.035, n),
            "prior_fraud_reports": rng.binomial(2, 0.006, n),
            "recipient_age": rng.integers(1, 900, n),
            "recipient_risk": rng.choice(
                ["low", "medium", "high"], n, p=[0.92, 0.065, 0.015]
            ),
            "minutes_since_deposit": rng.integers(60, 20000, n).astype(float),
            "hours_since_last_location": rng.uniform(2, 72, n),
            "is_fraud": fraud,
            "fraud_category": categories,
        }
    )
    # Overlapping legitimate outliers keep labels imperfectly separable from controls.
    noisy = rng.random(n) < 0.035
    for category in CATEGORIES:
        m = (d.fraud_category == category) | (noisy & (rng.random(n) < 0.12))
        count = int(m.sum())
        if category in ["Account takeover", "Authentication attack"]:
            d.loc[m, "failed_logins"] = rng.integers(3, 12, count)
            d.loc[m, "password_reset"] = True
            d.loc[m, "mfa_enabled"] = rng.random(count) > 0.65
            d.loc[m, "device_trusted"] = False
        if category in ["Stolen credentials", "ACH return abuse"]:
            d.loc[m, "ownership_match"] = False
            d.loc[m, "prior_chargebacks"] = rng.integers(1, 6, count)
            d.loc[m, "new_payment_method"] = True
            if category == "ACH return abuse":
                d.loc[m, "payment_rail"] = "ACH"
        if category in ["New-account fraud", "Mule account"]:
            d.loc[m, "account_age"] = rng.integers(0, 28, count)
            d.loc[m, "amount"] *= rng.uniform(5, 20, count)
            d.loc[m, "direction"] = "withdrawal"
            d.loc[m, "recipient_risk"] = "high"
        if category in ["Card testing", "Velocity abuse"]:
            d.loc[m, "tx_count_1h"] = rng.integers(7, 35, count)
            if category == "Card testing":
                d.loc[m, "amount"] = np.round(rng.uniform(1, 9, count), 2)
                d.loc[m, "payment_rail"] = "Credit card"
        if category in ["Rapid cash-out", "Crypto off-ramp"]:
            d.loc[m, "minutes_since_deposit"] = rng.integers(1, 25, count)
            d.loc[m, "direction"] = "withdrawal"
            d.loc[m, "amount"] *= 8
            if category == "Crypto off-ramp":
                d.loc[m, "payment_rail"] = "Crypto"
        if category == "Shared device":
            d.loc[m, "device_id"] = [f"DV-CLUSTER-{i % 12}" for i in range(count)]
        if category == "Device hopping":
            d.loc[m, "device_id"] = [f"DV-NOVEL-{i}" for i in range(count)]
            d.loc[m, "device_trusted"] = False
        if category in ["Impossible travel", "Proxy abuse"]:
            d.loc[m, "distance_km"] = rng.uniform(1500, 9500, count)
            d.loc[m, "hours_since_last_location"] = rng.uniform(0.5, 2, count)
            d.loc[m, "vpn_proxy"] = True
            d.loc[m, "amount"] *= 4
        if category == "Unusual amount":
            d.loc[m, "amount"] *= rng.uniform(8, 25, count)
        if category in ["Risky recipient", "Mule account"]:
            d.loc[m, "recipient_risk"] = "high"
            d.loc[m, "recipient_age"] = rng.integers(0, 5, count)
    d["amount"] = d.amount.clip(1, 100000).round(2)
    d["tx_count_24h"] = np.maximum(d.tx_count_24h, d.tx_count_1h)
    d["customer_tenure"] = np.maximum(d.customer_tenure, d.account_age)
    d["crypto_asset"] = np.where(
        d.payment_rail == "Crypto", rng.choice(["BTC", "ETH", "USDC"], n), ""
    )
    return d
