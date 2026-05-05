# Guia completo — Tailscale para acesso admin do Casa Ludic CRM

**Para quem nunca usou VPN.** Este guia te leva do zero até conseguir acessar a sua VPS pelo notebook, em rede privada, sem expor portas pra internet pública.

---

## O que é isso e por que estamos fazendo

Sua VPS (servidor na nuvem) tem um IP público. Qualquer pessoa do mundo pode tentar se conectar nela — robôs varrem a internet 24h tentando senhas. O `setup_vps.sh` já fechou tudo menos a porta 22 (SSH), o que reduz o risco, mas não elimina.

**Tailscale** cria uma "rede privada virtual" (VPN) entre os seus dispositivos. Você instala em todo aparelho que precisa acessar o CRM (notebook, celular, e a própria VPS), e eles se enxergam por IPs privados (`100.x.x.x`) que **só existem dentro dessa rede**. Pra qualquer um de fora, é como se a VPS não existisse.

**O que muda na prática:**

- Você vai conseguir digitar `ssh root@casa-ludic-vps` no terminal, sem decorar IP.
- Ninguém de fora consegue se conectar — só seus dispositivos autorizados.
- Funciona em qualquer lugar (casa, café, celular 4G), o Tailscale acha o caminho sozinho.
- É **grátis** até 100 dispositivos (você usará 2-3).

**Tempo estimado:** 15 minutos.

---

## Pré-requisitos

Antes de começar, você precisa ter:

- [ ] Uma VPS rodando Ubuntu 22.04 (ex: Hetzner, DigitalOcean, AWS Lightsail)
- [ ] O IP público da sua VPS (algo tipo `203.0.113.45`) — o provedor te mostrou ao criar
- [ ] A senha de root da VPS, OU uma chave SSH configurada
- [ ] O `setup_vps.sh` já rodado na VPS (o `setup_tailscale.sh` depende do UFW estar instalado)
- [ ] Uma conta Google ou Microsoft (vai ser o login do Tailscale — não precisa criar senha nova)
- [ ] Seu notebook com Windows, Mac ou Linux

Se algum item está faltando, pare aqui e resolva antes de continuar. Sem a VPS provisionada, os passos abaixo não funcionam.

---

## Visão geral dos passos

```
┌─────────────────────────────────────────────────────────┐
│  1. Criar conta no Tailscale (1 min)                     │
│  2. Instalar Tailscale no SEU NOTEBOOK (2 min)           │
│  3. Conectar no SSH da VPS via IP público (1 min)        │
│  4. Rodar setup_tailscale.sh na VPS (3 min)              │
│  5. Autorizar a VPS no Tailscale (abrir URL) (1 min)     │
│  6. Testar SSH pelo nome `casa-ludic-vps` (1 min)        │
│  7. (Opcional) Fechar SSH público (1 min)                │
└─────────────────────────────────────────────────────────┘
```

---

## Passo 1 — Criar conta no Tailscale

1. Abra no navegador: <https://login.tailscale.com/start>

2. Você verá quatro botões grandes: **Google**, **Microsoft**, **Apple**, **GitHub**.

   > **Importante:** lembre qual escolheu. Você vai usar o MESMO login no notebook e na VPS — é assim que o Tailscale sabe que ambos pertencem a você.

3. Clique no que preferir, faça login normalmente.

4. O Tailscale vai te perguntar o nome da sua "tailnet" (sua rede privada). Pode aceitar o que ele sugere, é só um identificador interno.

5. **Pode aparecer um questionário** ("Help us better understand your product needs"). É só pesquisa de marketing, não afeta nada técnico. Responda assim:

   - **Primary reason:** `Infrastructure Access`
   - **Role:** `IT` ou `Developer` ou `Founder / Owner` (NÃO escolha Sales/Marketing — desvia o conteúdo)
   - **VPN provider:** marque `I don't use a VPN`
   - **How did you hear:** opcional, pode pular

   Depois clique em **Next: Add your first device**.

6. **A próxima tela do onboarding tenta te guiar pra instalar Tailscale numa máquina.** Você pode **fechar a aba** e ir direto pra <https://login.tailscale.com/admin/machines> — nosso guia segue uma ordem específica (notebook primeiro, VPS depois) que casa com o `setup_tailscale.sh`.

7. Você cai na tela **Machines** (Máquinas). Está vazia. É esperado — vamos popular nos próximos passos.

> ✅ **Checkpoint:** você consegue ver a página <https://login.tailscale.com/admin/machines>, ainda sem nenhuma máquina listada.

---

## Passo 2 — Instalar Tailscale no seu notebook

### Windows

1. Vá em <https://tailscale.com/download/windows>
2. Clique em **Download Tailscale for Windows**.
3. Abra o `.msi` baixado, clique em **Next** → **Install** → **Finish**.
4. Vai aparecer um ícone do Tailscale na bandeja (canto inferior direito, perto do relógio). Clique nele.
5. Vai abrir o navegador pedindo login — use **a mesma conta** do Passo 1.
6. Autorize.

### Mac

1. Vá em <https://tailscale.com/download/mac>
2. Instale via App Store (recomendado) ou baixe o `.pkg`.
3. Abra o app, clique em **Log in**, use a mesma conta do Passo 1.

### Linux

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Vai imprimir uma URL — abra no navegador e autorize.
```

### Verificação

Volte na página <https://login.tailscale.com/admin/machines>. Atualize. Agora deve aparecer **uma máquina** com o nome do seu computador (ex: `notebook-gilney`) e um IP `100.x.x.x`.

> ✅ **Checkpoint:** seu notebook aparece na lista de Machines com status "Connected" (verde).

---

## Passo 3 — Conectar no SSH da VPS (pela última vez via IP público)

Esta é a única vez que você vai usar o IP público diretamente. Depois disso, vamos pelo Tailscale.

### No Windows (PowerShell)

Abra o PowerShell e digite:

```powershell
ssh root@SEU_IP_PUBLICO
```

Substitua `SEU_IP_PUBLICO` pelo IP real (ex: `ssh root@203.0.113.45`).

### No Mac/Linux

Mesmo comando, no Terminal:

```bash
ssh root@SEU_IP_PUBLICO
```

### O que esperar

- **Primeira conexão:** pergunta `Are you sure you want to continue connecting (yes/no)?` — digite `yes` e Enter.
- **Senha:** vai pedir a senha de root (mesma que o provedor enviou por email, ou que você definiu ao criar a VPS). Digite — **não vai aparecer nada na tela enquanto você digita**, isso é normal, é segurança. Aperte Enter no final.
- Se deu certo, você vê algo como `root@casa-ludic-vps:~#` — você está dentro da VPS.

### Se der erro

| Erro | O que significa | Solução |
|---|---|---|
| `Connection refused` | SSH não está rodando ou firewall bloqueou | Confira no painel do provedor que a VPS está "Running"; verifique se rodou `setup_vps.sh` |
| `Permission denied (publickey,password)` | Senha errada, ou só aceita chave SSH | Use a senha exata do email do provedor; ou configure chave SSH no painel |
| `Host key verification failed` | Você se conectou nesse IP antes com outra máquina | Rode `ssh-keygen -R SEU_IP_PUBLICO` e tente de novo |

> ✅ **Checkpoint:** você está logado na VPS, vê o prompt `root@...:~#`.

---

## Passo 4 — Rodar `setup_tailscale.sh` na VPS

**Ainda dentro do SSH** (não saia), digite:

```bash
sudo bash /opt/casa-ludic-crm/deploy/setup_tailscale.sh
```

Isto faz, na ordem:

1. **Instala o Tailscale** (baixa via script oficial). Dura ~30 segundos.
2. **Libera a interface `tailscale0` no firewall UFW**. Instantâneo.
3. **Conecta na sua tailnet**. Aqui ele vai imprimir uma **URL longa** parecida com:

   ```
   To authenticate, visit:
   https://login.tailscale.com/a/abc123def456...
   ```

4. **PARE.** Não saia do SSH. Vá para o próximo passo com essa URL na tela.

> ⚠️ Se o terminal travou esperando, é normal — está aguardando você autorizar.

---

## Passo 5 — Autorizar a VPS

1. **Selecione a URL** com o mouse no terminal e copie (no PowerShell: clique direito copia automaticamente).

2. Cole no navegador (no notebook). Vai abrir uma página do Tailscale dizendo algo tipo:

   ```
   Connect casa-ludic-vps to your tailnet?
   ```

3. Confirme que está logado com a mesma conta do Passo 1 (canto superior direito da página).

4. Clique em **Connect**.

5. Volte ao terminal SSH. Em alguns segundos, ele vai imprimir o status final, algo como:

   ```
   ============================================================
     Tailscale ativo nesta VPS
   ============================================================

     Hostname na tailnet:  casa-ludic-vps
     IP IPv4 da tailnet:   100.64.12.34
   ```

6. **Anote esse IP `100.64.x.x`** — você não vai precisar dele com frequência (vamos usar o nome `casa-ludic-vps`), mas serve de fallback.

> ✅ **Checkpoint:** volte em <https://login.tailscale.com/admin/machines>. Agora você tem **DUAS máquinas**: o notebook e `casa-ludic-vps`, ambas verdes/conectadas.

---

## Passo 6 — Testar SSH pelo Tailscale

1. **Saia do SSH atual** digitando `exit` e Enter. Você volta ao PowerShell/Terminal do notebook.

2. Conecte de novo, agora **pelo nome**:

   ```bash
   ssh root@casa-ludic-vps
   ```

3. Não precisa do IP público, não precisa decorar nada. O Tailscale resolve o nome internamente.

4. **Bônus — sem senha:** o `setup_tailscale.sh` ativou o **Tailscale SSH**, que autentica via Tailscale ao invés de senha. Pode ser que ele conecte direto sem pedir senha (depende da configuração da sua tailnet). Se pedir senha, é a mesma de root.

### Se não funcionar

| Problema | Solução |
|---|---|
| `Could not resolve hostname casa-ludic-vps` | Tailscale não está rodando no notebook. Abra o ícone na bandeja, confira se está "Connected". |
| `Connection timed out` | A VPS pode estar offline ou o Tailscale dela parou. SSH pelo IP público e rode `tailscale status` na VPS. |
| Pede senha mas não aceita | Use a senha de root original. O Tailscale SSH às vezes precisa de configuração extra no admin (ACLs). |

> ✅ **Checkpoint:** você acessou a VPS digitando só `ssh root@casa-ludic-vps`. Agora você está em rede privada de verdade.

---

## Passo 7 — (Opcional, recomendado depois) Fechar SSH público

**Só faça isto depois de confirmar pelo menos UMA semana que o Tailscale funciona pra você.** Se o Tailscale falhar enquanto o SSH público estiver fechado, você se trancou pra fora e precisa abrir um chamado no provedor pra resetar.

Quando estiver confiante, dentro da VPS (via Tailscale):

```bash
# Permite SSH SÓ pelo Tailscale:
sudo ufw allow in on tailscale0 to any port 22 proto tcp

# Remove a regra que liberava SSH público:
sudo ufw delete allow OpenSSH

# Recarrega:
sudo ufw reload

# Confere:
sudo ufw status verbose
```

A saída deve mostrar regras só pra `tailscale0`, sem `OpenSSH (v6)/Anywhere`.

A partir daí, sua VPS literalmente não tem nenhuma porta exposta pra internet pública. Bots de scan vão ver "host unreachable" e ir embora.

---

## Uso no dia a dia

Depois de tudo configurado, sua rotina é:

```bash
# Acessar a CLI do CRM:
ssh root@casa-ludic-vps 'bash /opt/casa-ludic-crm/deploy/cli.sh'

# Ver logs do scheduler:
ssh root@casa-ludic-vps 'docker compose -f /opt/casa-ludic-crm/docker-compose.yml logs -f --tail=50'

# Editar config:
ssh root@casa-ludic-vps 'nano /opt/casa-ludic-crm/.env'

# Atualizar código depois de push no GitHub:
ssh root@casa-ludic-vps 'cd /opt/casa-ludic-crm && git pull && docker compose up -d --build'
```

Você pode abrir várias abas do PowerShell, cada uma com uma sessão SSH. Não tem limite.

---

## Adicionar mais dispositivos

Se quiser acessar do celular ou outro notebook:

1. Instale Tailscale no aparelho (App Store / Play Store / site oficial).
2. Login com **a mesma conta** do Passo 1.
3. Pronto — esse aparelho já enxerga `casa-ludic-vps`.

No celular Android você pode usar apps como **Termius** ou **JuiceSSH** pra conectar via `ssh root@casa-ludic-vps`. No iPhone, **Termius** ou **Blink Shell**.

---

## Troubleshooting comum

### "Eu desliguei o notebook e não consigo mais acessar a VPS"

O Tailscale do notebook precisa estar rodando. Em Windows, abra o ícone na bandeja → "Connected". Em Mac, ícone na barra de menu superior. Se sumiu, reinstale.

### "Trocou o IP da VPS, perdi acesso"

Não importa: o Tailscale usa o nome `casa-ludic-vps`, não o IP público. O IP `100.x.x.x` da tailnet é estável mesmo se o IP público mudar. Pode ignorar o IP público pra sempre.

### "Aparece duplicado no admin Tailscale"

Se reinstalar, pode criar uma entrada nova. Vá em <https://login.tailscale.com/admin/machines>, identifique a velha pelo "Last Seen" mais antigo e clique nos três pontinhos → **Remove**.

### "Quero revogar acesso a um aparelho perdido"

Mesmo lugar: <https://login.tailscale.com/admin/machines> → três pontinhos → **Remove**. O aparelho perde acesso na hora.

### "Tailscale parou de funcionar na VPS depois de reboot"

Não deveria, ele é serviço systemd. Mas se acontecer, SSH público (se ainda estiver aberto) ou console do provedor:

```bash
sudo systemctl status tailscaled
sudo systemctl restart tailscaled
sudo tailscale up
```

### "Quero usar com a CLI sem digitar `ssh root@casa-ludic-vps` toda vez"

No seu `~/.ssh/config` (ou `C:\Users\seu-user\.ssh\config` no Windows), adicione:

```
Host ludic
    HostName casa-ludic-vps
    User root
```

Daí basta digitar `ssh ludic`.

---

## Custos

- **Tailscale Free:** 100 dispositivos, 3 usuários. Suficiente pra Casa Ludic — você é 1 usuário, com 2-3 dispositivos.
- **Não há custo na VPS:** Tailscale consome ~30MB de RAM e tráfego desprezível.

---

## Onde aprender mais (opcional)

- Documentação oficial: <https://tailscale.com/kb>
- Comandos do CLI: na VPS rode `tailscale --help`
- Status da rede: `tailscale status` (mostra todos os peers e latência)

---

**Dúvidas?** Volta nesse chat dizendo onde travou e eu desbloqueio.
