"""Lead scoring and Hot/Warm/Cold classification."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from modules.utils import emoji_for_priority, get_logger, load_config, safe

log = get_logger("casa_ludic.qualification")

URGENCY_KEYWORDS = ("urgente", "urgência", "urgencia", "agora", "hoje", "imediato", "rápido", "rapido")


@safe(default=(0, "cold"), log_name="casa_ludic.qualification")
def score(lead_data: dict[str, Any]) -> tuple[int, str]:
    """Score 0-100, return (score, priority). Padrao 1: type hints + safe degradation."""
    cfg = load_config().get("qualification", {})
    weights = cfg.get("weights", {
        "has_phone": 30, "has_email": 15, "has_service": 20,
        "urgency": 25, "business_hours": 10,
    })
    thresholds = cfg.get("thresholds", {"hot": 70, "warm": 40})

    points = 0
    if lead_data.get("phone"):
        points += int(weights.get("has_phone", 30))
    if lead_data.get("email"):
        points += int(weights.get("has_email", 15))

    service = (lead_data.get("service") or "").lower()
    if service and service != "indefinido":
        points += int(weights.get("has_service", 20))

    raw_text = (lead_data.get("raw_text") or "").lower()
    if any(k in raw_text for k in URGENCY_KEYWORDS):
        points += int(weights.get("urgency", 25))

    hour = datetime.now().hour
    if 9 <= hour <= 18:
        points += int(weights.get("business_hours", 10))

    points = min(100, points)

    if points >= int(thresholds.get("hot", 70)):
        priority = "hot"
    elif points >= int(thresholds.get("warm", 40)):
        priority = "warm"
    else:
        priority = "cold"

    log.info("Lead pontuou %d -> %s %s", points, priority, emoji_for_priority(priority))
    return points, priority


@safe(default=False, log_name="casa_ludic.qualification")
def requalify_pending(db: Any) -> bool:
    """Re-score leads still in 'prospect' stage. Used by scheduler job 3."""
    leads = db.list_leads(stage="prospect")
    updated = 0
    for lead in leads:
        s, p = score(lead)
        if s != lead.get("score") or p != lead.get("priority"):
            db.update_score(lead["id"], s, p)
            updated += 1
    log.info("Requalificacao concluida: %d leads atualizados", updated)
    return True
