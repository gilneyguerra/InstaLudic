# Casa Ludic CRM

Sistema integrado de captação e conversão de leads para a Casa Ludic — clínica multidisciplinar infantil em Rio das Ostras/RJ.

## Stack

- Python 3.9+
- APScheduler (jobs 24/7)
- SQLite + Fernet (LGPD)
- Twilio WhatsApp + Gmail SMTP
- instagrapi (Instagram)
- ReportLab (PDF) + Jinja2 + Chart.js (HTML)

## Setup

```powershell
python setup_casa_ludic.py
.\venv\Scripts\Activate.ps1
# Edite .env preenchendo TWILIO_*, GMAIL_*, IG_* (DB_ENCRYPT_KEY já vem gerada)
```

### Como obter credenciais

- **Twilio**: console.twilio.com → Account SID + Auth Token. Para WhatsApp use Sandbox: `whatsapp:+14155238886`.
- **Gmail App Password**: https://myaccount.google.com/apppasswords (requer 2FA ativo).
- **Instagram**: usuário/senha da conta `@casaludic`. Sessão é persistida em `outputs/ig_session.json`.

## Uso

```powershell
python cli_interface.py    # menu interativo
python main.py             # scheduler 24/7 (7 jobs)
pytest                     # rodar testes
```

## Jobs do scheduler

| Job | Cron | Descrição |
|-----|------|-----------|
| 1 | `0 */6 * * *` | Sync métricas Instagram |
| 2 | `*/30 * * * *` | Captura comentários IG → leads |
| 3 | `0 * * * *` | Requalifica leads pendentes |
| 4 | `0 9,14,18 * * *` | WhatsApp para leads hot |
| 5 | `0 10 * * 1,3,5` | Email follow-up para leads warm |
| 6 | `0 8 * * *` | Relatório PDF + dashboard HTML |
| 7 | `0 9 * * 1` | Sugestões semanais de conteúdo |

## Padrões aplicados

- **LGPD**: phone/email encriptados com Fernet; `audit_log` em toda mutação; `delete_lead()` para esquecimento; limite 5 mensagens/lead/semana.
- **Erros (graceful)**: decorator `@safe` em todas as operações públicas; nada propaga exceção; tudo é logado em `outputs/casa_ludic.log`.
- **Relatórios**: PDF Helvetica via ReportLab; HTML com paleta `#667eea/#764ba2/#4CAF50/#FF9800/#F44336`; CSV `utf-8-sig`.

## Troubleshooting

| Sintoma | Ação |
|---------|------|
| `ModuleNotFoundError` | Ativar venv: `.\venv\Scripts\Activate.ps1` |
| `Twilio 401` | Verificar `TWILIO_AUTH_TOKEN`; em sandbox o número precisa ser autorizado |
| `Gmail SMTPAuthenticationError` | Use App Password, não senha normal |
| Instagram bloqueia login | Sistema cai automaticamente em mock; verifique `outputs/casa_ludic.log` |
| `database is locked` | Apenas uma instância de `main.py` por vez |

## Estrutura

```
casa-ludic-crm/
├── main.py             # scheduler
├── cli_interface.py    # menu
├── setup_casa_ludic.py # bootstrap
├── config.json         # serviços, templates, paleta, limites
├── modules/            # database, lead_capture, qualification, outreach, instagram_monitor, analytics, content_recommender, utils
├── templates/          # dashboard.html
├── tests/              # pytest
└── outputs/            # leads.db, casa_ludic.log, *.pdf, *.html, *.csv (gitignored)
```
