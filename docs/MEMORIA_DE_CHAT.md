# Memória de Chat — Casa Ludic CRM

> **Propósito deste arquivo:** snapshot completo da conversa entre o usuário (Gilney Guerra) e o Claude Code, para que em outra máquina ou nova sessão seja possível retomar exatamente de onde paramos. Atualizado em **2026-05-05**.

---

## Como usar este arquivo

1. Em qualquer máquina, clone o repo: `git clone https://github.com/gilneyguerra/InstaLudic.git`
2. Abra `casa-ludic-crm/docs/MEMORIA_DE_CHAT.md`
3. Cole o conteúdo dele (ou faça upload) numa nova sessão Claude Code com o prompt:

   > "Leia o arquivo `docs/MEMORIA_DE_CHAT.md`. Estamos retomando este projeto exatamente do ponto descrito na seção 'Estado atual e próximo passo'. Continue daí."

---

## 1. Contexto do projeto

**Casa Ludic** — clínica multidisciplinar infantil em Rio das Ostras/RJ. Especialidades: Psicologia, Fisioterapia, Fonoaudiologia, Musicalização, Psicopedagogia, Terapia Ocupacional.

**Sistema:** CRM em Python que automatiza captação e conversão de leads via Instagram + WhatsApp (Twilio) + Email (Gmail SMTP). Persistência em SQLite com Fernet/AES-128 para LGPD. Scheduler 24/7 via APScheduler.

**Metas operacionais:**
- 50-100 leads qualificados/mês
- Conversão >30% prospect→paciente
- +R$7.500-15.000/mês de faturamento

**Stack:** Python 3.9+, Docker Compose, SQLite, Ubuntu 22.04 VPS, deploy em `/opt/casa-ludic-crm`.

**Repo:** <https://github.com/gilneyguerra/InstaLudic.git>
**Diretório local de trabalho:** `c:\Users\gguerra\Desktop\Ludic\casa-ludic-crm`

---

## 2. Histórico da conversa (resumido)

### Turno 1 — Reabertura do chat
**Usuário:** o chat anterior fechou sem querer; estavam construindo o app; pararam no processo de construção da VPN. Pediu pra restaurar.

**Claude:** explicou que não acessa histórico de sessões anteriores, mas pode reconstruir contexto a partir dos arquivos. Listou estrutura do projeto. Perguntou:
1. Qual o objetivo da VPN? (acesso admin ou saída do scraper IG?)
2. Tecnologia escolhida? (WireGuard / OpenVPN / Tailscale?)
3. Já tinha algum arquivo começado?

### Turno 2 — Decisões da VPN
**Usuário:**
- Objetivo: **acesso admin**
- Tecnologia: **Tailscale**
- Não tinha arquivo prévio
- **Diretiva durável:** "Atualize sempre o repositório após cada interação e modificação no código"

**Claude:**
- Verificou git status — havia arquivos não commitados da sessão anterior (`Dockerfile`, `docker-compose.yml`, `.dockerignore`, `deploy/backup.sh`, `deploy/cli.sh`, `deploy/setup_vps.sh`)
- Salvou na memória: feedback de auto-push, contexto do projeto, referência ao repo
- **Criou:** `casa-ludic-crm/deploy/setup_tailscale.sh` — script idempotente que:
  - Instala Tailscale via instalador oficial
  - Libera interface `tailscale0` no UFW
  - Sobe com `--ssh --hostname=casa-ludic-vps --accept-routes`
  - Aceita `TS_AUTHKEY` (não-interativo) ou pede URL no terminal
  - Imprime instruções pós-setup
- **Modificou:** `setup_vps.sh` — adicionou passo 6 opcional apontando pro tailscale
- **Modificou:** `docs/README.md` — seção "Acesso admin via Tailscale" + entradas de troubleshooting
- **Commit:** `e49fc23` — `feat(deploy): Docker stack + VPS provisioning + Tailscale admin VPN`

### Turno 3 — Vercel + guia completo
**Usuário:** sem experiência com VPN, pediu guia passo a passo. Perguntou se podia rodar no Vercel.

**Claude:**
- **Vercel:** veredito direto = **não viável**. Razões:
  - APScheduler 24/7 incompatível com funções serverless efêmeras (60s Hobby / 300s Pro)
  - SQLite com persistência em `outputs/leads.db` impossível (filesystem read-only)
  - Sessão `instagrapi` precisa persistir
  - CLI interativa não roda em serverless
  - Docker Compose não suportado
  - IPs do Vercel em blocklists do Instagram
- **Recomendou VPS:** Hetzner CX22 (€4,5/mês ~R$25), DigitalOcean ($6/mês), AWS Lightsail-São Paulo ($5/mês)
- **Criou:** `docs/TAILSCALE_GUIDE.md` — guia completo de 7 passos para iniciantes:
  1. Criar conta Tailscale
  2. Instalar no notebook (Win/Mac/Linux)
  3. SSH na VPS via IP público (única vez)
  4. Rodar `setup_tailscale.sh`
  5. Autorizar URL no navegador
  6. Testar `ssh root@casa-ludic-vps`
  7. (Opcional) Fechar SSH público
- **Modificou:** `docs/README.md` — link em destaque pro guia
- **Commit:** `b012643` — `docs: guia Tailscale completo para usuarios sem experiencia em VPN`

### Turno 4 — Questionário de onboarding Tailscale
**Usuário:** mandou print da tela de pesquisa do Tailscale (perguntando role, VPN provider, etc.). Perguntou como configurar.

**Claude:** explicou que é só pesquisa de marketing, não afeta nada técnico. Recomendou:
- Primary reason: `Infrastructure Access`
- Role: `IT` ou `Developer` ou `Founder / Owner` (não Sales/Marketing)
- VPN provider: `I don't use a VPN`
- How did you hear: opcional, pular

Atualizou o guia com essas instruções.
- **Commit:** `488d338` — `docs(tailscale): explicar questionario de onboarding e como pular fluxo guiado`

### Turno 5 — Tela Machines
**Usuário:** mandou print da tela <https://login.tailscale.com/admin/machines> com o dropdown de "Add device" aberto (opções: Linux server / Client device). Tailnet criada: `gilneyguerra.github` (Free plan, login via GitHub).

**Claude:** explicou que pode ignorar o botão "Add device" — quando o cliente é instalado e faz login com a mesma conta, a máquina aparece sozinha. Orientou ir pro Passo 2 do guia (instalar Tailscale no Windows via <https://tailscale.com/download/windows>).

### Turno 6 — Sem permissão de instalação
**Usuário:** não tem permissão administrativa nessa máquina pra instalar o cliente Tailscale. Pediu pra criar este arquivo de memória de chat e fazer push pro repo, pra continuar em outro computador.

**Claude:** criou este arquivo, está fazendo o commit/push.

---

## 3. Decisões durāveis tomadas

| Decisão | Por quê |
|---|---|
| **Tailscale (não WireGuard)** | Zero-config, free até 100 dispositivos, ideal para 1 operador |
| **VPS (não Vercel)** | App tem jobs 24/7, SQLite persistente, sessão IG, CLI — tudo incompatível com serverless |
| **UFW em modo paranoico** | Só SSH liberado; outras portas privadas via tailnet |
| **SSH via Tailscale (`--ssh`)** | Permite fechar SSH público no futuro |
| **Auto-push após cada modificação** | Diretiva durável do usuário; commits descritivos em português |

---

## 4. Estado atual do repositório

**Branch:** `main`
**Último commit antes deste arquivo:** `488d338`
**Arquivos relevantes criados/modificados nesta sessão:**

```
casa-ludic-crm/
├── deploy/
│   ├── setup_tailscale.sh          [NOVO — script de instalação]
│   ├── setup_vps.sh                [MODIFICADO — passo 6 menciona tailscale]
│   ├── backup.sh                   [já existia — agora versionado]
│   └── cli.sh                      [já existia — agora versionado]
├── docs/
│   ├── README.md                   [MODIFICADO — seção Tailscale + link pro guia]
│   ├── TAILSCALE_GUIDE.md          [NOVO — guia passo a passo de 7 passos]
│   └── MEMORIA_DE_CHAT.md          [NOVO — este arquivo]
├── Dockerfile                      [já existia — agora versionado]
├── docker-compose.yml              [já existia — agora versionado]
└── .dockerignore                   [já existia — agora versionado]
```

**Histórico de commits desta sessão:**
- `e49fc23` — feat(deploy): Docker stack + VPS provisioning + Tailscale admin VPN
- `b012643` — docs: guia Tailscale completo para usuarios sem experiencia em VPN
- `488d338` — docs(tailscale): explicar questionario de onboarding e como pular fluxo guiado
- (próximo, ao fim deste turno) — docs: memória de chat para retomada em outra máquina

---

## 5. Estado atual e próximo passo

### Onde paramos exatamente

Você (Gilney) está na tela <https://login.tailscale.com/admin/machines> da sua tailnet `gilneyguerra.github`. Conta criada (login via GitHub), nenhuma máquina ainda conectada.

**Bloqueio:** sem permissão administrativa na máquina atual para instalar o cliente Tailscale.

### O que fazer na próxima máquina

1. **Abra o repo** em uma máquina onde você tenha permissão de admin: `git clone https://github.com/gilneyguerra/InstaLudic.git`

2. **Leia este arquivo** + o guia: `casa-ludic-crm/docs/TAILSCALE_GUIDE.md`

3. **Retome no Passo 2** do guia (já completou o Passo 1, conta está criada):
   - Instalar o cliente Tailscale na máquina (Windows: <https://tailscale.com/download/windows>)
   - Login com a **mesma conta GitHub** (`gilneyguerra`)
   - Confirmar que a máquina aparece em <https://login.tailscale.com/admin/machines>

4. **Depois disso, prossiga para os Passos 3-7:**
   - Passo 3: SSH na VPS via IP público (você precisa ter a VPS provisionada antes — veja seção 6 abaixo)
   - Passo 4: rodar `sudo bash /opt/casa-ludic-crm/deploy/setup_tailscale.sh`
   - Passo 5: autorizar URL impressa no navegador
   - Passo 6: testar `ssh root@casa-ludic-vps`
   - Passo 7: (opcional) fechar SSH público

### Para retomar com Claude Code

Numa nova sessão, comece com:

> "Estou retomando o projeto Casa Ludic CRM em outra máquina. Acabei de instalar o Tailscale no notebook. Preciso seguir do Passo 3 em diante do `docs/TAILSCALE_GUIDE.md`. Já tenho a VPS provisionada / Ainda preciso provisionar a VPS." (escolha a frase que se aplica)

---

## 6. Pendências e próximas decisões em aberto

### 1. Provisionar a VPS (ainda não feito)

Você ainda não criou a VPS. Antes de qualquer coisa do Tailscale-na-VPS, precisa:

1. Escolher um provedor (recomendados: **Hetzner CX22** ~R$25/mês, **AWS Lightsail-São Paulo** ~R$32/mês, **DigitalOcean** ~R$32/mês)
2. Criar uma instância Ubuntu 22.04
3. Obter o IP público + senha de root (ou configurar chave SSH)
4. Rodar `sudo bash setup_vps.sh` na VPS
5. Configurar credenciais em `/opt/casa-ludic-crm/.env` (Twilio, Gmail, Instagram)
6. **Aí sim** rodar `setup_tailscale.sh`

Pergunte ao Claude na próxima sessão: *"Me ajude a escolher e provisionar a VPS."*

### 2. Outras decisões em aberto

Mencionadas mas não decididas:
- Fechar SSH público após confirmar Tailscale (recomendado, mas requer 1 semana de validação)
- Healthcheck no `docker-compose.yml`
- Escrever testes pytest mencionados no README
- Migração futura para API oficial Graph do Instagram (Fase 2 do roadmap)

---

## 7. Referência rápida — comandos importantes

### Provisionar VPS (após criar Ubuntu 22.04)
```bash
# Como root na VPS:
git clone https://github.com/gilneyguerra/InstaLudic.git /tmp/setup
sudo bash /tmp/setup/casa-ludic-crm/deploy/setup_vps.sh
nano /opt/casa-ludic-crm/.env   # preencher credenciais
cd /opt/casa-ludic-crm && docker compose up -d
```

### Configurar Tailscale na VPS
```bash
sudo bash /opt/casa-ludic-crm/deploy/setup_tailscale.sh
# (cole a URL impressa no navegador, autorize com a conta GitHub)
```

### Acesso diário (após Tailscale ativo)
```bash
ssh root@casa-ludic-vps                                              # SSH privado
ssh root@casa-ludic-vps 'bash /opt/casa-ludic-crm/deploy/cli.sh'     # CLI do CRM
ssh root@casa-ludic-vps 'docker compose -f /opt/casa-ludic-crm/docker-compose.yml logs -f --tail=50'
```

### Atualizar código após push no GitHub
```bash
ssh root@casa-ludic-vps 'cd /opt/casa-ludic-crm && git pull && docker compose up -d --build'
```

---

## 8. Credenciais — onde estão (NUNCA commitar)

Estes valores ficam no arquivo `.env` da VPS, criado pelo `setup_vps.sh`. **Não vão para o git** (estão no `.gitignore`).

| Variável | Onde obter |
|---|---|
| `DB_ENCRYPT_KEY` | Auto-gerada pelo `setup_vps.sh` |
| `TWILIO_ACCOUNT_SID` | <https://console.twilio.com> |
| `TWILIO_AUTH_TOKEN` | mesmo console Twilio |
| `TWILIO_WHATSAPP_FROM` | sandbox: `whatsapp:+14155238886` |
| `GMAIL_USER` | email da clínica |
| `GMAIL_APP_PASSWORD` | <https://myaccount.google.com/apppasswords> (precisa 2FA ativo) |
| `IG_USER` | `casaludic` |
| `IG_PASS` | senha do Instagram da clínica |

---

**Fim do arquivo.** Boa retomada na próxima máquina.
