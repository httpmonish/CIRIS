"""Generate atm_master.csv — the candidate withdrawal-location universe."""

import numpy as np
import pandas as pd
from config import CITIES, LOCATION_TYPES, BANKS, N_ATMS
from utils import jitter_latlon, weighted_choice, random_pincode, id_series


def generate_atms(rng):
    city_names = [c[0] for c in CITIES]
    weights = [c[5] for c in CITIES]
    chosen_cities = weighted_choice(rng, CITIES, weights, N_ATMS)

    lat0 = np.array([c[3] for c in chosen_cities])
    lon0 = np.array([c[4] for c in chosen_cities])
    lat, lon = jitter_latlon(rng, lat0, lon0, max_km=12.0)

    atm_ids = id_series("ATM", N_ATMS)
    banks = rng.choice(BANKS, size=N_ATMS)
    loc_types = rng.choice(
        LOCATION_TYPES, size=N_ATMS,
        p=_loc_type_weights(),
    )

    df = pd.DataFrame({
        "atm_id": atm_ids,
        "atm_name": [f"{b} {lt} {i+1}" for i, (b, lt) in enumerate(zip(banks, loc_types))],
        "bank_name": banks,
        "state": [c[1] for c in chosen_cities],
        "district": [c[2] for c in chosen_cities],
        "city": [c[0] for c in chosen_cities],
        "area": [f"Area-{rng.integers(1, 60)}" for _ in range(N_ATMS)],
        "pincode": [random_pincode(rng, str(rng.integers(40, 83))) for _ in range(N_ATMS)],
        "latitude": lat,
        "longitude": lon,
        "location_type": loc_types,
    })
    return df


def _loc_type_weights():
    # Bank branch / market / mall ATMs are more common than airport/hospital ATMs.
    raw = {
        "Bank Branch ATM": 22, "Railway Station ATM": 9, "Bus Terminal ATM": 7,
        "Mall ATM": 12, "Market ATM": 14, "Standalone Kiosk": 15,
        "Petrol Station ATM": 10, "Hospital ATM": 5, "University ATM": 4,
        "Airport ATM": 2, "Residential Complex ATM": 10,
    }
    w = np.array([raw[t] for t in LOCATION_TYPES], dtype=float)
    return w / w.sum()
