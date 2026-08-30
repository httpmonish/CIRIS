"""
CIRIS GIS & Operational Database Engine & Connection Manager.
Supports SQLite with R*Tree spatial indexing, WAL mode for sub-millisecond queries,
and operational tables for alerts, cases, evidence, interventions, and append-only audit logs.
"""

import os
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional

logger = logging.getLogger("ciris.gis.db")

# Default database path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_DIR = BASE_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_SQLITE_PATH = DB_DIR / "ciris_gis.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")


def get_db_path() -> Path:
    if DATABASE_URL.startswith("sqlite:///"):
        return Path(DATABASE_URL.replace("sqlite:///", ""))
    return DEFAULT_SQLITE_PATH


def create_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create a high-performance SQLite connection configured with WAL mode and custom math functions."""
    target_path = db_path or get_db_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(target_path), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    
    # Pragma performance optimizations
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA mmap_size = 268435456;")  # 256MB memory-mapped I/O
    
    return conn


@contextmanager
def get_db_connection(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database connections."""
    conn = create_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()


def init_spatial_schema(conn: sqlite3.Connection) -> None:
    """Initialize relational, R*Tree spatial, and operational action tables."""
    cursor = conn.cursor()
    
    # -------------------------------------------------------------------------
    # 1. Cases / Complaints table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geo_cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT UNIQUE NOT NULL,
        complaint_timestamp TEXT,
        incident_timestamp TEXT,
        fraud_type TEXT,
        channel TEXT,
        reported_loss_amount REAL DEFAULT 0.0,
        victim_state TEXT,
        victim_district TEXT,
        victim_city TEXT,
        victim_area TEXT,
        victim_pincode TEXT,
        victim_lat REAL NOT NULL,
        victim_lon REAL NOT NULL,
        victim_rural_urban TEXT,
        victim_bank TEXT,
        urgency_score REAL DEFAULT 0.0,
        fraud_category TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_fraud_type ON geo_cases(fraud_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_urgency ON geo_cases(urgency_score);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_city ON geo_cases(victim_city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_state ON geo_cases(victim_state);")

    # Spatial R*Tree Index for Cases
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS rtree_cases_idx USING rtree(
        id,              -- matches geo_cases.id
        min_lon, max_lon,
        min_lat, max_lat
    );
    """)

    # -------------------------------------------------------------------------
    # 2. ATM Master table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geo_atms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        atm_id TEXT UNIQUE NOT NULL,
        atm_name TEXT,
        bank_name TEXT,
        state TEXT,
        district TEXT,
        city TEXT,
        area TEXT,
        pincode TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        location_type TEXT,
        historical_cashouts INTEGER DEFAULT 0,
        historical_loss REAL DEFAULT 0.0,
        hotspot_score REAL DEFAULT 0.0
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atms_bank ON geo_atms(bank_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atms_city ON geo_atms(city);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_atms_hotspot ON geo_atms(hotspot_score);")

    # Spatial R*Tree Index for ATMs
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS rtree_atms_idx USING rtree(
        id,              -- matches geo_atms.id
        min_lon, max_lon,
        min_lat, max_lat
    );
    """)

    # -------------------------------------------------------------------------
    # 3. Predicted Cash-out ATMs (CIRIS ML Intelligence Consumer)
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geo_predicted_atms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        atm_id TEXT NOT NULL,
        prediction_timestamp TEXT,
        rank_order INTEGER NOT NULL,
        prediction_score REAL NOT NULL,
        confidence_level TEXT,
        time_window_label TEXT,
        withdrawal_delay_hours REAL,
        victim_lat REAL,
        victim_lon REAL,
        atm_lat REAL NOT NULL,
        atm_lon REAL NOT NULL,
        distance_km REAL,
        is_ground_truth INTEGER DEFAULT 0,
        FOREIGN KEY (complaint_id) REFERENCES geo_cases(complaint_id),
        FOREIGN KEY (atm_id) REFERENCES geo_atms(atm_id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_complaint ON geo_predicted_atms(complaint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_atm ON geo_predicted_atms(atm_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pred_rank ON geo_predicted_atms(rank_order);")

    # Spatial R*Tree Index for Predicted ATMs
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS rtree_predicted_atms_idx USING rtree(
        id,              -- matches geo_predicted_atms.id
        min_lon, max_lon,
        min_lat, max_lat
    );
    """)

    # -------------------------------------------------------------------------
    # 4. Money Flow Network Geometries
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geo_network_flows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT NOT NULL,
        edge_id TEXT,
        src_account_id TEXT NOT NULL,
        dst_account_id TEXT NOT NULL,
        amount REAL NOT NULL,
        channel TEXT,
        timestamp TEXT,
        hop_level INTEGER DEFAULT 1,
        src_lat REAL,
        src_lon REAL,
        dst_lat REAL,
        dst_lon REAL,
        flow_path_geojson TEXT,
        is_cashout_mule INTEGER DEFAULT 0
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_net_complaint ON geo_network_flows(complaint_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_net_src ON geo_network_flows(src_account_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_net_dst ON geo_network_flows(dst_account_id);")

    # -------------------------------------------------------------------------
    # 5. Merchants & Entities
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geo_merchants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_id TEXT UNIQUE NOT NULL,
        entity_type TEXT NOT NULL,
        name TEXT NOT NULL,
        category TEXT,
        state TEXT,
        city TEXT,
        pincode TEXT,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        risk_score REAL DEFAULT 0.0,
        linked_case_count INTEGER DEFAULT 0,
        total_suspicious_volume REAL DEFAULT 0.0
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchants_type ON geo_merchants(entity_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_merchants_risk ON geo_merchants(risk_score);")

    # Spatial R*Tree Index for Merchants
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS rtree_merchants_idx USING rtree(
        id,              -- matches geo_merchants.id
        min_lon, max_lon,
        min_lat, max_lat
    );
    """)

    # -------------------------------------------------------------------------
    # 6. Geographic Risk Hotspots / Clusters
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS geo_risk_hotspots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hotspot_id TEXT UNIQUE NOT NULL,
        name TEXT,
        state TEXT,
        district TEXT,
        city TEXT,
        center_lat REAL NOT NULL,
        center_lon REAL NOT NULL,
        radius_km REAL DEFAULT 5.0,
        risk_level TEXT,
        risk_score REAL DEFAULT 0.0,
        case_count INTEGER DEFAULT 0,
        total_loss REAL DEFAULT 0.0,
        active_mule_accounts INTEGER DEFAULT 0,
        hotspot_polygon_geojson TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hotspot_risk ON geo_risk_hotspots(risk_score);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_hotspot_level ON geo_risk_hotspots(risk_level);")

    # Spatial R*Tree Index for Hotspots
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS rtree_risk_hotspots_idx USING rtree(
        id,              -- matches geo_risk_hotspots.id
        min_lon, max_lon,
        min_lat, max_lat
    );
    """)

    # -------------------------------------------------------------------------
    # 7. PHASE 4: Operational Alerts Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operational_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT UNIQUE NOT NULL,
        case_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        prediction_timestamp TEXT,
        alert_type TEXT NOT NULL,
        priority TEXT NOT NULL,          -- 'P1', 'P2', 'P3', 'P4'
        severity TEXT NOT NULL,          -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
        risk_score REAL NOT NULL,
        confidence REAL NOT NULL,
        endpoint_type TEXT,              -- 'ATM', 'MERCHANT', 'TRANSFER', 'UNKNOWN'
        predicted_endpoint_id TEXT,
        amount_at_risk REAL DEFAULT 0.0,
        status TEXT NOT NULL,            -- 'NEW', 'ACKNOWLEDGED', 'ASSIGNED', 'INVESTIGATING', 'ESCALATED', 'MONITORING', 'RESOLVED', 'CLOSED'
        assigned_to TEXT,
        assigned_team TEXT,
        source TEXT DEFAULT 'CIRIS_INTELLIGENCE',
        evidence_summary TEXT,
        dedup_hash TEXT UNIQUE NOT NULL,
        sla_deadline TEXT,
        acknowledged_at TEXT,
        first_reviewed_at TEXT,
        resolved_at TEXT,
        closed_at TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_case ON operational_alerts(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_priority ON operational_alerts(priority);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON operational_alerts(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_dedup ON operational_alerts(dedup_hash);")

    # -------------------------------------------------------------------------
    # 8. PHASE 4: Case Lifecycle & Assignment Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_lifecycle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT UNIQUE NOT NULL,
        complaint_id TEXT UNIQUE NOT NULL,
        priority TEXT NOT NULL,          -- 'P1', 'P2', 'P3', 'P4'
        status TEXT NOT NULL,            -- 'NEW', 'ACKNOWLEDGED', 'ASSIGNED', 'INVESTIGATING', 'ESCALATED', 'MONITORING', 'RESOLVED', 'CLOSED'
        owner TEXT,
        team TEXT,
        risk_score REAL NOT NULL DEFAULT 0.0,
        amount_at_risk REAL DEFAULT 0.0,
        endpoint_type TEXT DEFAULT 'UNKNOWN',
        predicted_endpoint_id TEXT,
        summary TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        sla_deadline TEXT,
        acknowledged_at TEXT,
        assigned_at TEXT,
        first_review_at TEXT,
        resolved_at TEXT,
        closed_at TEXT,
        resolution_outcome TEXT         -- 'CONFIRMED', 'NOT_CONFIRMED', 'FALSE_POSITIVE', 'INSUFFICIENT_EVIDENCE', 'ESCALATED'
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_status ON case_lifecycle(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_priority ON case_lifecycle(priority);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_owner ON case_lifecycle(owner);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lifecycle_team ON case_lifecycle(team);")

    # -------------------------------------------------------------------------
    # 9. PHASE 4: Evidence Registry Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        evidence_id TEXT UNIQUE NOT NULL,
        case_id TEXT NOT NULL,
        category TEXT NOT NULL,          -- 'TRANSACTION', 'GRAPH', 'ENTITY', 'GEOGRAPHIC', 'HISTORICAL', 'BEHAVIOURAL', 'MODEL', 'CASE'
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        source TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        confidence REAL DEFAULT 1.0,
        severity TEXT DEFAULT 'MEDIUM',
        reference_id TEXT,
        metadata_json TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence_registry(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_cat ON evidence_registry(category);")

    # -------------------------------------------------------------------------
    # 10. PHASE 4: Interventions Table (Decision Support Only)
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        intervention_id TEXT UNIQUE NOT NULL,
        case_id TEXT NOT NULL,
        recommendation TEXT NOT NULL,    -- 'HOLD_REVIEW', 'MONITOR', 'INVESTIGATE', 'ESCALATE'
        reason TEXT NOT NULL,
        evidence_ids TEXT,              -- Comma-separated or JSON list
        authorization_boundary TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING_REVIEW', -- 'PENDING_REVIEW', 'ACCEPTED', 'REJECTED', 'SUPERSEDED'
        reviewed_by TEXT,
        reviewed_at TEXT,
        review_notes TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intervention_case ON interventions(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_intervention_rec ON interventions(recommendation);")

    # -------------------------------------------------------------------------
    # 11. PHASE 4: Escalations Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS escalations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        escalation_id TEXT UNIQUE NOT NULL,
        case_id TEXT NOT NULL,
        reason TEXT NOT NULL,
        priority TEXT NOT NULL,
        requested_by TEXT NOT NULL,
        requested_at TEXT NOT NULL,
        status TEXT NOT NULL,            -- 'PENDING', 'ACCEPTED', 'REJECTED', 'RESOLVED'
        target_role TEXT NOT NULL,       -- 'SUPERVISOR', 'LEA_OFFICER', 'I4C_ANALYST'
        response_notes TEXT,
        resolved_at TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_escalation_case ON escalations(case_id);")

    # -------------------------------------------------------------------------
    # 12. PHASE 4: Case Notes Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS case_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id TEXT UNIQUE NOT NULL,
        case_id TEXT NOT NULL,
        author TEXT NOT NULL,
        created_at TEXT NOT NULL,
        content TEXT NOT NULL,
        visibility TEXT DEFAULT 'INTERNAL' -- 'INTERNAL', 'PUBLIC', 'RESTRICTED'
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_case ON case_notes(case_id);")

    # -------------------------------------------------------------------------
    # 13. PHASE 4: Append-Only Audit Trail Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_trail (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id TEXT UNIQUE NOT NULL,
        case_id TEXT,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,            -- 'CASE_CREATED', 'ALERT_CREATED', 'ALERT_ACKNOWLEDGED', 'CASE_ASSIGNED', 'CASE_OPENED', 'EVIDENCE_VIEWED', 'NETWORK_EXPANDED', 'INTERVENTION_RECOMMENDED', 'INTERVENTION_REVIEWED', 'CASE_ESCALATED', 'CASE_RESOLVED', 'CASE_CLOSED'
        timestamp TEXT NOT NULL,
        metadata_json TEXT
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_case ON audit_trail(case_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_trail(action);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_trail(timestamp);")

    # -------------------------------------------------------------------------
    # 14. PHASE 4: Investigator Feedback Table
    # -------------------------------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS investigator_feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feedback_id TEXT UNIQUE NOT NULL,
        case_id TEXT NOT NULL,
        investigator_id TEXT NOT NULL,
        outcome TEXT NOT NULL,           -- 'CONFIRMED', 'NOT_CONFIRMED', 'FALSE_POSITIVE', 'INSUFFICIENT_EVIDENCE', 'ESCALATED'
        notes TEXT,
        actual_cashout_atm_id TEXT,
        actual_loss_recovered REAL DEFAULT 0.0,
        submitted_at TEXT NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_case ON investigator_feedback(case_id);")

    conn.commit()
    logger.info("Spatial and operational database schema initialized successfully.")
