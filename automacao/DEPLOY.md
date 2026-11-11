# Automação: instalar, testar e migrar

Fluxo da etapa 1: o Dr. Clayton manda o **vídeo bruto no Telegram** com o pedido ("capa-fala, postar quinta 19h") → o agente edita → chega a **prévia com botões** (Aprovar / Ajustar / Descartar) → no horário, o Reels é **publicado no Instagram** e o bot avisa com o link.

Tudo roda em Docker: o mesmo `docker compose up -d` funciona no **PC do Instituto** e num **servidor na nuvem**. O estado fica só em `dados/` (fila e vídeos) e `automacao/.env` (credenciais). Por isso migrar é copiar essas duas coisas.

---

## 1. O que providenciar antes (uma vez)

### Telegram
1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome e @ → copie o **token** para `TELEGRAM_TOKEN`.
2. Em **https://my.telegram.org** → *API development tools* → crie um app → copie **api_id** e **api_hash** para `TELEGRAM_API_ID` / `TELEGRAM_API_HASH`. Isso habilita o servidor local da Bot API, que aceita vídeos de até 2 GB (sem ele o limite é 20 MB).
3. **Cada pessoa autorizada precisa abrir o bot no Telegram e tocar em "Iniciar" uma vez.** O Telegram não deixa um bot mandar a primeira mensagem.
4. IDs autorizados: depois de subir o sistema, quem mandar `/id` ao bot recebe o próprio número. Coloque os números do Dr. Clayton e o seu em `TELEGRAM_USUARIOS`, separados por vírgula, e reinicie. Qualquer outra pessoa é recusada.

### Anthropic (o "cérebro" da edição)
- Em **https://console.anthropic.com**: crie a conta, ative a cobrança e gere uma **API key** → `ANTHROPIC_API_KEY`.
- Custo estimado: ~US$0,50–1,10 por vídeo com Opus 5.5. `TETO_USD_POR_JOB` limita o gasto máximo por vídeo (padrão US$3).
- Dica: em *Limits*, defina um teto mensal no console também.

### Instagram (API oficial da Meta)
1. O Instagram do Dr. Clayton precisa ser **conta profissional** (Empresa ou Criador de conteúdo) e estar **vinculado a uma Página do Facebook**.
2. Em **https://business.facebook.com** (Gerenciador de Negócios), adicione a Página e a conta do Instagram aos ativos da empresa.
3. Em **https://developers.facebook.com** → *Criar app* (tipo **Empresa**) → adicione o produto **Instagram** (API com login do Facebook).
4. No Gerenciador de Negócios → *Usuários do sistema* → crie um usuário do sistema (Admin), atribua a Página, a conta do Instagram e o app, e **gere um token** com as permissões `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement` e `business_management`. Tokens de usuário do sistema **não expiram**. Copie para `IG_TOKEN`.
5. Descubra o `IG_USER_ID` (troque `TOKEN`):
   ```bash
   curl "https://graph.facebook.com/v23.0/me/accounts?fields=name,instagram_business_account&access_token=TOKEN"
   ```
   O número em `instagram_business_account.id` é o `IG_USER_ID`.
6. Se a Meta pedir revisão do app para `instagram_content_publish`, siga o formulário dela. Para publicar na própria conta da empresa, o acesso padrão costuma bastar.

---

## 2. Instalar no PC do Instituto (Windows)

1. Instale o **Docker Desktop** (https://www.docker.com/products/docker-desktop) com a opção **WSL 2** e, nas configurações, marque **"Start Docker Desktop when you sign in"**.
2. Instale o **Git** (https://git-scm.com) e, no PowerShell:
   ```powershell
   git clone https://github.com/MatheusCOM/editor-de-video.git C:\editor-de-video
   ```
   ```powershell
   cd C:\editor-de-video\automacao
   ```
   ```powershell
   copy .env.exemplo .env
   ```
3. Abra o `.env` no Bloco de Notas e preencha (deixe `MODO_ENSAIO=1` no começo).
4. Suba tudo (a primeira vez demora ~10–15 min para montar a imagem):
   ```powershell
   docker compose up -d --build
   ```
5. Veja se está rodando:
   ```powershell
   docker compose logs -f editor
   ```
   Deve aparecer `[inicio] modo ENSAIO`, e o bot manda "🟢 Sistema iniciado" no Telegram.

### Para o PC não "dormir" nem ficar fora do ar
- **Energia**: Configurações → Sistema → Energia → *Suspender* = **Nunca**; desative a hibernação (`powercfg /h off` no PowerShell como administrador).
- **Login automático do Windows** (o Docker Desktop só sobe após o login) ou um usuário dedicado que fica logado.
- **Queda de energia**: na BIOS/UEFI, ative *Restore on AC Power Loss = Power On*, para o PC religar sozinho. Um nobreak ajuda.
- **Atualizações do Windows**: defina *horário ativo* para não reiniciar no horário de publicação.
- O bot manda **todo dia às 9h** um "🟢 Estou no ar" com a fila. Se não chegar, o sistema caiu.

---

## 3. Testar com segurança

1. No Telegram: `/start` e `/status` (mostra o modo, o editor, a conexão com o Instagram e o que falta configurar).
2. Mande um vídeo curto com a legenda `capa-fala, postar hoje 18h` (ou `assim que aprovar`).
3. Acompanhe: o bot confirma o pedido → "Editando…" → manda o vídeo pronto com os botões. Teste **Ajustar** (escreva o pedido de ajuste) e depois **Aprovar**.
4. Em `MODO_ENSAIO=1`, no horário marcado ele avisa "[ENSAIO] seria publicado agora" e **não publica**.
5. Quando estiver tudo certo: troque para `MODO_ENSAIO=0` no `.env` e rode `docker compose up -d` de novo.

Comandos do bot: `/fila`, `/modelos`, `/cancelar N`, `/refazer N` (job com erro), `/status`, `/id`.

---

## 4. Migrar do PC para a nuvem

Servidor recomendado: **Hetzner CPX31** (4 vCPU, 8 GB, ~€15/mês) com **Ubuntu 24.04**. Qualquer VPS Linux com 4 vCPU e 8 GB serve.

1. **No servidor** (via SSH), instale o Docker e baixe o projeto:
   ```bash
   curl -fsSL https://get.docker.com | sh
   ```
   ```bash
   git clone https://github.com/MatheusCOM/editor-de-video.git ~/editor-de-video
   ```
2. **No PC do Instituto** (Git Bash ou WSL, na pasta do projeto), empacote o estado. Isso para o editor antes, para a fila ficar consistente:
   ```bash
   bash automacao/migrar.sh exportar
   ```
   Copie o `.tar.gz` gerado para o servidor:
   ```bash
   scp editor-estado-*.tar.gz usuario@IP_DO_SERVIDOR:~/editor-de-video/
   ```
3. **No servidor**:
   ```bash
   cd ~/editor-de-video && bash automacao/migrar.sh importar editor-estado-*.tar.gz
   ```
   ```bash
   cd automacao && docker compose up -d --build
   ```
4. Confira no Telegram (`/status`, `/fila`). Os jobs agendados continuam de onde pararam.
5. **Desligue no PC** (dois bots com o mesmo token brigam pelas mensagens):
   ```powershell
   docker compose down
   ```

---

## 5. Backup

O que importa está em `dados/` e no `.env`. No servidor, um backup diário às 3h:
```bash
(crontab -l 2>/dev/null; echo "0 3 * * * tar czf ~/backup-editor-\$(date +\%u).tar.gz -C ~/editor-de-video dados automacao/.env") | crontab -
```
Isso guarda 7 cópias rotativas (uma por dia da semana). Leve uma cópia para fora do servidor de vez em quando.

---

## 6. Problemas comuns

| Sintoma | Causa provável / solução |
|---|---|
| Bot não responde | `docker compose logs editor`. Confira `TELEGRAM_TOKEN` e se o seu ID está em `TELEGRAM_USUARIOS` (o bot diz o ID de quem não está autorizado). |
| "passa de 20 MB" | O servidor local da Bot API não está ativo: confira `TELEGRAM_API_ID`/`HASH` e `docker compose ps`. |
| Edição falha | `/fila` mostra o erro. Verifique `ANTHROPIC_API_KEY` e o saldo. `/refazer N` tenta de novo. |
| Publicação falha | `/status` testa o token. O sistema tenta 3 vezes (10 e 20 min depois) e avisa. Token expirado: gere outro de usuário do sistema. |
| Log mostra "Chat not found" | A pessoa ainda não abriu o bot e tocou em **Iniciar**, ou o ID em `TELEGRAM_USUARIOS` está errado (use o número do @userinfobot, não o do token). |
| "Não consegui ler o vídeo: falta permissão" | O editor precisa estar no grupo do servidor do Telegram (`group_add: ["101"]` no `docker-compose.yml`). Se a imagem do servidor mudar de grupo, descubra o número com `docker compose exec telegram-bot-api id` e ajuste. |
| PC reiniciou | O Docker Desktop sobe no login e o compose religa sozinho (`restart: unless-stopped`). Jobs que estavam no meio voltam para a fila. |
