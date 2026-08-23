"""
Spatial Indexing Engine for Dynamic ATM Candidate Retrieval.

Uses spherical geometry and nearest-neighbor search (BallTree/KDTree) to retrieve
geographically proximate ATMs within radius R or Top-K nearest ATMs for any input coordinate.
Zero hardcoding of ATM count or regional boundaries.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from sklearn.neighbors import BallTree


class SpatialIndex:
    """
    Geospatial index over physical ATM coordinates using BallTree with Haversine metric.
    Accepts arbitrary ATM DataFrames or master records at runtime.
    """

    EARTH_RADIUS_KM = 6371.0088

    def __init__(self, atm_df: pd.DataFrame):
        """
        Initialize the spatial index with an ATM dataset.

        Args:
            atm_df: DataFrame containing at minimum ['atm_id', 'latitude', 'longitude'].
                    Optional columns: 'atm_name', 'bank_name', 'city', 'district', 'location_type'.
        """
        self.atm_df = atm_df.copy().reset_index(drop=True)
        self._validate_schema()
        self._build_index()

    def _validate_schema(self) -> None:
        required_cols = {"atm_id", "latitude", "longitude"}
        missing = required_cols - set(self.atm_df.columns)
        if missing:
            raise ValueError(f"ATM dataset missing required columns for spatial indexing: {missing}")

        # Ensure numeric coordinates
        self.atm_df["latitude"] = pd.to_numeric(self.atm_df["latitude"], errors="coerce")
        self.atm_df["longitude"] = pd.to_numeric(self.atm_df["longitude"], errors="coerce")

        if self.atm_df["latitude"].isna().any() or self.atm_df["longitude"].isna().any():
            raise ValueError("ATM dataset contains NaN or non-numeric coordinates.")

    def _build_index(self) -> None:
        # BallTree with haversine requires radians (lat, lon)
        coords_rad = np.radians(self.atm_df[["latitude", "longitude"]].values)
        self.tree = BallTree(coords_rad, metric="haversine")
        self.n_atms = len(self.atm_df)

    def query_radius(self, lat: float, lon: float, radius_km: float = 50.0) -> List[Dict[str, Any]]:
        """
        Retrieve all ATMs within radius_km of (lat, lon).

        Returns:
            List of ATM dicts with calculated distance_km, sorted by distance ascending.
        """
        query_rad = np.radians(np.array([[lat, lon]]))
        radius_rad = radius_km / self.EARTH_RADIUS_KM

        indices, distances = self.tree.query_radius(query_rad, r=radius_rad, return_distance=True, sort_results=True)

        matched_indices = indices[0]
        matched_distances_km = distances[0] * self.EARTH_RADIUS_KM

        results = []
        for idx, dist in zip(matched_indices, matched_distances_km):
            row = self.atm_df.iloc[idx].to_dict()
            row["distance_km"] = float(dist)
            results.append(row)
        return results

    def query_knn(self, lat: float, lon: float, k: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve Top-K nearest ATMs to (lat, lon).

        Returns:
            List of ATM dicts with calculated distance_km, sorted by distance ascending.
        """
        k = min(k, self.n_atms)
        query_rad = np.radians(np.array([[lat, lon]]))

        distances, indices = self.tree.query(query_rad, k=k)

        matched_indices = indices[0]
        matched_distances_km = distances[0] * self.EARTH_RADIUS_KM

        results = []
        for idx, dist in zip(matched_indices, matched_distances_km):
            row = self.atm_df.iloc[idx].to_dict()
            row["distance_km"] = float(dist)
            results.append(row)
        return results

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate exact Haversine distance in km between two coordinate points."""
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)

        a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return float(SpatialIndex.EARTH_RADIUS_KM * c)
