"""
Mocked Last-Mile Dispatch & Emergency Alert Notification Service.
Simulates real-time WhatsApp, SMS, and Bank NOC Webhook broadcasts with
geospatial Google Maps coordinates links and confidence tiers for SIH live evaluation.
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("ciris.notification.service")


class DispatchNotification(BaseModel):
    dispatch_id: str
    case_id: str
    atm_name: str
    bank_name: str
    city: str
    latitude: float
    longitude: float
    google_maps_url: str
    confidence_tier: str  # AUTO_FREEZE_RECOMMENDED, LEA_ALERT, MONITOR_ONLY
    raw_probability: float
    recommended_action: str
    recipient_group: str
    channel: str  # WHATSAPP, SMS, BANK_NOC_API
    message_text: str
    timestamp: str
    status: str = "DELIVERED"


class NotificationService:
    """Manages emergency dispatch formatting, logging, and broadcast feeds."""

    def __init__(self):
        self._dispatch_log: List[Dict[str, Any]] = []
        self._seed_initial_dispatches()

    def _seed_initial_dispatches(self):
        """Pre-seeds recent sample dispatches for immediate demo visibility."""
        sample = self.create_and_send_dispatch(
            case_id="CASE_000001",
            atm_name="ICICI Bank Railway Station ATM 308",
            bank_name="ICICI Bank",
            city="Hyderabad",
            latitude=17.469835,
            longitude=78.479816,
            raw_probability=0.950,
            recommended_action="Deploy Beat Interception at Terminal & Execute CBS Account Lock",
            recipient_group="Secunderabad Railway Beat Units & ICICI NOC"
        )

    def create_and_send_dispatch(
        self,
        case_id: str,
        atm_name: str,
        bank_name: str,
        city: str,
        latitude: float,
        longitude: float,
        raw_probability: float,
        recommended_action: Optional[str] = None,
        recipient_group: Optional[str] = None
    ) -> Dict[str, Any]:
        """Formats and logs a simulated last-mile emergency notification."""
        now = datetime.now(timezone.utc).isoformat()
        maps_link = f"https://maps.google.com/?q={latitude:.6f},{longitude:.6f}"

        tier = "AUTO_FREEZE_RECOMMENDED" if raw_probability >= 0.90 else ("LEA_ALERT" if raw_probability >= 0.70 else "MONITOR_ONLY")
        tier_label = "⚡ [CRITICAL P1 AUTO-FREEZE]" if tier == "AUTO_FREEZE_RECOMMENDED" else ("🚨 [HIGH P2 LEA ALERT]" if tier == "LEA_ALERT" else "ℹ️ [P3 MONITOR ONLY]")

        recipients = recipient_group or f"{city} Cybercrime Police Beat & {bank_name} Risk Ops"
        action = recommended_action or ("Immediate ATM Terminal Beat Intercept" if tier == "LEA_ALERT" else "Mule Account CBS Lock Confirmation")

        msg_body = (
            f"{tier_label} CIRIS Proactive Intercept:\n"
            f"Case: {case_id} | Probability: {raw_probability*100:.1f}%\n"
            f"Target Terminal: {atm_name} ({bank_name}, {city})\n"
            f"Action: {action}\n"
            f"Live GPS Navigation: {maps_link}"
        )

        dispatch_record = {
            "dispatch_id": f"DISP_{datetime.now().strftime('%Y%m%d%H%M%S')}_{case_id[-4:]}",
            "case_id": case_id,
            "atm_name": atm_name,
            "bank_name": bank_name,
            "city": city,
            "latitude": round(latitude, 6),
            "longitude": round(longitude, 6),
            "google_maps_url": maps_link,
            "confidence_tier": tier,
            "raw_probability": round(raw_probability, 4),
            "recommended_action": action,
            "recipient_group": recipients,
            "channels": ["WHATSAPP_LEA_BROADCAST", "SMS_FLASH_ALERT", "BANK_NOC_WEBHOOK"],
            "message_text": msg_body,
            "timestamp": now,
            "status": "DELIVERED"
        }

        self._dispatch_log.insert(0, dispatch_record)
        # Keep recent 50 logs
        self._dispatch_log = self._dispatch_log[:50]

        logger.info("Mocked Last-Mile Dispatch broadcasted for case %s to %s", case_id, recipients)
        return dispatch_record

    def get_recent_dispatches(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._dispatch_log[:limit]


_global_notification_service = NotificationService()

def get_notification_service() -> NotificationService:
    return _global_notification_service
