"""Generate complaints.csv — the main fraud-case table."""

import numpy as np
import pandas as pd
from config import CITIES, FRAUD_TYPES, CHANNELS, DEVICE_TYPES, N_COMPLAINTS, SIM_START, SIM_END
from utils import jitter_latlon, weighted_choice, random_pincode, id_series, random_timestamps


def generate_complaints(rng):
    city_w = [c[5] for c in CITIES]
    chosen_cities = weighted_choice(rng, CITIES, city_w, N_COMPLAINTS)
    lat0 = np.array([c[3] for c in chosen_cities])
    lon0 = np.array([c[4] for c in chosen_cities])
    lat, lon = jitter_latlon(rng, lat0, lon0, max_km=15.0)

    fraud_names = [f[0] for f in FRAUD_TYPES]
    fraud_w = [f[1] for f in FRAUD_TYPES]
    fraud_type = weighted_choice(rng, fraud_names, fraud_w, N_COMPLAINTS)

    incident_ts = random_timestamps(rng, SIM_START, SIM_END, N_COMPLAINTS)
    # Reporting delay: cybercrime helplines (e.g. 1930) push for fast reporting
    # to enable freezing funds before cashout, so most victims report within a
    # few hours; a long tail still reports days later.
    report_delay_hours = rng.gamma(shape=2.0, scale=1.8, size=N_COMPLAINTS)
    complaint_ts = incident_ts + pd.to_timedelta(report_delay_hours, unit="h")

    # Loss amount: log-normal, varies by fraud type severity
    severity_mult = np.array([_severity(f) for f in fraud_type])
    reported_loss = np.round(rng.lognormal(mean=9.2, sigma=1.1, size=N_COMPLAINTS) * severity_mult, 2)
    reported_loss = np.clip(reported_loss, 500, 5_000_000)

    rural_urban = rng.choice(["Urban", "Semi-Urban", "Rural"], size=N_COMPLAINTS, p=[0.62, 0.28, 0.10])

    df = pd.DataFrame({
        "complaint_id": id_series("CASE", N_COMPLAINTS),
        "complaint_timestamp": complaint_ts,
        "incident_timestamp": incident_ts,
        "fraud_type": fraud_type,
        "channel": rng.choice(CHANNELS, size=N_COMPLAINTS, p=_channel_weights()),
        "reported_loss_amount": reported_loss,
        "victim_state": [c[1] for c in chosen_cities],
        "victim_district": [c[2] for c in chosen_cities],
        "victim_city": [c[0] for c in chosen_cities],
        "victim_area": [f"Area-{rng.integers(1, 60)}" for _ in range(N_COMPLAINTS)],
        "victim_pincode": [random_pincode(rng, str(rng.integers(40, 83))) for _ in range(N_COMPLAINTS)],
        "victim_lat": lat,
        "victim_lon": lon,
        "victim_rural_urban": rural_urban,
        "victim_bank": rng.choice(
            ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank",
             "Bank of Baroda", "Kotak Mahindra Bank", "Canara Bank"], size=N_COMPLAINTS),
        "device_type": rng.choice(DEVICE_TYPES, size=N_COMPLAINTS, p=[0.55, 0.30, 0.13, 0.02]),
        "is_otp_shared": rng.choice([0, 1], size=N_COMPLAINTS, p=[0.55, 0.45]),
        "clicked_malicious_link": rng.choice([0, 1], size=N_COMPLAINTS, p=[0.68, 0.32]),
        "urgency_score": np.round(rng.beta(2.5, 2.0, size=N_COMPLAINTS), 3),
        "account_age_months": rng.integers(1, 240, size=N_COMPLAINTS),
        "num_transactions": rng.poisson(3.2, size=N_COMPLAINTS) + 1,
        "fraud_description_category": fraud_type,  # kept aligned with fraud_type per spec
    })
    return df


def _severity(fraud_type):
    table = {
        "Investment Scam": 3.5, "Impersonation (Digital Arrest/Officer)": 2.8,
        "Loan App Scam": 1.6, "Remote Access Scam": 1.8, "UPI Fraud": 1.0,
        "Phishing": 1.1, "Card Fraud": 1.3, "OTP Fraud": 1.0,
        "Fake Customer Care": 1.2, "Marketplace Fraud (OLX/e-commerce)": 0.7,
        "Social Engineering (Romance/Job)": 2.0,
    }
    return table.get(fraud_type, 1.0)


def _channel_weights():
    from config import CHANNELS
    table = {"UPI": 34, "Net Banking": 16, "Card": 15, "IMPS": 14, "NEFT": 8, "Wallet": 9, "ATM": 4}
    w = np.array([table[c] for c in CHANNELS], dtype=float)
    return w / w.sum()
