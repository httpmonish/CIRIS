"""
CIRIS Phase 4 — Unified Investigation Workspace & Deep-Dive Service.
Provides consolidated investigation payload (/cases/{id}/investigation)
and specialized endpoints for Money Flow, Entities, Networks, Endpoints, and Cross-Case Correlations.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.db.database import get_db_connection
from src.db.operational_models import (
    AlertType,
    CaseInvestigationWorkspace,
    CaseStatus,
    EntityProfile,
    EvidenceCategory,
    EvidenceItem,
    MoneyFlowHop,
    NetworkInvestigationResponse,
    PriorityLevel,
    SeverityLevel,
    mask_account_id,
    mask_phone_number,
    mask_upi_id,
)
from src.services.alert_service import AlertService
from src.services.audit_service import AuditService
from src.services.case_service import CaseService
from src.services.evidence_service import EvidenceService
from src.services.intervention_service import InterventionService

logger = logging.getLogger("ciris.services.investigation")


class InvestigationService:
    """Consolidated Case Investigation & Intelligence Engine."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.case_service = CaseService(db_path)
        self.evidence_service = EvidenceService(db_path)
        self.intervention_service = InterventionService(db_path)
        self.alert_service = AlertService(db_path)
        self.audit_service = AuditService(db_path)

    # =========================================================================
    # 1. Primary Unified Investigation Workspace Payload
    # =========================================================================
    def get_case_investigation(self, case_id: str) -> CaseInvestigationWorkspace:
        """
        Consolidates the complete investigation workspace payload for an investigator:
        case metadata, risk, timeline, money flow, predictions, evidence chain,
        intervention recommendations, cross-case correlations, notes, and audit history.
        """
        case = self.case_service.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        cid = case.complaint_id

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # 1. Fetch Complaint / Case Base Intelligence
            cursor.execute("""
            SELECT complaint_id, complaint_timestamp, incident_timestamp, fraud_type,
                   channel, reported_loss_amount, victim_state, victim_district,
                   victim_city, victim_area, victim_pincode, victim_lat, victim_lon,
                   victim_bank, urgency_score, fraud_category
            FROM geo_cases WHERE complaint_id = ?;
            """, (cid,))
            gcase = cursor.fetchone()

            loss_amt = float(gcase["reported_loss_amount"] or case.amount_at_risk) if gcase else case.amount_at_risk
            urg_score = float(gcase["urgency_score"] or case.risk_score) if gcase else case.risk_score

            victim_loc = {
                "state": gcase["victim_state"] if gcase else "Unknown",
                "city": gcase["victim_city"] if gcase else "Unknown",
                "district": gcase["victim_district"] if gcase else None,
                "area": gcase["victim_area"] if gcase else None,
                "pincode": gcase["victim_pincode"] if gcase else None,
                "coordinates": [float(gcase["victim_lon"]), float(gcase["victim_lat"])] if gcase and gcase["victim_lat"] else None,
                "bank": gcase["victim_bank"] if gcase else None
            }

            # 2. Predicted Endpoints (ATMs / POS)
            cursor.execute("""
            SELECT p.atm_id, p.rank_order, p.prediction_score, p.confidence_level,
                   p.time_window_label, p.withdrawal_delay_hours, p.atm_lat, p.atm_lon,
                   p.distance_km, p.is_ground_truth,
                   a.atm_name, a.bank_name, a.city, a.district, a.state, a.location_type,
                   a.historical_cashouts, a.hotspot_score
            FROM geo_predicted_atms p
            JOIN geo_atms a ON p.atm_id = a.atm_id
            WHERE p.complaint_id = ?
            ORDER BY p.rank_order ASC
            LIMIT 5;
            """, (cid,))
            pred_rows = cursor.fetchall()

            predicted_endpoints = [
                {
                    "endpoint_id": p["atm_id"],
                    "endpoint_type": "ATM",
                    "name": p["atm_name"],
                    "bank": p["bank_name"],
                    "rank": int(p["rank_order"]),
                    "score": float(p["prediction_score"]),
                    "confidence": p["confidence_level"],
                    "time_window": p["time_window_label"],
                    "estimated_delay_hours": float(p["withdrawal_delay_hours"] or 0.0),
                    "distance_km": round(float(p["distance_km"] or 0.0), 2),
                    "city": p["city"],
                    "state": p["state"],
                    "coordinates": [float(p["atm_lon"]), float(p["atm_lat"])],
                    "historical_cashouts": int(p["historical_cashouts"] or 0),
                    "hotspot_score": float(p["hotspot_score"] or 0.0),
                    "priority": "CRITICAL" if p["rank_order"] == 1 else "HIGH"
                }
                for p in pred_rows
            ]

            # 3. Money Flow Network & Hops
            cursor.execute("""
            SELECT edge_id, src_account_id, dst_account_id, amount, channel,
                   timestamp, hop_level, src_lat, src_lon, dst_lat, dst_lon, is_cashout_mule
            FROM geo_network_flows
            WHERE complaint_id = ?
            ORDER BY hop_level ASC;
            """, (cid,))
            flow_rows = cursor.fetchall()

            money_flow_hops = [
                MoneyFlowHop(
                    edge_id=f["edge_id"] or f"TX_{idx}",
                    from_account=mask_account_id(f["src_account_id"]),
                    to_account=mask_account_id(f["dst_account_id"]),
                    amount=float(f["amount"]),
                    channel=f["channel"] or "UPI",
                    timestamp=f["timestamp"] or "",
                    hop_level=int(f["hop_level"]),
                    is_cashout_endpoint=bool(f["is_cashout_mule"]),
                    source_coordinates=[float(f["src_lon"]), float(f["src_lat"])] if f["src_lon"] else None,
                    dest_coordinates=[float(f["dst_lon"]), float(f["dst_lat"])] if f["dst_lon"] else None
                ).model_dump()
                for idx, f in enumerate(flow_rows, start=1)
            ]

            total_moved = sum(float(f["amount"]) for f in flow_rows)
            observed_remaining = max(0.0, loss_amt - (float(flow_rows[-1]["amount"]) if flow_rows else 0.0))

            money_flow_summary = {
                "total_hops": len(flow_rows),
                "total_volume_moved": round(total_moved, 2),
                "observed_remaining_amount": round(observed_remaining, 2),
                "hops": money_flow_hops
            }

            # 4. Related Entities
            entity_set = set()
            for f in flow_rows:
                entity_set.add(f["src_account_id"])
                entity_set.add(f["dst_account_id"])

            related_entities = [
                EntityProfile(
                    entity_id=acc,
                    entity_type="MULE_ACCOUNT" if idx > 0 else "VICTIM_ACCOUNT",
                    masked_name=mask_account_id(acc),
                    category="Digital Banking Node",
                    risk_score=round(min(1.0, 0.45 + (idx * 0.15)), 2),
                    linked_case_count=1 + (idx % 3),
                    linked_account_count=2 + idx,
                    total_volume=loss_amt,
                    city=victim_loc["city"],
                    state=victim_loc["state"]
                )
                for idx, acc in enumerate(list(entity_set)[:5])
            ]

        # 5. Timeline Assembly
        timeline = []
        if gcase and gcase["incident_timestamp"]:
            timeline.append({
                "timestamp": gcase["incident_timestamp"],
                "event_type": "INCIDENT_OCCURRED",
                "title": "Fraud Incident Compromise",
                "description": f"Victim compromised via {gcase['fraud_type']} ({gcase['channel']})."
            })
        for f in flow_rows:
            timeline.append({
                "timestamp": f["timestamp"],
                "event_type": "FUND_TRANSFER_HOP",
                "title": f"Hop {f['hop_level']} Transfer",
                "description": f"Transferred ₹{float(f['amount']):,.2f} to {mask_account_id(f['dst_account_id'])}."
            })
        if gcase and gcase["complaint_timestamp"]:
            timeline.append({
                "timestamp": gcase["complaint_timestamp"],
                "event_type": "COMPLAINT_FILED",
                "title": "Victim Complaint Lodged",
                "description": f"Formal report registered with urgency score {urg_score:.2f}."
            })
        for p in predicted_endpoints[:1]:
            timeline.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "PREDICTED_INTERCEPTION",
                "title": "Predicted ATM Interception Window",
                "description": f"Target ATM: {p['name']} ({p['time_window']})."
            })
        timeline.sort(key=lambda t: t["timestamp"] or "")

        # 6. Evidence Chain
        evidence_chain = self.evidence_service.get_case_evidence(cid)

        # 7. Intervention Policy Recommendation
        top_pred = predicted_endpoints[0] if predicted_endpoints else None
        intervention = self.intervention_service.generate_recommendation(
            case_id=cid,
            risk_score=urg_score,
            confidence=top_pred["score"] if top_pred else 0.85,
            amount_at_risk=loss_amt,
            time_window_label=top_pred["time_window"] if top_pred else "0-3h",
            hop_count=len(flow_rows),
            priority=case.priority,
            is_fragmented=(len(flow_rows) >= 2)
        )

        # 8. Active Alerts
        alerts = self.alert_service.get_alerts(case_id=cid)
        if not alerts:
            # Generate initial alert
            new_alt = self.alert_service.create_alert(
                case_id=cid,
                alert_type=from_fraud_type_to_alert(gcase["fraud_type"] if gcase else "ATM_CASHOUT_RISK"),
                risk_score=urg_score,
                confidence=top_pred["score"] if top_pred else 0.85,
                amount_at_risk=loss_amt,
                endpoint_type="ATM",
                predicted_endpoint_id=top_pred["endpoint_id"] if top_pred else None,
                time_window_label=top_pred["time_window"] if top_pred else "0-3h",
                hop_count=len(flow_rows),
                is_fragmented=(len(flow_rows) >= 2),
                urgency_score=urg_score,
                prediction_timestamp=gcase["complaint_timestamp"] if gcase else None
            )
            if new_alt:
                alerts = [new_alt]

        # 9. Notes & Audit Trail
        notes = self.case_service.get_notes(cid)
        audit_events = self.audit_service.get_events_for_case(cid)

        # 10. Cross-Case Correlations
        correlations = self.get_case_correlations(cid)

        # 11. Structured Reasons Why
        reasons_why = [
            f"High-velocity money dispersion observed across {len(flow_rows)} mule hops.",
            f"ML V4 predicted terminal ATM cashout at {top_pred['name'] if top_pred else 'designated ATM'} with confidence {top_pred['confidence'] if top_pred else 'HIGH'}.",
            f"Estimated victim loss at risk: ₹{loss_amt:,.2f}.",
            f"Urgency classification index: {urg_score:.2f}."
        ]

        # 12. Executive Summary
        exec_summary = (
            f"Case {cid} ({gcase['fraud_type'] if gcase else 'Cyber Fraud'}): "
            f"Reported loss of ₹{loss_amt:,.2f} originating in {victim_loc['city']}. "
            f"Funds fragmented across {len(flow_rows)} accounts. "
            f"Target cash-out interception point identified at {top_pred['name'] if top_pred else 'local ATM'} "
            f"within {top_pred['time_window'] if top_pred else 'imminent window'}. "
            f"Intervention recommendation: {intervention.recommendation.value}."
        )

        # 13. SLA Metrics
        created_dt = datetime.fromisoformat(case.created_at.replace("Z", "+00:00"))
        age_hrs = round((datetime.now(timezone.utc) - created_dt).total_seconds() / 3600.0, 2)
        sla_status = "BREACHED" if (case.sla_deadline and datetime.now(timezone.utc).isoformat() > case.sla_deadline and case.status != CaseStatus.CLOSED) else "WITHIN_SLA"

        sla_metrics = {
            "age_hours": age_hrs,
            "created_at": case.created_at,
            "sla_deadline": case.sla_deadline,
            "sla_status": sla_status,
            "acknowledged_at": case.acknowledged_at,
            "first_review_at": case.first_review_at,
            "resolved_at": case.resolved_at
        }

        return CaseInvestigationWorkspace(
            case_id=case.case_id,
            complaint_id=cid,
            status=case.status,
            priority=case.priority,
            risk_score=urg_score,
            urgency_score=urg_score,
            confidence=top_pred["score"] if top_pred else 0.85,
            amount_at_risk=loss_amt,
            reported_loss_amount=loss_amt,
            fraud_type=gcase["fraud_type"] if gcase else "Cybercrime Incident",
            incident_timestamp=gcase["incident_timestamp"] if gcase else None,
            complaint_timestamp=gcase["complaint_timestamp"] if gcase else None,
            victim_location=victim_loc,
            assigned_owner=case.owner,
            assigned_team=case.team,
            executive_summary=exec_summary,
            reasons_why=reasons_why,
            timeline=timeline,
            evidence_chain=evidence_chain,
            predicted_endpoints=predicted_endpoints,
            money_flow_network=money_flow_summary,
            related_entities=related_entities,
            related_cases=correlations,
            intervention_recommendation=intervention,
            active_alerts=alerts,
            notes=notes,
            audit_events=audit_events,
            sla_metrics=sla_metrics
        )

    # =========================================================================
    # 2. Money Flow Investigation Deep-Dive
    # =========================================================================
    def get_money_flow_investigation(
        self,
        case_id: str,
        hop_limit: int = 5,
        risk_only: bool = False
    ) -> Dict[str, Any]:
        """Deep-dive money flow path extraction."""
        case = self.case_service.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        cid = case.complaint_id
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT edge_id, src_account_id, dst_account_id, amount, channel,
                   timestamp, hop_level, src_lat, src_lon, dst_lat, dst_lon, is_cashout_mule
            FROM geo_network_flows
            WHERE complaint_id = ? AND hop_level <= ?
            ORDER BY hop_level ASC;
            """, (cid, hop_limit))
            rows = cursor.fetchall()

            hops = []
            for r in rows:
                if risk_only and not r["is_cashout_mule"] and r["hop_level"] < 2:
                    continue
                hops.append({
                    "edge_id": r["edge_id"],
                    "from_account": mask_account_id(r["src_account_id"]),
                    "to_account": mask_account_id(r["dst_account_id"]),
                    "amount": float(r["amount"]),
                    "channel": r["channel"],
                    "timestamp": r["timestamp"],
                    "hop_level": int(r["hop_level"]),
                    "is_cashout": bool(r["is_cashout_mule"]),
                    "source_coordinates": [float(r["src_lon"]), float(r["src_lat"])] if r["src_lon"] else None,
                    "destination_coordinates": [float(r["dst_lon"]), float(r["dst_lat"])] if r["dst_lon"] else None
                })

            return {
                "case_id": case.case_id,
                "complaint_id": cid,
                "hop_limit": hop_limit,
                "total_hops_found": len(hops),
                "hops": hops,
                "is_fragmentation_detected": len(hops) >= 2,
                "terminal_cashout_node": hops[-1]["to_account"] if hops else None
            }

    # =========================================================================
    # 3. Entity Investigation Deep-Dive
    # =========================================================================
    def get_entity_investigation(self, entity_id: str) -> Dict[str, Any]:
        """Deep-dive investigation on an account or merchant entity."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Check if it is in geo_merchants
            cursor.execute("SELECT * FROM geo_merchants WHERE entity_id = ?;", (entity_id,))
            merchant = cursor.fetchone()
            if merchant:
                return {
                    "entity_id": merchant["entity_id"],
                    "entity_type": "SUSPICIOUS_MERCHANT",
                    "name": merchant["name"],
                    "category": merchant["category"],
                    "city": merchant["city"],
                    "state": merchant["state"],
                    "risk_score": float(merchant["risk_score"]),
                    "linked_case_count": int(merchant["linked_case_count"]),
                    "total_suspicious_volume": float(merchant["total_suspicious_volume"]),
                    "coordinates": [float(merchant["longitude"]), float(merchant["latitude"])]
                }

            # Account investigation across flows
            cursor.execute("""
            SELECT complaint_id, amount, timestamp, channel, hop_level, is_cashout_mule
            FROM geo_network_flows
            WHERE src_account_id = ? OR dst_account_id = ?
            ORDER BY timestamp DESC LIMIT 20;
            """, (entity_id, entity_id))
            flows = cursor.fetchall()

            linked_cases = list(set(f["complaint_id"] for f in flows))
            total_vol = sum(float(f["amount"]) for f in flows)

            return {
                "entity_id": entity_id,
                "masked_id": mask_account_id(entity_id),
                "entity_type": "MULE_ACCOUNT_NODE" if flows else "UNKNOWN_ENTITY",
                "risk_score": 0.85 if any(f["is_cashout_mule"] for f in flows) else (0.65 if flows else 0.20),
                "linked_case_count": len(linked_cases),
                "linked_cases": linked_cases,
                "total_observed_volume": round(total_vol, 2),
                "transaction_count": len(flows),
                "role_in_network": "TERMINAL_CASHOUT" if any(f["is_cashout_mule"] for f in flows) else "INTERMEDIARY_DISPERSION"
            }

    # =========================================================================
    # 4. Network Investigation Deep-Dive (Bounded 1-3 hops)
    # =========================================================================
    def get_network_investigation(self, cluster_id_or_case_id: str, hop_depth: int = 2) -> NetworkInvestigationResponse:
        """Bounded network graph extraction."""
        hop_depth = min(3, max(1, hop_depth))
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT edge_id, src_account_id, dst_account_id, amount, channel, timestamp, hop_level, is_cashout_mule
            FROM geo_network_flows
            WHERE (complaint_id = ? OR src_account_id = ? OR dst_account_id = ?) AND hop_level <= ?
            LIMIT 50;
            """, (cluster_id_or_case_id, cluster_id_or_case_id, cluster_id_or_case_id, hop_depth))
            rows = cursor.fetchall()

            nodes_dict = {}
            edges = []
            total_vol = 0.0

            for r in rows:
                amt = float(r["amount"])
                total_vol += amt
                src = r["src_account_id"]
                dst = r["dst_account_id"]

                nodes_dict[src] = {
                    "id": src,
                    "label": mask_account_id(src),
                    "role": "SOURCE_MULE" if r["hop_level"] > 1 else "VICTIM",
                    "degree": nodes_dict.get(src, {}).get("degree", 0) + 1
                }
                nodes_dict[dst] = {
                    "id": dst,
                    "label": mask_account_id(dst),
                    "role": "CASHOUT_ENDPOINT" if r["is_cashout_mule"] else "INTERMEDIARY",
                    "degree": nodes_dict.get(dst, {}).get("degree", 0) + 1
                }

                edges.append({
                    "id": r["edge_id"] or f"E_{len(edges)+1}",
                    "source": src,
                    "target": dst,
                    "amount": amt,
                    "channel": r["channel"],
                    "hop": int(r["hop_level"])
                })

            evidence = [
                EvidenceItem(
                    evidence_id=f"EVD_NET_{cluster_id_or_case_id}",
                    case_id=cluster_id_or_case_id,
                    category=EvidenceCategory.GRAPH,
                    title="Sub-Network Topology Verification",
                    description=f"Extracted bounded {hop_depth}-hop subgraph containing {len(nodes_dict)} accounts and ₹{total_vol:,.2f} total flow volume.",
                    source="GRAPH_INTELLIGENCE",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    confidence=0.92,
                    severity=SeverityLevel.HIGH,
                    reference_id=cluster_id_or_case_id
                )
            ]

            return NetworkInvestigationResponse(
                cluster_id=cluster_id_or_case_id,
                hop_depth=hop_depth,
                node_count=len(nodes_dict),
                edge_count=len(edges),
                total_network_volume=round(total_vol, 2),
                active_mule_candidates=len([n for n in nodes_dict.values() if n["role"] != "VICTIM"]),
                nodes=list(nodes_dict.values()),
                edges=edges,
                evidence=evidence
            )

    # =========================================================================
    # 5. Endpoint Investigation Deep-Dive
    # =========================================================================
    def get_endpoint_investigation(self, endpoint_id: str) -> Dict[str, Any]:
        """Investigate ATM or Merchant endpoint."""
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Check ATM
            cursor.execute("SELECT * FROM geo_atms WHERE atm_id = ?;", (endpoint_id,))
            atm = cursor.fetchone()
            if atm:
                # Find recent predictions targeting this ATM
                cursor.execute("""
                SELECT complaint_id, rank_order, prediction_score, confidence_level, time_window_label
                FROM geo_predicted_atms WHERE atm_id = ? ORDER BY rank_order ASC LIMIT 5;
                """, (endpoint_id,))
                preds = cursor.fetchall()

                return {
                    "endpoint_id": atm["atm_id"],
                    "endpoint_type": "ATM",
                    "name": atm["atm_name"],
                    "bank": atm["bank_name"],
                    "city": atm["city"],
                    "district": atm["district"],
                    "state": atm["state"],
                    "pincode": atm["pincode"],
                    "location_type": atm["location_type"],
                    "coordinates": [float(atm["longitude"]), float(atm["latitude"])],
                    "historical_cashouts": int(atm["historical_cashouts"] or 0),
                    "hotspot_score": float(atm["hotspot_score"] or 0.0),
                    "active_predictions_count": len(preds),
                    "recent_targeting_cases": [p["complaint_id"] for p in preds],
                    "risk_assessment": "CRITICAL" if atm["hotspot_score"] >= 0.7 else ("HIGH" if atm["hotspot_score"] >= 0.4 else "STANDARD")
                }

            # Check Merchant
            cursor.execute("SELECT * FROM geo_merchants WHERE entity_id = ?;", (endpoint_id,))
            m = cursor.fetchone()
            if m:
                return {
                    "endpoint_id": m["entity_id"],
                    "endpoint_type": "MERCHANT",
                    "name": m["name"],
                    "category": m["category"],
                    "city": m["city"],
                    "state": m["state"],
                    "risk_score": float(m["risk_score"]),
                    "linked_cases_count": int(m["linked_case_count"]),
                    "total_volume": float(m["total_suspicious_volume"]),
                    "coordinates": [float(m["longitude"]), float(m["latitude"])]
                }

            return {
                "endpoint_id": endpoint_id,
                "endpoint_type": "UNKNOWN_ENDPOINT",
                "message": "Endpoint not catalogued in ATM Master or Merchant registry."
            }

    # =========================================================================
    # 6. Cross-Case Correlation Discovery
    # =========================================================================
    def get_case_correlations(self, case_id: str) -> List[Dict[str, Any]]:
        """Identify related cases sharing entities, accounts, networks, or endpoints."""
        case = self.case_service.get_case(case_id)
        if not case:
            return []

        cid = case.complaint_id
        correlations = []

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # 1. Check shared predicted cashout ATM
            cursor.execute("SELECT atm_id FROM geo_predicted_atms WHERE complaint_id = ? AND rank_order = 1;", (cid,))
            p_atm = cursor.fetchone()
            if p_atm:
                atm_id = p_atm["atm_id"]
                cursor.execute("""
                SELECT DISTINCT complaint_id FROM geo_predicted_atms
                WHERE atm_id = ? AND complaint_id != ? LIMIT 3;
                """, (atm_id, cid))
                for r in cursor.fetchall():
                    correlations.append({
                        "related_case_id": r["complaint_id"],
                        "correlation_type": "SHARED_ENDPOINT",
                        "reason": f"Both cases target predicted cash-out ATM {atm_id}.",
                        "confidence": 0.88
                    })

            # 2. Check shared victim city / cluster
            cursor.execute("SELECT victim_city, fraud_type FROM geo_cases WHERE complaint_id = ?;", (cid,))
            c_info = cursor.fetchone()
            if c_info and c_info["victim_city"]:
                v_city = c_info["victim_city"]
                f_type = c_info["fraud_type"]
                cursor.execute("""
                SELECT complaint_id FROM geo_cases
                WHERE victim_city = ? AND fraud_type = ? AND complaint_id != ? LIMIT 3;
                """, (v_city, f_type, cid))
                for r in cursor.fetchall():
                    correlations.append({
                        "related_case_id": r["complaint_id"],
                        "correlation_type": "SHARED_TRANSACTION_PATTERN",
                        "reason": f"Matching fraud signature ({f_type}) in {v_city}.",
                        "confidence": 0.72
                    })

        return correlations

    # =========================================================================
    # 7. Search Cases
    # =========================================================================
    def search_cases(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search cases by Case ID, Complaint ID, Account, or ATM."""
        q = f"%{query.strip()}%"
        results = []

        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()

            # Search in geo_cases
            cursor.execute("""
            SELECT complaint_id, fraud_type, reported_loss_amount, victim_city, urgency_score
            FROM geo_cases
            WHERE complaint_id LIKE ? OR victim_city LIKE ? OR fraud_type LIKE ?
            LIMIT ?;
            """, (q, q, q, limit))
            for r in cursor.fetchall():
                results.append({
                    "case_id": f"CASE_{r['complaint_id'].replace('CASE_', '')}",
                    "complaint_id": r["complaint_id"],
                    "fraud_type": r["fraud_type"],
                    "amount": float(r["reported_loss_amount"]),
                    "city": r["victim_city"],
                    "urgency": float(r["urgency_score"]),
                    "match_type": "CASE_RECORD"
                })

            # Search in network flows
            if len(results) < limit:
                cursor.execute("""
                SELECT DISTINCT complaint_id, src_account_id, dst_account_id
                FROM geo_network_flows
                WHERE src_account_id LIKE ? OR dst_account_id LIKE ? OR edge_id LIKE ?
                LIMIT ?;
                """, (q, q, q, limit - len(results)))
                for r in cursor.fetchall():
                    if not any(res["complaint_id"] == r["complaint_id"] for res in results):
                        results.append({
                            "case_id": f"CASE_{r['complaint_id'].replace('CASE_', '')}",
                            "complaint_id": r["complaint_id"],
                            "matched_account": mask_account_id(r["src_account_id"]),
                            "match_type": "NETWORK_FLOW"
                        })

        return results


def from_fraud_type_to_alert(fraud_type: str) -> AlertType:
    ft = str(fraud_type).lower()
    if "atm" in ft:
        return AlertType.ATM_CASHOUT_RISK
    elif "mule" in ft:
        return AlertType.MULE_NETWORK
    elif "fragment" in ft:
        return AlertType.FRAGMENTATION
    elif "cross" in ft:
        return AlertType.CROSS_CASE_NETWORK
    elif "upi" in ft or "otp" in ft:
        return AlertType.HIGH_RISK_MONEY_FLOW
    return AlertType.COMBINED_CASE_RISK
