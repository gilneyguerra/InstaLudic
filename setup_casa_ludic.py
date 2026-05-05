#!/usr/bin/env python3
"""Bootstrap script: creates venv, installs deps, scaffolds .env."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIRS = ["modules", "templates", "tests", "outputs", "docs", "external_repos"]


def run(cmd: list[str], description: str = "", check: bool = True) -> int:
    if description:
        print(f"  [INSTALANDO] {description}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if check and result.returncode != 0:
        print(f"  ✗ Falha em: {description or cmd}")
        sys.exit(result.returncode)
    return result.returncode


def create_directories() -> None:
    for d in DIRS:
        (ROOT / d).mkdir(parents=True, exist_ok=True)
    print("  ✓ Diretorios criados")


def create_venv() -> Path:
    venv_dir = ROOT / "venv"
    if venv_dir.exists():
        print("  ✓ venv ja existe - skip")
    else:
        run([sys.executable, "-m", "venv", "venv"], description="Virtual environment")
    if sys.platform == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def install_requirements(py: Path) -> None:
    req = ROOT / "requirements.txt"
    if not req.exists():
        print(f"  ✗ requirements.txt nao encontrado em {req}")
        sys.exit(1)
    run([str(py), "-m", "pip", "install", "--upgrade", "pip"], description="pip upgrade")
    run([str(py), "-m", "pip", "install", "-r", str(req)], description="dependencias")


def ensure_env() -> None:
    env_path = ROOT / ".env"
    example = ROOT / ".env.example"
    if env_path.exists():
        print("  ✓ .env ja existe - preservando")
        return
    if example.exists():
        shutil.copyfile(example, env_path)
    else:
        env_path.write_text("DB_ENCRYPT_KEY=\n", encoding="utf-8")

    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        content = env_path.read_text(encoding="utf-8")
        if "DB_ENCRYPT_KEY=" in content and not content.split("DB_ENCRYPT_KEY=")[1].split("\n")[0].strip():
            content = content.replace("DB_ENCRYPT_KEY=", f"DB_ENCRYPT_KEY={key}", 1)
            env_path.write_text(content, encoding="utf-8")
        print(f"  ✓ .env criado com DB_ENCRYPT_KEY auto-gerada")
    except Exception as exc:
        print(f"  ⚠ Nao foi possivel gerar Fernet key automaticamente: {exc}")
        print(f"    Gere manualmente: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")


def setup() -> None:
    print("=" * 56)
    print("  Casa Ludic CRM - Setup")
    print("=" * 56)
    create_directories()
    py = create_venv()
    install_requirements(py)
    ensure_env()
    print()
    print("=" * 56)
    print("  ✓ SETUP CONCLUIDO")
    print("=" * 56)
    print()
    print("Proximos passos:")
    if sys.platform == "win32":
        print("  1. .\\venv\\Scripts\\Activate.ps1")
    else:
        print("  1. source venv/bin/activate")
    print("  2. Edite .env e preencha TWILIO_*, GMAIL_*, IG_*")
    print("  3. python cli_interface.py   (menu interativo)")
    print("  4. python main.py            (scheduler 24/7)")


if __name__ == "__main__":
    setup()
