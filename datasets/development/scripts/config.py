"""
Central configuration for the synthetic cybercrime ATM-prediction dataset generator.

IMPORTANT — SCALE NOTE:
The full production target sizes (50,000 complaints / 250k-500k transactions /
5-20 MILLION rank pairs) are defined here exactly as specified, and every script
in this pipeline is written to run at that scale unmodified. However, generating
and validating 5-20 million feature-rich rows requires substantial RAM/CPU/time
(realistically tens of GB of memory and a dedicated machine, not an interactive
sandbox). This config exposes a SCALE variable so the *exact same code* can be
run as:
  - "demo"  : small, fast, fully validated end-to-end (default here)
  - "dev"   : the dev dataset sizes from the spec (5,000 complaints)
  - "full"  : the full production sizes from the spec (50,000 complaints)

Nothing about the logic changes between scales — only these counts.
"""

import os

SEED = 42
SCALE = os.environ.get("DATASET_SCALE", "demo")  # demo | dev | full

# ----------------------------------------------------------------------------
# Size presets
# ----------------------------------------------------------------------------
SIZE_PRESETS = {
    "full": dict(
        n_complaints=50_000,
        n_transactions=350_000,      # within 250k-500k
        n_accounts=40_000,           # within 30k-50k
        n_atms=7_000,                # within 5k-10k
        n_withdrawals=50_000,
        candidate_recall_targets=[50, 100, 200, 300],
    ),
    "dev": dict(
        n_complaints=5_000,
        n_transactions=35_000,
        n_accounts=7_000,
        n_atms=1_500,
        n_withdrawals=5_000,
        candidate_recall_targets=[50, 100, 200, 300],
    ),
    "demo": dict(
        # Small enough to generate + validate + compute Recall@K quickly in a
        # single interactive run, same schema/logic as dev/full.
        n_complaints=1_200,
        n_transactions=9_000,
        n_accounts=1_800,
        n_atms=400,
        n_withdrawals=1_200,
        candidate_recall_targets=[20, 40, 60, 80],
    ),
}

CFG = SIZE_PRESETS[SCALE]

N_COMPLAINTS = CFG["n_complaints"]
N_TRANSACTIONS = CFG["n_transactions"]
N_ACCOUNTS = CFG["n_accounts"]
N_ATMS = CFG["n_atms"]
N_WITHDRAWALS = CFG["n_withdrawals"]
CANDIDATE_RECALL_TARGETS = CFG["candidate_recall_targets"]

# Simulation time window (2 years of synthetic history ending "now")
SIM_END = "2026-06-30"
SIM_START = "2024-01-01"

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dataset")

# ----------------------------------------------------------------------------
# Geography: major Indian metros + surrounding districts/areas with plausible
# lat/lon bounding boxes (publicly known city centers; synthetic jitter applied
# within a small radius to place individual ATMs/victims realistically without
# claiming to be real addresses).
# ----------------------------------------------------------------------------
CITIES = [
    # city, state, district, lat, lon, weight (relative population/activity)
    ("Mumbai", "Maharashtra", "Mumbai City", 19.0760, 72.8777, 22),
    ("Thane", "Maharashtra", "Thane", 19.2183, 72.9781, 8),
    ("Navi Mumbai", "Maharashtra", "Thane", 19.0330, 73.0297, 7),
    ("Pune", "Maharashtra", "Pune", 18.5204, 73.8567, 14),
    ("Nashik", "Maharashtra", "Nashik", 19.9975, 73.7898, 6),
    ("Nagpur", "Maharashtra", "Nagpur", 21.1458, 79.0882, 7),
    ("Delhi", "Delhi", "New Delhi", 28.6139, 77.2090, 20),
    ("Bengaluru", "Karnataka", "Bengaluru Urban", 12.9716, 77.5946, 18),
    ("Hyderabad", "Telangana", "Hyderabad", 17.3850, 78.4867, 15),
    ("Chennai", "Tamil Nadu", "Chennai", 13.0827, 80.2707, 14),
    ("Kolkata", "West Bengal", "Kolkata", 22.5726, 88.3639, 13),
    ("Ahmedabad", "Gujarat", "Ahmedabad", 23.0225, 72.5714, 10),
    ("Jaipur", "Rajasthan", "Jaipur", 26.9124, 75.7873, 8),
    ("Lucknow", "Uttar Pradesh", "Lucknow", 26.8467, 80.9462, 7),
    ("Surat", "Gujarat", "Surat", 21.1702, 72.8311, 6),
    ("Indore", "Madhya Pradesh", "Indore", 22.7196, 75.8577, 5),
]

AREA_TYPES = ["Residential", "Commercial", "Mixed", "IT Park", "Old City", "Suburb", "Industrial"]

LOCATION_TYPES = [
    "Bank Branch ATM", "Railway Station ATM", "Bus Terminal ATM", "Mall ATM",
    "Market ATM", "Standalone Kiosk", "Petrol Station ATM", "Hospital ATM",
    "University ATM", "Airport ATM", "Residential Complex ATM",
]

BANKS = [
    "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank",
    "Bank of Baroda", "Kotak Mahindra Bank", "Canara Bank", "Union Bank of India",
    "IDFC First Bank", "Yes Bank", "IndusInd Bank",
]

FRAUD_TYPES = [
    # fraud_type, relative weight
    ("UPI Fraud", 24),
    ("Phishing", 15),
    ("Investment Scam", 13),
    ("Impersonation (Digital Arrest/Officer)", 10),
    ("Remote Access Scam", 9),
    ("Card Fraud", 8),
    ("OTP Fraud", 7),
    ("Fake Customer Care", 6),
    ("Marketplace Fraud (OLX/e-commerce)", 5),
    ("Loan App Scam", 2),
    ("Social Engineering (Romance/Job)", 1),
]

CHANNELS = ["UPI", "Net Banking", "Card", "IMPS", "NEFT", "Wallet", "ATM"]
DEVICE_TYPES = ["Android", "iOS", "Desktop", "Feature Phone"]

MULE_ROLES = ["none", "first_hop_mule", "intermediary_mule", "cashout_mule", "hub_account"]
ACCOUNT_TYPES = ["victim", "ordinary_recipient", "mule", "intermediary", "high_volume", "suspicious_hub"]
