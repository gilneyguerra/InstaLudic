"""Interactive CLI for Casa Ludic CRM."""
from __future__ import annotations

import os
import time
from typing import Callable

from modules.analytics import Analytics
from modules.content_recommender import suggest_topics
from modules.database import Database
from modules.instagram_monitor import InstagramMonitor
from modules.lead_capture import LeadCapture
from modules.outreach import OutreachEngine
from modules.utils import EMOJI, emoji_for_priority, get_logger, validate_email, validate_phone

log = get_logger("casa_ludic.cli")


def timed(label: str, fn: Callable[[], object]) -> object:
    start = time.perf_counter()
    result = fn()
    elapsed = time.perf_counter() - start
    icon = EMOJI["ok"] if result not in (False, None) else EMOJI["err"]
    print(f"{icon} {label} ({elapsed:.2f}s)")
    return result


def banner() -> None:
    print()
    print("=" * 56)
    print("  CASA LUDIC CRM - Hub de Captacao e Conversao")
    print("=" * 56)


def main_menu() -> None:
    db = Database()
    capture = LeadCapture(db)
    ig = InstagramMonitor(db)
    outreach = OutreachEngine(db)
    analytics = Analytics(db)

    while True:
        banner()
        print("[1] Relatorios")
        print("[2] Leads")
        print("[3] Outreach")
        print("[4] Instagram")
        print("[5] Configuracao")
        print("[0] Sair")
        op = input("\nOpcao: ").strip()

        if op == "1":
            menu_relatorios(analytics)
        elif op == "2":
            menu_leads(db, capture)
        elif op == "3":
            menu_outreach(db, outreach)
        elif op == "4":
            menu_instagram(ig)
        elif op == "5":
            menu_config(db)
        elif op == "0":
            db.close()
            print(f"{EMOJI['ok']} Ate logo!")
            return
        else:
            print(f"{EMOJI['warn']} Opcao invalida")


def menu_relatorios(analytics: Analytics) -> None:
    print("\n--- Relatorios ---")
    print("[1.1] Gerar PDF executivo")
    print("[1.2] Gerar dashboard HTML")
    print("[1.3] Exportar CSV")
    op = input("Opcao: ").strip()
    if op == "1.1":
        path = timed("PDF gerado", lambda: analytics.generate_pdf_report())
        if path:
            print(f"  {EMOJI['info']} {path}")
    elif op == "1.2":
        path = timed("Dashboard HTML gerado", lambda: analytics.generate_html_dashboard())
        if path:
            print(f"  {EMOJI['info']} Abra no navegador: {path}")
    elif op == "1.3":
        path = timed("CSV exportado", lambda: analytics.export_csv())
        if path:
            print(f"  {EMOJI['info']} {path}")


def menu_leads(db: Database, capture: LeadCapture) -> None:
    print("\n--- Leads ---")
    print("[2.1] Capturar lead demo")
    print("[2.2] Listar leads")
    print("[2.3] Atualizar stage")
    print("[2.4] Deletar lead (LGPD)")
    print("[2.5] Capturar de texto livre")
    op = input("Opcao: ").strip()

    if op == "2.1":
        demo = "Oi, sou Maria. Quero agendar fonoaudiologia urgente para meu filho. Tel: 22 99888-7766, email maria@test.com"
        lead_id = timed("Lead demo capturado", lambda: capture.process_raw_text(demo, source="demo"))
        if lead_id:
            print(f"  {EMOJI['info']} lead_id={lead_id}")
        else:
            print(f"  {EMOJI['err']} Verifique o log em outputs/casa_ludic.log")

    elif op == "2.2":
        leads = db.list_leads()
        if not leads:
            print(f"  {EMOJI['info']} Nenhum lead cadastrado")
            return
        print(f"\n  {len(leads)} leads:")
        for lead in leads[:50]:
            icon = emoji_for_priority(lead["priority"])
            phone = lead.get("phone") or "-"
            print(f"  {icon} #{lead['id']} {lead['name']} | {lead['service']} | {lead['stage']} | {phone}")

    elif op == "2.3":
        try:
            lead_id = int(input("Lead ID: ").strip())
        except ValueError:
            print(f"  {EMOJI['err']} ID invalido"); return
        stage = input("Novo stage (prospect/contacted/scheduled/converted/lost): ").strip()
        if stage not in {"prospect", "contacted", "scheduled", "converted", "lost"}:
            print(f"  {EMOJI['err']} Stage invalido"); return
        timed("Stage atualizado", lambda: db.update_stage(lead_id, stage, actor="cli"))

    elif op == "2.4":
        try:
            lead_id = int(input("Lead ID a remover (LGPD): ").strip())
        except ValueError:
            print(f"  {EMOJI['err']} ID invalido"); return
        confirm = input(f"Confirma remocao do lead {lead_id}? (s/N): ").strip().lower()
        if confirm == "s":
            timed("Lead removido", lambda: db.delete_lead(lead_id, actor="cli"))
        else:
            print(f"  {EMOJI['info']} Cancelado")

    elif op == "2.5":
        text = input("Cole a mensagem do lead: ").strip()
        if not text:
            print(f"  {EMOJI['warn']} Texto vazio"); return
        lead_id = timed("Lead capturado", lambda: capture.process_raw_text(text, source="cli_paste"))
        if not lead_id:
            print(f"  {EMOJI['err']} Nao foi possivel extrair lead (precisa de phone ou email)")


def menu_outreach(db: Database, outreach: OutreachEngine) -> None:
    print("\n--- Outreach ---")
    print("[3.1] WhatsApp manual")
    print("[3.2] Email manual")
    print("[3.3] Disparar lote hot (WhatsApp)")
    print("[3.4] Disparar lote warm (Email)")
    op = input("Opcao: ").strip()

    if op == "3.1":
        try:
            lead_id = int(input("Lead ID: ").strip())
        except ValueError:
            print(f"  {EMOJI['err']} ID invalido"); return
        ok = timed("WhatsApp", lambda: outreach.send_whatsapp(lead_id))
        if not ok:
            print(f"  {EMOJI['warn']} Falha - veja outputs/casa_ludic.log e verifique TWILIO_* no .env")

    elif op == "3.2":
        try:
            lead_id = int(input("Lead ID: ").strip())
        except ValueError:
            print(f"  {EMOJI['err']} ID invalido"); return
        ok = timed("Email", lambda: outreach.send_email(lead_id))
        if not ok:
            print(f"  {EMOJI['warn']} Falha - verifique GMAIL_USER e GMAIL_APP_PASSWORD no .env")

    elif op == "3.3":
        sent = timed("Lote hot", lambda: outreach.run_hot_outreach())
        print(f"  {EMOJI['info']} {sent} mensagens enviadas")

    elif op == "3.4":
        sent = timed("Lote warm", lambda: outreach.run_warm_followup())
        print(f"  {EMOJI['info']} {sent} emails enviados")


def menu_instagram(ig: InstagramMonitor) -> None:
    print("\n--- Instagram ---")
    print("[4.1] Sync metrics")
    print("[4.2] Mostrar ultima coleta")
    op = input("Opcao: ").strip()

    if op == "4.1":
        ok = timed("Sync metrics", lambda: ig.sync_metrics())
        if not ok:
            print(f"  {EMOJI['warn']} Sync falhou - logado em outputs/casa_ludic.log")

    elif op == "4.2":
        m = ig.latest()
        if not m:
            print(f"  {EMOJI['info']} Nenhuma coleta ainda - rode 4.1")
            return
        print(f"  Data: {m.get('date')}")
        print(f"  Seguidores: {m.get('followers')}")
        print(f"  Posts: {m.get('posts')}")
        print(f"  Engagement: {m.get('engagement')}%")
        print(f"  Fonte: {m.get('source')}")


def menu_config(db: Database) -> None:
    print("\n--- Configuracao ---")
    print("[5.1] Validar credenciais")
    print("[5.2] Mostrar config (resumo)")
    op = input("Opcao: ").strip()

    if op == "5.1":
        checks = {
            "DB_ENCRYPT_KEY": bool(os.getenv("DB_ENCRYPT_KEY")),
            "TWILIO_ACCOUNT_SID": bool(os.getenv("TWILIO_ACCOUNT_SID")),
            "TWILIO_AUTH_TOKEN": bool(os.getenv("TWILIO_AUTH_TOKEN")),
            "GMAIL_USER": bool(os.getenv("GMAIL_USER")),
            "GMAIL_APP_PASSWORD": bool(os.getenv("GMAIL_APP_PASSWORD")),
            "IG_USER": bool(os.getenv("IG_USER")),
            "IG_PASS": bool(os.getenv("IG_PASS")),
        }
        for key, ok in checks.items():
            icon = EMOJI["ok"] if ok else EMOJI["err"]
            print(f"  {icon} {key}: {'configurado' if ok else 'AUSENTE'}")
        if not all(checks.values()):
            print(f"\n  {EMOJI['warn']} Edite .env para preencher os campos faltantes")

    elif op == "5.2":
        from modules.utils import load_config
        cfg = load_config()
        print(f"  Servicos: {', '.join(cfg.get('services', []))}")
        print(f"  Limite outreach/lead/semana: {cfg.get('outreach', {}).get('max_messages_per_lead_per_week')}")
        print(f"  Total leads: {db.kpis().get('total_leads', 0)}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{EMOJI['ok']} Encerrado")
