"""Config + utils tests."""
from modules.utils import EMOJI, PALETTE, load_config, validate_email, validate_phone


def test_config_loads_services():
    cfg = load_config()
    services = cfg.get("services", [])
    assert "psicologia" in services
    assert "fonoaudiologia" in services
    assert len(services) >= 6


def test_palette_has_required_colors():
    for key in ("primary", "secondary", "success", "warn", "error"):
        assert key in PALETTE
        assert PALETTE[key].startswith("#")


def test_emoji_table():
    for key in ("ok", "err", "warn", "info", "hot", "warm", "cold"):
        assert key in EMOJI


def test_validate_phone_accepts_br_format():
    assert validate_phone("22 99888-7777") is not None
    assert validate_phone("(22) 9988-7777") is not None
    assert validate_phone("+55 22 99888-7777") is not None
    assert validate_phone("not a phone") is None


def test_validate_email():
    assert validate_email("a@b.com") == "a@b.com"
    assert validate_email("Mae@Familia.COM") == "mae@familia.com"
    assert validate_email("invalid") is None
    assert validate_email(None) is None
