"""CRM Database with Fernet encryption (LGPD) and audit_log."""
from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv

from modules.utils import get_logger, safe

load_dotenv()

log = get_logger("casa_ludic.database")
DB_PATH = Path(__file__).resolve().parent.parent / "outputs" / "leads.db"


class Database:
    """SQLite + Fernet-backed CRM store. Methods never raise - return bool/Optional."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cipher: Optional[Fernet] = self._init_cipher()
        self._create_tables()
        log.info("Database inicializado em %s (cipher=%s)", db_path, bool(self.cipher))

    def _init_cipher(self) -> Optional[Fernet]:
        key = os.getenv("DB_ENCRYPT_KEY")
        if not key:
            log.warning("DB_ENCRYPT_KEY ausente - dados serao gravados em texto puro")
            return None
        try:
            return Fernet(key.encode())
        except Exception as exc:  # noqa: BLE001
            log.error("DB_ENCRYPT_KEY invalida: %s", exc)
            return None

    def _create_tables(self) -> None:
        c = self.conn.cursor()
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone_enc TEXT,
                email_enc TEXT,
                service TEXT,
                priority TEXT,
                stage TEXT DEFAULT 'prospect',
                score INTEGER DEFAULT 0,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS outreach_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                template TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                entity TEXT,
                entity_id INTEGER,
                actor TEXT,
                details TEXT,
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS instagram_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                followers INTEGER,
                posts INTEGER,
                engagement REAL,
                source TEXT DEFAULT 'real'
            );
            """
        )
        self.conn.commit()

    def _encrypt(self, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        if not self.cipher:
            return value
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        if not self.cipher:
            return value
        try:
            return self.cipher.decrypt(value.encode()).decode()
        except InvalidToken:
            log.warning("Token Fernet invalido - retornando bruto")
            return value

    @safe(default=None, log_name="casa_ludic.database")
    def add_lead(self, data: dict[str, Any]) -> Optional[int]:
        """Insert lead. Returns lead_id or None."""
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO leads (name, phone_enc, email_enc, service, priority, score, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data.get("name", "Sem nome"),
                self._encrypt(data.get("phone")),
                self._encrypt(data.get("email")),
                data.get("service", "indefinido"),
                data.get("priority", "cold"),
                int(data.get("score", 0)),
                data.get("source", "manual"),
            ),
        )
        lead_id = cursor.lastrowid
        self.conn.commit()
        self.log_audit("create", "lead", lead_id, data.get("source", "manual"), str(data.get("priority")))
        log.info("Lead %s criado (priority=%s)", lead_id, data.get("priority"))
        return lead_id

    @safe(default=None, log_name="casa_ludic.database")
    def get_lead(self, lead_id: int) -> Optional[dict[str, Any]]:
        row = self.conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["phone"] = self._decrypt(d.pop("phone_enc"))
        d["email"] = self._decrypt(d.pop("email_enc"))
        return d

    @safe(default=[], log_name="casa_ludic.database")
    def list_leads(self, priority: Optional[str] = None, stage: Optional[str] = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM leads WHERE 1=1"
        params: list[Any] = []
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        if stage:
            query += " AND stage = ?"
            params.append(stage)
        query += " ORDER BY created_at DESC"
        rows = self.conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["phone"] = self._decrypt(d.pop("phone_enc"))
            d["email"] = self._decrypt(d.pop("email_enc"))
            result.append(d)
        return result

    @safe(default=False, log_name="casa_ludic.database")
    def update_stage(self, lead_id: int, stage: str, actor: str = "system") -> bool:
        self.conn.execute(
            "UPDATE leads SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (stage, lead_id),
        )
        self.conn.commit()
        self.log_audit("update_stage", "lead", lead_id, actor, stage)
        return True

    @safe(default=False, log_name="casa_ludic.database")
    def update_score(self, lead_id: int, score: int, priority: str) -> bool:
        self.conn.execute(
            "UPDATE leads SET score = ?, priority = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (score, priority, lead_id),
        )
        self.conn.commit()
        self.log_audit("qualify", "lead", lead_id, "system", f"{priority}:{score}")
        return True

    @safe(default=False, log_name="casa_ludic.database")
    def delete_lead(self, lead_id: int, actor: str = "user") -> bool:
        """LGPD - direito ao esquecimento."""
        self.conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        self.conn.execute("DELETE FROM outreach_log WHERE lead_id = ?", (lead_id,))
        self.conn.commit()
        self.log_audit("delete", "lead", lead_id, actor, "lgpd")
        log.info("Lead %s removido por %s (LGPD)", lead_id, actor)
        return True

    @safe(default=0, log_name="casa_ludic.database")
    def count_messages_week(self, lead_id: int) -> int:
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM outreach_log WHERE lead_id = ? AND sent_at >= ?",
            (lead_id, cutoff),
        ).fetchone()
        return int(row["n"]) if row else 0

    @safe(default=False, log_name="casa_ludic.database")
    def log_outreach(self, lead_id: int, channel: str, template: str, status: str) -> bool:
        self.conn.execute(
            "INSERT INTO outreach_log (lead_id, channel, template, status) VALUES (?, ?, ?, ?)",
            (lead_id, channel, template, status),
        )
        self.conn.commit()
        return True

    @safe(default=False, log_name="casa_ludic.database")
    def log_audit(self, action: str, entity: str, entity_id: Optional[int], actor: str, details: str) -> bool:
        self.conn.execute(
            "INSERT INTO audit_log (action, entity, entity_id, actor, details) VALUES (?, ?, ?, ?, ?)",
            (action, entity, entity_id, actor, details),
        )
        self.conn.commit()
        return True

    @safe(default=False, log_name="casa_ludic.database")
    def save_instagram_metrics(self, followers: int, posts: int, engagement: float, source: str = "real") -> bool:
        self.conn.execute(
            "INSERT INTO instagram_metrics (date, followers, posts, engagement, source) VALUES (?, ?, ?, ?, ?)",
            (datetime.utcnow().date().isoformat(), followers, posts, engagement, source),
        )
        self.conn.commit()
        log.info("Instagram metrics gravadas (source=%s)", source)
        return True

    @safe(default=None, log_name="casa_ludic.database")
    def latest_instagram_metrics(self) -> Optional[dict[str, Any]]:
        row = self.conn.execute(
            "SELECT * FROM instagram_metrics ORDER BY date DESC, id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    @safe(default=False, log_name="casa_ludic.database")
    def export_csv(self, path: Path) -> bool:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        leads = self.list_leads()
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "name", "phone", "email", "service", "priority",
                "stage", "score", "source", "created_at",
            ])
            for lead in leads:
                writer.writerow([
                    lead["id"], lead["name"], lead.get("phone") or "",
                    lead.get("email") or "", lead["service"], lead["priority"],
                    lead["stage"], lead["score"], lead.get("source", ""),
                    lead["created_at"],
                ])
        self.log_audit("export_csv", "leads", None, "user", str(path))
        log.info("CSV exportado: %s (%d leads)", path, len(leads))
        return True

    @safe(default={}, log_name="casa_ludic.database")
    def kpis(self) -> dict[str, Any]:
        c = self.conn.cursor()
        total = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        by_priority = {
            row["priority"] or "unknown": row["n"]
            for row in c.execute(
                "SELECT priority, COUNT(*) as n FROM leads GROUP BY priority"
            ).fetchall()
        }
        by_stage = {
            row["stage"] or "unknown": row["n"]
            for row in c.execute(
                "SELECT stage, COUNT(*) as n FROM leads GROUP BY stage"
            ).fetchall()
        }
        by_service = {
            row["service"] or "unknown": row["n"]
            for row in c.execute(
                "SELECT service, COUNT(*) as n FROM leads GROUP BY service"
            ).fetchall()
        }
        outreach = c.execute("SELECT COUNT(*) FROM outreach_log").fetchone()[0]
        last_30 = c.execute(
            "SELECT DATE(created_at) as d, COUNT(*) as n FROM leads "
            "WHERE created_at >= DATE('now', '-30 days') GROUP BY DATE(created_at) ORDER BY d"
        ).fetchall()
        return {
            "total_leads": total,
            "by_priority": by_priority,
            "by_stage": by_stage,
            "by_service": by_service,
            "total_outreach": outreach,
            "timeline_30d": [{"date": r["d"], "count": r["n"]} for r in last_30],
        }

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:  # noqa: BLE001
            pass
