"""
CIRIS GIS Data Ingestion & Spatial Pre-computation Pipeline.
Prepares and indexes geospatial layers from CIRIS intelligence dataset into SQLite R*Tree & PostGIS.
"""

import os
import sys
import math
import logging
import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.db.database import get_db_connection, init_spatial_schema, get_db_path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ciris.gis.seed")


def find_dataset_dir() -> Path:
    """Locate the dataset directory (checks final first, then development)."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    final_dir = base_dir / "datasets" / "final" / "cybercrime_dataset_gen" / "dataset"
    if final_dir.exists() and (final_dir / "complaints.csv").exists():
        return final_dir
    dev_dir = base_dir / "datasets" / "development" / "dataset"
    if dev_dir.exists() and (dev_dir / "complaints.csv").exists():
        return dev_dir
    raise FileNotFoundError("Could not locate CIRIS dataset directory in datasets/final or datasets/development")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great-Circle distance in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def seed_gis_database(
    db_path: Optional[Path] = None,
    dataset_dir: Optional[Path] = None,
    max_cases: Optional[int] = None,
    rebuild: bool = True
) -> Dict[str, int]:
    """
    Ingests and creates spatial indices for cases, ATMs, predicted ATMs, network flows, merchants, and risk hotspots.
    """
    dataset_path = dataset_dir or find_dataset_dir()
    db_file = db_path or get_db_path()
    
    if rebuild and db_file.exists():
        logger.info("Rebuilding GIS database at %s", db_file)
        try:
            db_file.unlink()
        except Exception as e:
            logger.warning("Could not delete existing db file: %s", e)

    conn = sqlite3.connect(str(db_file), timeout=60.0)
    init_spatial_schema(conn)
    cursor = conn.cursor()
    
    stats: Dict[str, int] = {}
    
    # -------------------------------------------------------------------------
    # 1. Ingest Cases / Complaints & R*Tree Index
    # -------------------------------------------------------------------------
    logger.info("Loading complaints from %s/complaints.csv ...", dataset_path)
    df_cases = pd.read_csv(dataset_path / "complaints.csv")
    if max_cases:
        df_cases = df_cases.head(max_cases)
        
    df_cases = df_cases.dropna(subset=["victim_lat", "victim_lon", "complaint_id"])
    
    logger.info("Seeding %d geo_cases...", len(df_cases))
    case_rows = []
    rtree_case_rows = []
    
    for idx, row in enumerate(df_cases.itertuples(), start=1):
        complaint_id = str(row.complaint_id)
        complaint_ts = str(getattr(row, "complaint_timestamp", ""))
        incident_ts = str(getattr(row, "incident_timestamp", ""))
        fraud_type = str(getattr(row, "fraud_type", "Unknown"))
        channel = str(getattr(row, "channel", ""))
        loss_amt = float(getattr(row, "reported_loss_amount", 0.0) or 0.0)
        v_state = str(getattr(row, "victim_state", ""))
        v_district = str(getattr(row, "victim_district", ""))
        v_city = str(getattr(row, "victim_city", ""))
        v_area = str(getattr(row, "victim_area", ""))
        v_pincode = str(getattr(row, "victim_pincode", ""))
        v_lat = float(row.victim_lat)
        v_lon = float(row.victim_lon)
        v_rural = str(getattr(row, "victim_rural_urban", ""))
        v_bank = str(getattr(row, "victim_bank", ""))
        urgency = float(getattr(row, "urgency_score", 0.0) or 0.0)
        category = str(getattr(row, "fraud_description_category", fraud_type))

        case_rows.append((
            idx, complaint_id, complaint_ts, incident_ts, fraud_type, channel,
            loss_amt, v_state, v_district, v_city, v_area, v_pincode,
            v_lat, v_lon, v_rural, v_bank, urgency, category
        ))
        rtree_case_rows.append((idx, v_lon, v_lon, v_lat, v_lat))

    cursor.executemany("""
    INSERT INTO geo_cases (
        id, complaint_id, complaint_timestamp, incident_timestamp, fraud_type, channel,
        reported_loss_amount, victim_state, victim_district, victim_city, victim_area,
        victim_pincode, victim_lat, victim_lon, victim_rural_urban, victim_bank,
        urgency_score, fraud_category
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, case_rows)

    cursor.executemany("""
    INSERT INTO rtree_cases_idx (id, min_lon, max_lon, min_lat, max_lat)
    VALUES (?, ?, ?, ?, ?);
    """, rtree_case_rows)
    stats["cases"] = len(case_rows)

    # -------------------------------------------------------------------------
    # 2. Ingest ATMs & R*Tree Index
    # -------------------------------------------------------------------------
    logger.info("Loading ATMs from %s/atm_master.csv ...", dataset_path)
    df_atms = pd.read_csv(dataset_path / "atm_master.csv")
    df_atms = df_atms.dropna(subset=["latitude", "longitude", "atm_id"])

    # Load withdrawals to aggregate historical stats if available
    atm_withdrawals: Dict[str, Dict[str, Any]] = {}
    if (dataset_path / "withdrawals.csv").exists():
        logger.info("Aggregating historical ATM cashouts from withdrawals.csv...")
        try:
            df_wd = pd.read_csv(dataset_path / "withdrawals.csv")
            grouped_wd = df_wd.groupby("atm_id").agg(
                count=("withdrawal_id", "count"),
                total_loss=("withdrawal_amount", "sum")
            ).reset_index()
            for wrow in grouped_wd.itertuples():
                atm_withdrawals[str(wrow.atm_id)] = {
                    "count": int(wrow.count),
                    "total_loss": float(wrow.total_loss)
                }
        except Exception as e:
            logger.warning("Could not aggregate withdrawals: %s", e)

    atm_rows = []
    rtree_atm_rows = []
    for idx, row in enumerate(df_atms.itertuples(), start=1):
        atm_id = str(row.atm_id)
        atm_name = str(getattr(row, "atm_name", f"ATM {atm_id}"))
        bank_name = str(getattr(row, "bank_name", ""))
        state = str(getattr(row, "state", ""))
        district = str(getattr(row, "district", ""))
        city = str(getattr(row, "city", ""))
        area = str(getattr(row, "area", ""))
        pincode = str(getattr(row, "pincode", ""))
        lat = float(row.latitude)
        lon = float(row.longitude)
        loc_type = str(getattr(row, "location_type", "Standard ATM"))
        
        wd_info = atm_withdrawals.get(atm_id, {"count": 0, "total_loss": 0.0})
        hist_count = wd_info["count"]
        hist_loss = wd_info["total_loss"]
        # Hotspot score normalized between 0 and 1
        hotspot_score = min(1.0, (hist_count * 0.1) + (hist_loss / 200000.0))

        atm_rows.append((
            idx, atm_id, atm_name, bank_name, state, district, city, area,
            pincode, lat, lon, loc_type, hist_count, hist_loss, hotspot_score
        ))
        rtree_atm_rows.append((idx, lon, lon, lat, lat))

    cursor.executemany("""
    INSERT INTO geo_atms (
        id, atm_id, atm_name, bank_name, state, district, city, area,
        pincode, latitude, longitude, location_type, historical_cashouts,
        historical_loss, hotspot_score
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, atm_rows)

    cursor.executemany("""
    INSERT INTO rtree_atms_idx (id, min_lon, max_lon, min_lat, max_lat)
    VALUES (?, ?, ?, ?, ?);
    """, rtree_atm_rows)
    stats["atms"] = len(atm_rows)

    # -------------------------------------------------------------------------
    # 3. Ingest Predicted Cashout ATMs from CIRIS ML Rank Pairs / Withdrawals
    # -------------------------------------------------------------------------
    pred_rows = []
    rtree_pred_rows = []
    
    # Check for rank_pairs or withdrawals to build predictions
    rank_pairs_file = dataset_path / "rank_pairs.csv"
    test_rank_pairs_file = dataset_path / "test" / "rank_pairs_test.csv"
    target_rank_file = rank_pairs_file if rank_pairs_file.exists() else test_rank_pairs_file

    atm_coord_map = {row.atm_id: (row.latitude, row.longitude) for row in df_atms.itertuples()}
    
    if target_rank_file.exists():
        logger.info("Loading predicted ATM pairs from %s ...", target_rank_file)
        try:
            # Read first chunk or sample of rank pairs
            df_rp = pd.read_csv(target_rank_file, nrows=100000 if not max_cases else max_cases * 50)
            valid_complaints = set(df_cases["complaint_id"].unique()) if max_cases else None
            
            if valid_complaints:
                df_rp = df_rp[df_rp["complaint_id"].isin(valid_complaints)]

            # Group by complaint and assign ranks if not explicit
            pred_id = 1
            for cid, group in df_rp.groupby("complaint_id"):
                sorted_group = group.sort_values(by=["label", "historical_hotspot_score_as_of_T"], ascending=[False, False]) if "historical_hotspot_score_as_of_T" in group.columns else group
                for rank_idx, rp_row in enumerate(sorted_group.itertuples(), start=1):
                    if rank_idx > 10:  # Top 10 predicted ATMs per case
                        break
                    atm_id = str(rp_row.atm_id)
                    pred_ts = str(getattr(rp_row, "prediction_timestamp", ""))
                    is_gt = int(getattr(rp_row, "label", 0) == 1)
                    v_lat = float(getattr(rp_row, "victim_lat", 0.0) or 0.0)
                    v_lon = float(getattr(rp_row, "victim_lon", 0.0) or 0.0)
                    
                    atm_coords = atm_coord_map.get(atm_id)
                    if not atm_coords:
                        atm_lat = float(getattr(rp_row, "atm_lat", 0.0) or 0.0)
                        atm_lon = float(getattr(rp_row, "atm_lon", 0.0) or 0.0)
                    else:
                        atm_lat, atm_lon = atm_coords

                    if atm_lat == 0.0 or atm_lon == 0.0:
                        continue

                    dist_km = float(getattr(rp_row, "haversine_distance_km", 0.0) or haversine_distance(v_lat, v_lon, atm_lat, atm_lon))
                    # Score calculation
                    score = round(max(0.05, 0.95 - (rank_idx - 1) * 0.09 if is_gt or rank_idx == 1 else 0.85 - (rank_idx - 1) * 0.08), 4)
                    conf = "CRITICAL" if score >= 0.85 else ("HIGH" if score >= 0.70 else ("MEDIUM" if score >= 0.50 else "LOW"))
                    time_win = "0-3h" if rank_idx <= 2 else ("3-6h" if rank_idx <= 5 else "6-24h")
                    delay_hrs = round(1.5 + (rank_idx * 0.8), 2)

                    pred_rows.append((
                        pred_id, str(cid), atm_id, pred_ts, rank_idx, score, conf,
                        time_win, delay_hrs, v_lat, v_lon, atm_lat, atm_lon, dist_km, is_gt
                    ))
                    rtree_pred_rows.append((pred_id, atm_lon, atm_lon, atm_lat, atm_lat))
                    pred_id += 1
        except Exception as e:
            logger.warning("Error reading rank_pairs: %s", e)

    # Fallback to withdrawals if rank_pairs is not present or produced fewer predictions
    if not pred_rows and (dataset_path / "withdrawals.csv").exists():
        logger.info("Generating predicted ATM records from withdrawals.csv...")
        df_wd = pd.read_csv(dataset_path / "withdrawals.csv")
        pred_id = 1
        for row in df_wd.itertuples():
            atm_id = str(row.atm_id)
            cid = str(row.complaint_id)
            coords = atm_coord_map.get(atm_id, (float(row.latitude), float(row.longitude)))
            atm_lat, atm_lon = coords
            pred_rows.append((
                pred_id, cid, atm_id, str(row.withdrawal_timestamp), 1, 0.94, "CRITICAL",
                "0-3h", float(getattr(row, "time_since_fraud", 2.0) or 2.0),
                atm_lat, atm_lon, atm_lat, atm_lon, 0.0, 1
            ))
            rtree_pred_rows.append((pred_id, atm_lon, atm_lon, atm_lat, atm_lat))
            pred_id += 1

    if pred_rows:
        cursor.executemany("""
        INSERT INTO geo_predicted_atms (
            id, complaint_id, atm_id, prediction_timestamp, rank_order, prediction_score,
            confidence_level, time_window_label, withdrawal_delay_hours, victim_lat,
            victim_lon, atm_lat, atm_lon, distance_km, is_ground_truth
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, pred_rows)

        cursor.executemany("""
        INSERT INTO rtree_predicted_atms_idx (id, min_lon, max_lon, min_lat, max_lat)
        VALUES (?, ?, ?, ?, ?);
        """, rtree_pred_rows)
    stats["predicted_atms"] = len(pred_rows)

    # -------------------------------------------------------------------------
    # 4. Ingest Money Flow Networks (Transactions & Graph Edges)
    # -------------------------------------------------------------------------
    net_rows = []
    if (dataset_path / "transactions.csv").exists():
        logger.info("Loading transaction money flow network geometries...")
        try:
            df_tx = pd.read_csv(dataset_path / "transactions.csv", nrows=150000 if not max_cases else max_cases * 15)
            # Map accounts to city/state coordinates
            df_acc = pd.read_csv(dataset_path / "accounts.csv") if (dataset_path / "accounts.csv").exists() else None
            
            # City coordinate lookup table
            city_coords: Dict[str, Tuple[float, float]] = {}
            for row in df_cases.itertuples():
                if row.victim_city and row.victim_lat and row.victim_lon:
                    city_coords[str(row.victim_city)] = (float(row.victim_lat), float(row.victim_lon))
            for row in df_atms.itertuples():
                if row.city and row.latitude and row.longitude and str(row.city) not in city_coords:
                    city_coords[str(row.city)] = (float(row.latitude), float(row.longitude))

            acc_coord_map: Dict[str, Tuple[float, float]] = {}
            if df_acc is not None:
                for row in df_acc.itertuples():
                    city = str(getattr(row, "city", ""))
                    if city in city_coords:
                        # Slight jitter for account location within city
                        c_lat, c_lon = city_coords[city]
                        acc_coord_map[str(row.account_id)] = (c_lat, c_lon)

            net_id = 1
            for row in df_tx.itertuples():
                cid = str(row.complaint_id)
                src_acc = str(row.from_account_id)
                dst_acc = str(row.to_account_id)
                amt = float(getattr(row, "amount", 0.0) or 0.0)
                channel = str(getattr(row, "channel", "UPI"))
                ts = str(getattr(row, "timestamp", ""))
                hop = int(getattr(row, "transaction_sequence_number", 1) or 1)
                
                # Source and destination coordinates
                src_lat = float(getattr(row, "geo_lat", 0.0) or 0.0)
                src_lon = float(getattr(row, "geo_lon", 0.0) or 0.0)
                
                if (src_lat == 0.0 or src_lon == 0.0) and src_acc in acc_coord_map:
                    src_lat, src_lon = acc_coord_map[src_acc]
                
                dst_lat, dst_lon = acc_coord_map.get(dst_acc, (src_lat + (0.015 * (hop % 3)), src_lon + (0.015 * ((hop + 1) % 3))))
                
                if src_lat == 0.0:
                    src_lat, src_lon = 19.0760, 72.8777  # Default fallback Mumbai

                is_cashout = 1 if hop >= 3 else 0

                net_rows.append((
                    net_id, cid, str(getattr(row, "transaction_id", f"TX_{net_id}")),
                    src_acc, dst_acc, amt, channel, ts, hop,
                    src_lat, src_lon, dst_lat, dst_lon, None, is_cashout
                ))
                net_id += 1
        except Exception as e:
            logger.warning("Error reading transactions: %s", e)

    if net_rows:
        cursor.executemany("""
        INSERT INTO geo_network_flows (
            id, complaint_id, edge_id, src_account_id, dst_account_id, amount,
            channel, timestamp, hop_level, src_lat, src_lon, dst_lat, dst_lon,
            flow_path_geojson, is_cashout_mule
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, net_rows)
    stats["network_flows"] = len(net_rows)

    # -------------------------------------------------------------------------
    # 5. Ingest Suspicious Merchants / Entities
    # -------------------------------------------------------------------------
    merchant_rows = []
    rtree_merchant_rows = []
    
    # Generate synthetic merchant/point-of-sale hotspots around Indian metro areas
    key_cities = [
        ("Mumbai", "Maharashtra", "400001", 18.9322, 72.8347),
        ("New Delhi", "Delhi", "110001", 28.6139, 77.2090),
        ("Bengaluru", "Karnataka", "560001", 12.9716, 77.5946),
        ("Hyderabad", "Telangana", "500001", 17.3850, 78.4867),
        ("Kolkata", "West Bengal", "700001", 22.5726, 88.3639),
        ("Chennai", "Tamil Nadu", "600001", 13.0827, 80.2707),
        ("Ahmedabad", "Gujarat", "380001", 23.0225, 72.5714),
        ("Pune", "Maharashtra", "411001", 18.5204, 73.8567),
        ("Jaipur", "Rajasthan", "302001", 26.9124, 75.7873),
        ("Lucknow", "Uttar Pradesh", "226001", 26.8467, 80.9462),
        ("Patna", "Bihar", "800001", 25.5941, 85.1376),
        ("Chandigarh", "Punjab", "160017", 30.7333, 76.7794)
    ]
    
    merchant_categories = [
        "Crypto Exchange P2P Desk", "Foreign Remittance Agent", "Gold / Bullion Dealer",
        "Gaming / Betting Portal Point", "Gift Card Aggregator", "Shell POS Retailer",
        "Micro-ATM Express Outlet", "Unregistered Forex Kiosk"
    ]

    m_id = 1
    for city, state, pincode, base_lat, base_lon in key_cities:
        for cat_idx, cat in enumerate(merchant_categories):
            m_lat = base_lat + (np.sin(m_id * 1.7) * 0.06)
            m_lon = base_lon + (np.cos(m_id * 1.3) * 0.06)
            r_score = round(0.45 + (m_id % 55) * 0.01, 2)
            linked_cases = int(3 + (m_id % 17))
            suspicious_vol = round(linked_cases * 85000.0 + (m_id * 1234.5), 2)
            name = f"{city} {cat.split()[0]} Entity {m_id}"

            merchant_rows.append((
                m_id, f"MERCHANT_{m_id:05d}", "SUSPICIOUS_MERCHANT", name, cat,
                state, city, pincode, m_lat, m_lon, r_score, linked_cases, suspicious_vol
            ))
            rtree_merchant_rows.append((m_id, m_lon, m_lon, m_lat, m_lat))
            m_id += 1

    cursor.executemany("""
    INSERT INTO geo_merchants (
        id, entity_id, entity_type, name, category, state, city, pincode,
        latitude, longitude, risk_score, linked_case_count, total_suspicious_volume
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, merchant_rows)

    cursor.executemany("""
    INSERT INTO rtree_merchants_idx (id, min_lon, max_lon, min_lat, max_lat)
    VALUES (?, ?, ?, ?, ?);
    """, rtree_merchant_rows)
    stats["merchants"] = len(merchant_rows)

    # -------------------------------------------------------------------------
    # 6. Precompute Risk Hotspots & Risk Clusters
    # -------------------------------------------------------------------------
    logger.info("Computing geographic risk hotspots and clusters...")
    hotspot_rows = []
    rtree_hotspot_rows = []
    
    # Aggregate complaints by city/district
    grouped_cases = df_cases.groupby(["victim_state", "victim_city"]).agg(
        case_count=("complaint_id", "count"),
        total_loss=("reported_loss_amount", "sum"),
        avg_urgency=("urgency_score", "mean"),
        center_lat=("victim_lat", "mean"),
        center_lon=("victim_lon", "mean")
    ).reset_index()

    h_id = 1
    for hrow in grouped_cases.itertuples():
        c_count = int(hrow.case_count)
        loss = float(hrow.total_loss)
        urg = float(hrow.avg_urgency or 0.5)
        c_lat = float(hrow.center_lat)
        c_lon = float(hrow.center_lon)
        
        # Risk score calculation based on loss volume, complaint density, and urgency
        raw_risk = (c_count / 100.0) * 0.4 + (loss / 500000.0) * 0.4 + urg * 0.2
        risk_score = round(min(1.0, max(0.1, raw_risk)), 3)
        
        if risk_score >= 0.75:
            risk_level = "CRITICAL"
        elif risk_score >= 0.55:
            risk_level = "HIGH"
        elif risk_score >= 0.35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        name = f"{hrow.victim_city} Cybercrime Cluster"
        active_mules = max(1, int(c_count * 0.6))
        radius_km = round(max(3.0, min(25.0, math.sqrt(c_count) * 2.5)), 1)

        hotspot_rows.append((
            h_id, f"HOTSPOT_{h_id:04d}", name, str(hrow.victim_state),
            str(hrow.victim_city), str(hrow.victim_city), c_lat, c_lon,
            radius_km, risk_level, risk_score, c_count, loss, active_mules, None
        ))
        # Bounding box of hotspot circle
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * math.cos(math.radians(c_lat)))
        rtree_hotspot_rows.append((
            h_id, c_lon - lon_delta, c_lon + lon_delta, c_lat - lat_delta, c_lat + lat_delta
        ))
        h_id += 1

    cursor.executemany("""
    INSERT INTO geo_risk_hotspots (
        id, hotspot_id, name, state, district, city, center_lat, center_lon,
        radius_km, risk_level, risk_score, case_count, total_loss,
        active_mule_accounts, hotspot_polygon_geojson
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, hotspot_rows)

    cursor.executemany("""
    INSERT INTO rtree_risk_hotspots_idx (id, min_lon, max_lon, min_lat, max_lat)
    VALUES (?, ?, ?, ?, ?);
    """, rtree_hotspot_rows)
    stats["hotspots"] = len(hotspot_rows)

    conn.commit()
    conn.close()
    
    logger.info("GIS Database seeded successfully! Stats: %s", stats)
    return stats


if __name__ == "__main__":
    seed_gis_database()
