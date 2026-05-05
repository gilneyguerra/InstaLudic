"""Pytest config: ensures project root is on sys.path and uses isolated DB per test."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Provide a Fernet key for tests so encryption path is exercised
if not os.getenv("DB_ENCRYPT_KEY"):
    from cryptography.fernet import Fernet
    os.environ["DB_ENCRYPT_KEY"] = Fernet.generate_key().decode()
