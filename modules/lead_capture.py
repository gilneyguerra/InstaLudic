"""Lead capture: parse raw text and Instagram comments into qualified leads."""
from __future__ import annotations

import re
from typing import Any, Optional

from modules.lead_qualification import score
from modules.utils import get_logger, load_config, safe, validate_email, validate_phone

log = get_logger("casa_ludic.capture")

_NAME_RE = re.compile(r"(?:sou|me chamo|meu nome[ée]?)\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç]{2,}(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇa-záéíóúâêôãõç]+){0,3})", re.IGNORECASE)


class LeadCapture:
    """Extract leads from free text. All public methods return Optional[int] (lead_id)."""

    def __init__(self, db: Any) -> None:
        self.db = db
        cfg = load_config()
        self.aliases: dict[str, str] = {k.lower(): v for k, v in cfg.get("service_aliases", {}).items()}
        self.services: list[str] = cfg.get("services", [])

    def _detect_service(self, text: str) -> str:
        lower = text.lower()
        for alias, canonical in self.aliases.items():
            if alias in lower:
                return canonical
        for svc in self.services:
            if svc.replace("_", " ") in lower:
                return svc
        return "indefinido"

    def _detect_name(self, text: str) -> str:
        m = _NAME_RE.search(text)
        if m:
            return m.group(1).strip().title()
        return "Lead Automático"

    @safe(default=None, log_name="casa_ludic.capture")
    def process_raw_text(self, text: str, source: str = "manual") -> Optional[int]:
        """Parse raw text into a lead and persist. Returns lead_id or None."""
        if not text or not text.strip():
            log.warning("Texto vazio em process_raw_text")
            return None

        phone = validate_phone(text)
        email_match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
        email = validate_email(email_match.group(0)) if email_match else None
        service = self._detect_service(text)
        name = self._detect_name(text)

        if not phone and not email:
            log.info("Texto descartado (sem phone nem email): %.60s", text)
            return None

        lead_data = {
            "name": name,
            "phone": phone,
            "email": email,
            "service": service,
            "source": source,
            "raw_text": text,
        }
        s, priority = score(lead_data)
        lead_data["score"] = s
        lead_data["priority"] = priority
        lead_id = self.db.add_lead(lead_data)
        if lead_id:
            log.info("Lead %s capturado de %s (%s, %s)", lead_id, source, service, priority)
        return lead_id

    @safe(default=None, log_name="casa_ludic.capture")
    def process_instagram_comment(self, comment: dict[str, Any]) -> Optional[int]:
        """Comment dict shape: {text: str, username: str, ...}."""
        text = comment.get("text", "")
        username = comment.get("username", "ig_user")
        enriched = f"{text} (@{username})"
        return self.process_raw_text(enriched, source=f"instagram:{username}")
