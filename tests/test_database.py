"""Database tests: encryption roundtrip, audit, LGPD delete, weekly limit."""
from pathlib import Path

from modules.database import Database


def make_db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "leads.db")


def test_add_and_decrypt_roundtrip(tmp_path):
    db = make_db(tmp_path)
    lead_id = db.add_lead({
        "name": "Teste",
        "phone": "22999887777",
        "email": "test@test.com",
        "service": "psicologia",
        "priority": "hot",
        "score": 80,
    })
    assert lead_id is not None
    lead = db.get_lead(lead_id)
    assert lead["phone"] == "22999887777"
    assert lead["email"] == "test@test.com"


def test_audit_log_recorded(tmp_path):
    db = make_db(tmp_path)
    lead_id = db.add_lead({"name": "X", "phone": "22999887777", "service": "fono", "priority": "warm"})
    rows = db.conn.execute("SELECT action, entity_id FROM audit_log").fetchall()
    assert any(r["action"] == "create" and r["entity_id"] == lead_id for r in rows)


def test_lgpd_delete(tmp_path):
    db = make_db(tmp_path)
    lead_id = db.add_lead({"name": "Y", "phone": "22999887777", "service": "fono", "priority": "cold"})
    assert db.delete_lead(lead_id, actor="cli") is True
    assert db.get_lead(lead_id) is None
    audit = db.conn.execute("SELECT action FROM audit_log WHERE entity_id = ?", (lead_id,)).fetchall()
    assert any(r["action"] == "delete" for r in audit)


def test_weekly_message_count(tmp_path):
    db = make_db(tmp_path)
    lead_id = db.add_lead({"name": "Z", "phone": "22999887777", "service": "fono", "priority": "hot"})
    assert db.count_messages_week(lead_id) == 0
    db.log_outreach(lead_id, "whatsapp", "greeting", "sent")
    db.log_outreach(lead_id, "whatsapp", "followup", "sent")
    assert db.count_messages_week(lead_id) == 2


def test_export_csv(tmp_path):
    db = make_db(tmp_path)
    db.add_lead({"name": "Export", "phone": "22999887777", "email": "e@e.com",
                 "service": "psicologia", "priority": "hot"})
    out = tmp_path / "leads.csv"
    assert db.export_csv(out) is True
    assert out.exists()
    content = out.read_text(encoding="utf-8-sig")
    assert "22999887777" in content
    assert "e@e.com" in content


def test_kpis_returns_dict(tmp_path):
    db = make_db(tmp_path)
    db.add_lead({"name": "A", "phone": "22999887777", "service": "fono", "priority": "hot"})
    db.add_lead({"name": "B", "phone": "22999887778", "service": "psicologia", "priority": "warm"})
    kpis = db.kpis()
    assert kpis["total_leads"] == 2
    assert "hot" in kpis["by_priority"]
