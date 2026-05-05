"""Outreach engine: Twilio WhatsApp + Gmail SMTP, with weekly rate limit (Padrao 5)."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from dotenv import load_dotenv

from modules.utils import get_logger, load_config, safe

load_dotenv()
log = get_logger("casa_ludic.outreach")


class OutreachEngine:
    def __init__(self, db: Any) -> None:
        self.db = db
        self.cfg = load_config()
        self.max_per_week = int(self.cfg.get("outreach", {}).get("max_messages_per_lead_per_week", 5))
        self._twilio = self._build_twilio()

    def _build_twilio(self):
        sid = os.getenv("TWILIO_ACCOUNT_SID")
        token = os.getenv("TWILIO_AUTH_TOKEN")
        if not sid or not token:
            log.warning("Twilio nao configurado - WhatsApp desativado")
            return None
        try:
            from twilio.rest import Client  # local import: optional dependency at runtime
            return Client(sid, token)
        except Exception as exc:  # noqa: BLE001
            log.error("Twilio init falhou: %s", exc)
            return None

    def _within_limit(self, lead_id: int) -> bool:
        used = self.db.count_messages_week(lead_id)
        if used >= self.max_per_week:
            log.warning("Limite semanal atingido para lead %s (%d/%d)", lead_id, used, self.max_per_week)
            return False
        return True

    def _format(self, template_key: str, lead: dict[str, Any]) -> str:
        templates = self.cfg.get("templates", {})
        tmpl = templates.get(template_key, "")
        try:
            return tmpl.format(name=lead.get("name") or "tudo bem?",
                               service=(lead.get("service") or "avaliacao").replace("_", " "))
        except KeyError as exc:
            log.error("Template %s placeholder invalido: %s", template_key, exc)
            return tmpl

    @safe(default=False, log_name="casa_ludic.outreach")
    def send_whatsapp(self, lead_id: int, template_key: str = "whatsapp_greeting") -> bool:
        lead = self.db.get_lead(lead_id)
        if not lead:
            log.error("Lead %s nao encontrado", lead_id)
            return False
        if not lead.get("phone"):
            log.warning("Lead %s sem phone - skip WhatsApp", lead_id)
            return False
        if not self._within_limit(lead_id):
            return False
        if not self._twilio:
            log.error("Twilio indisponivel")
            self.db.log_outreach(lead_id, "whatsapp", template_key, "skipped:no_client")
            return False

        body = self._format(template_key, lead)
        from_ = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
        phone = lead["phone"]
        if not phone.startswith("+"):
            digits = "".join(c for c in phone if c.isdigit())
            phone = f"+{digits if digits.startswith('55') else '55' + digits}"
        to_ = f"whatsapp:{phone}"

        try:
            msg = self._twilio.messages.create(body=body, from_=from_, to=to_)
            self.db.log_outreach(lead_id, "whatsapp", template_key, f"sent:{msg.sid}")
            self.db.log_audit("outreach_whatsapp", "lead", lead_id, "system", template_key)
            log.info("WhatsApp enviado lead=%s sid=%s", lead_id, msg.sid)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("Twilio send falhou lead=%s: %s", lead_id, exc)
            self.db.log_outreach(lead_id, "whatsapp", template_key, f"error:{exc}")
            return False

    @safe(default=False, log_name="casa_ludic.outreach")
    def send_email(
        self,
        lead_id: int,
        subject_template: str = "email_followup_subject",
        body_template: str = "email_followup_body",
    ) -> bool:
        lead = self.db.get_lead(lead_id)
        if not lead:
            return False
        if not lead.get("email"):
            log.warning("Lead %s sem email - skip", lead_id)
            return False
        if not self._within_limit(lead_id):
            return False

        user = os.getenv("GMAIL_USER")
        password = os.getenv("GMAIL_APP_PASSWORD")
        if not user or not password:
            log.error("Gmail nao configurado")
            self.db.log_outreach(lead_id, "email", body_template, "skipped:no_creds")
            return False

        subject = self._format(subject_template, lead)
        body_html = self._format(body_template, lead)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = lead["email"]
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(user, password)
                server.sendmail(user, [lead["email"]], msg.as_string())
            self.db.log_outreach(lead_id, "email", body_template, "sent")
            self.db.log_audit("outreach_email", "lead", lead_id, "system", body_template)
            log.info("Email enviado lead=%s", lead_id)
            return True
        except Exception as exc:  # noqa: BLE001
            log.error("SMTP falhou lead=%s: %s", lead_id, exc)
            self.db.log_outreach(lead_id, "email", body_template, f"error:{exc}")
            return False

    @safe(default=0, log_name="casa_ludic.outreach")
    def run_hot_outreach(self) -> int:
        """Scheduler job 4: WhatsApp para todos os leads hot ainda em prospect."""
        leads = self.db.list_leads(priority="hot", stage="prospect")
        sent = 0
        for lead in leads:
            if self.send_whatsapp(lead["id"]):
                sent += 1
                self.db.update_stage(lead["id"], "contacted", actor="outreach.hot")
        log.info("Outreach hot: %d/%d enviados", sent, len(leads))
        return sent

    @safe(default=0, log_name="casa_ludic.outreach")
    def run_warm_followup(self) -> int:
        """Scheduler job 5: email follow-up para leads warm."""
        leads = self.db.list_leads(priority="warm")
        sent = 0
        for lead in leads:
            if self.send_email(lead["id"]):
                sent += 1
        log.info("Outreach warm: %d/%d follow-ups", sent, len(leads))
        return sent
