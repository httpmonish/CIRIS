"""Shared helper functions used across the generation pipeline."""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    """Vectorized haversine distance in km. Accepts scalars or numpy arrays."""
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.minimum(1.0, np.sqrt(a)))
    return EARTH_RADIUS_KM * c


def jitter_latlon(rng, lat, lon, max_km=8.0):
    """Jitter a base city lat/lon within a plausible radius (km) so entities
    spread across a metro area rather than stacking on the exact city center."""
    n = np.atleast_1d(lat).shape[0]
    r = rng.uniform(0, max_km, size=n)
    theta = rng.uniform(0, 2 * np.pi, size=n)
    dlat = (r * np.cos(theta)) / 111.0
    dlon = (r * np.sin(theta)) / (111.0 * np.cos(np.radians(np.atleast_1d(lat))))
    return np.atleast_1d(lat) + dlat, np.atleast_1d(lon) + dlon


def weighted_choice(rng, items, weights, size):
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    idx = rng.choice(len(items), size=size, p=weights)
    return [items[i] for i in idx]


def random_pincode(rng, base_prefix):
    return f"{base_prefix}{rng.integers(100, 999):03d}"


def id_series(prefix, n, width=6):
    return [f"{prefix}_{i+1:0{width}d}" for i in range(n)]


def random_timestamps(rng, start, end, size):
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    total_seconds = (end_ts - start_ts).total_seconds()
    offsets = rng.uniform(0, total_seconds, size=size)
    return pd.to_datetime(start_ts) + pd.to_timedelta(offsets, unit="s")


def time_window_label(delay_hours):
    """Map a withdrawal delay (in hours) to the 5-class time-window label."""
    bins = [0, 1, 3, 6, 12, 24, np.inf]
    labels = [0, 1, 2, 3, 4, 4]  # anything >=24h folds into class 4 (12-24h+) to
    # keep every row labelable; see README for the boundary note.
    idx = np.digitize(delay_hours, bins[1:-1], right=False)
    idx = np.clip(idx, 0, len(labels) - 1)
    return np.array(labels)[idx]


def bayesian_smooth(successes, totals, prior_mean, prior_strength=10.0):
    """Smooth a rate (e.g. cashout rate) for sparse/new entities."""
    successes = np.asarray(successes, dtype=float)
    totals = np.asarray(totals, dtype=float)
    return (successes + prior_strength * prior_mean) / (totals + prior_strength)
