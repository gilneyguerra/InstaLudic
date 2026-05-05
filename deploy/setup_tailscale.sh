#!/usr/bin/env bash
# Instala Tailscale na VPS para acesso admin privado (substitui SSH publico).
# Idempotente: pode ser rodado quantas vezes for necessario.
#
# Uso:
#   sudo bash setup_tailscale.sh                       # interativo (URL no terminal)
#   sudo TS_AUTHKEY=tskey-auth-... bash setup_tailscale.sh   # nao-interativo
#   sudo TS_HOSTNAME=ludic-vps TS_AUTHKEY=... bash setup_tailscale.sh
set -euo pipefail

log()  { printf "\033[1;34m[tailscale]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
ok()   { printf "\033[1;32m[ok]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[fail]\033[0m %s\n" "$*"; exit 1; }

[[ $EUID -eq 0 ]] || die "Rode como root (sudo bash setup_tailscale.sh)"

TS_HOSTNAME="${TS_HOSTNAME:-casa-ludic-vps}"

log "1/4 Instalando Tailscale"
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
  ok "Tailscale instalado: $(tailscale version | head -n1)"
else
  ok "Tailscale ja presente: $(tailscale version | head -n1)"
fi

systemctl enable --now tailscaled >/dev/null 2>&1 || true

log "2/4 Liberando interface tailscale0 no UFW"
if command -v ufw >/dev/null 2>&1; then
  ufw allow in on tailscale0 >/dev/null
  ok "UFW: trafego permitido em tailscale0"
else
  warn "UFW nao instalado, pulando regra (rode setup_vps.sh primeiro se quiser firewall)"
fi

log "3/4 Conectando a tailnet (hostname=$TS_HOSTNAME, SSH habilitado)"
TS_UP_ARGS=(--ssh --hostname="$TS_HOSTNAME" --accept-routes)

if [[ -n "${TS_AUTHKEY:-}" ]]; then
  tailscale up --authkey="$TS_AUTHKEY" "${TS_UP_ARGS[@]}"
  ok "Autenticado via TS_AUTHKEY"
else
  warn "TS_AUTHKEY nao definida — autenticacao interativa"
  warn "Copie a URL que aparecer e abra no navegador para autorizar a maquina"
  tailscale up "${TS_UP_ARGS[@]}"
fi

log "4/4 Status final"
tailscale status || true
TS_IP=$(tailscale ip -4 2>/dev/null | head -n1 || echo "(sem IP)")

cat <<EOF

============================================================
  Tailscale ativo nesta VPS
============================================================

  Hostname na tailnet:  $TS_HOSTNAME
  IP IPv4 da tailnet:   $TS_IP

Proximos passos no SEU LAPTOP/CELULAR:

  1. Instale Tailscale com a MESMA conta usada para autenticar a VPS:
       https://tailscale.com/download

  2. Confirme a maquina aparece no admin:
       https://login.tailscale.com/admin/machines

  3. SSH privado (sem IP publico exposto):
       ssh root@$TS_HOSTNAME
       # ou: ssh root@$TS_IP

  4. Rodar a CLI do CRM remotamente:
       ssh root@$TS_HOSTNAME 'bash /opt/casa-ludic-crm/deploy/cli.sh'

OPCIONAL — fechar SSH publico (so via tailnet):

  Faca APENAS depois de confirmar que ssh root@$TS_HOSTNAME funciona,
  caso contrario voce pode se trancar fora da VPS.

      ufw delete allow OpenSSH
      ufw allow in on tailscale0 to any port 22 proto tcp
      ufw reload
EOF
