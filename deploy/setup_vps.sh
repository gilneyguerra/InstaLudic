#!/usr/bin/env bash
# Setup idempotente para Casa Ludic CRM em VPS Ubuntu 22.04
# Uso: bash setup_vps.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/gilneyguerra/InstaLudic.git}"
APP_DIR="${APP_DIR:-/opt/casa-ludic-crm}"

log()  { printf "\033[1;34m[setup]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ok]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[fail]\033[0m %s\n" "$*"; exit 1; }

[[ $EUID -eq 0 ]] || die "Rode como root (sudo bash setup_vps.sh)"

log "1/7 Atualizando pacotes do sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq

log "2/7 Instalando Docker + Compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
  ok "Docker instalado: $(docker --version)"
else
  ok "Docker ja presente: $(docker --version)"
fi

log "3/7 Configurando firewall (UFW: SSH apenas)"
if ! command -v ufw >/dev/null 2>&1; then
  apt-get install -y -qq ufw
fi
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw --force enable
ok "Firewall ativo (so SSH liberado)"

log "4/7 Clonando/atualizando repositorio em $APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" fetch --all -q
  git -C "$APP_DIR" reset --hard origin/main -q
  ok "Repositorio atualizado"
else
  git clone -q "$REPO_URL" "$APP_DIR"
  ok "Repositorio clonado"
fi
cd "$APP_DIR"

log "5/7 Preparando .env"
if [[ ! -f .env ]]; then
  cp .env.example .env
  KEY=$(docker run --rm python:3.11-slim sh -c "pip install -q cryptography && python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'")
  sed -i "s|^DB_ENCRYPT_KEY=.*|DB_ENCRYPT_KEY=$KEY|" .env
  chmod 600 .env
  warn ".env criado com DB_ENCRYPT_KEY auto-gerada"
  warn "VOCE PRECISA EDITAR: nano $APP_DIR/.env"
  warn "Preencha TWILIO_*, GMAIL_*, IG_* antes de subir o servico"
else
  ok ".env ja existe (preservado)"
fi

log "6/7 Configurando backup diario do SQLite"
install -m 0755 deploy/backup.sh /usr/local/bin/casa-ludic-backup
mkdir -p "$APP_DIR/outputs/backups"
cat > /etc/cron.d/casa-ludic-backup <<'CRON'
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 3 * * * root /usr/local/bin/casa-ludic-backup >> /var/log/casa-ludic-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/casa-ludic-backup
ok "Backup agendado para 03:00 (mantem 14 dias)"

log "7/7 Build da imagem Docker (pode levar 3-5 min na primeira vez)"
docker compose build

cat <<EOF

============================================================
  Casa Ludic CRM - setup do VPS concluido
============================================================

Proximos passos MANUAIS:

  1. Edite as credenciais:
       nano $APP_DIR/.env

     Preencha (sem aspas):
       TWILIO_ACCOUNT_SID=AC...
       TWILIO_AUTH_TOKEN=...
       TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
       GMAIL_USER=clinica@gmail.com
       GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
       IG_USER=casaludic
       IG_PASS=...

  2. Suba o servico:
       cd $APP_DIR && docker compose up -d

  3. Veja os logs em tempo real:
       docker compose logs -f

  4. Use a CLI interativa (capturar leads, gerar PDF, etc):
       bash $APP_DIR/deploy/cli.sh

  5. Atualizar o codigo no futuro:
       cd $APP_DIR && git pull && docker compose up -d --build

  6. (Recomendado) Configurar acesso admin privado via Tailscale,
     evitando expor SSH publico:
       sudo bash $APP_DIR/deploy/setup_tailscale.sh
     Veja docs/README.md secao "Acesso admin via Tailscale".
EOF
