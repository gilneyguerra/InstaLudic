"""Parser tests: lead_capture must extract phone, email, service, urgency."""
from pathlib import Path

from modules.database import Database
from modules.lead_capture import LeadCapture


def fresh_db(tmp_path: Path) -> Database:
    return Database(db_path=tmp_path / "test.db")


def test_parser_extracts_phone_and_priority(tmp_path):
    db = fresh_db(tmp_path)
    cap = LeadCapture(db)
    lead_id = cap.process_raw_text("Tel: 22 99888-7777, psicologia, urgente")
    assert lead_id is not None
    lead = db.get_lead(lead_id)
    assert lead is not None
    assert lead["service"] == "psicologia"
    assert lead["priority"] in ("hot", "warm")
    assert lead["phone"] and "9988" in lead["phone"]


def test_parser_extracts_email(tmp_path):
    db = fresh_db(tmp_path)
    cap = LeadCapture(db)
    lead_id = cap.process_raw_text("Quero marcar fono para meu filho. mae@familia.com")
    assert lead_id is not None
    lead = db.get_lead(lead_id)
    assert lead["email"] == "mae@familia.com"
    assert lead["service"] == "fonoaudiologia"


def test_parser_rejects_text_without_contact(tmp_path):
    db = fresh_db(tmp_path)
    cap = LeadCapture(db)
    lead_id = cap.process_raw_text("Apenas curtindo o conteudo")
    assert lead_id is None


def test_parser_handles_empty_input(tmp_path):
    db = fresh_db(tmp_path)
    cap = LeadCapture(db)
    assert cap.process_raw_text("") is None
    assert cap.process_raw_text("   ") is None


def test_instagram_comment_routed(tmp_path):
    db = fresh_db(tmp_path)
    cap = LeadCapture(db)
    comment = {"text": "fono para meu filho urgente, 22 98765-4321", "username": "mae123"}
    lead_id = cap.process_instagram_comment(comment)
    assert lead_id is not None
    lead = db.get_lead(lead_id)
    assert lead["source"].startswith("instagram:")
