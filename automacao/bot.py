"""Bot do Telegram: recebe vídeos e pedidos, mostra prévias com botões, responde comandos."""
from __future__ import annotations

import asyncio
import html
import re
from datetime import datetime, time as dtime
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from .config import Config
from .servico import Botao, Servico

AJUDA = (
    "Mande o <b>vídeo bruto</b> com uma legenda dizendo o <b>modelo</b> e <b>quando publicar</b>.\n"
    "Ex.: <i>capa-fala, postar quinta 19h</i>\n\n"
    "Comandos:\n/fila: jobs em andamento\n/modelos: modelos disponíveis\n/cancelar N: descarta o job N\n"
    "/refazer N: tenta de novo um job com erro\n/status: verifica o sistema\n/id: mostra seu ID"
)


def _html(msg: str) -> str:
    """Escapa HTML e converte **negrito** (usado pelo serviço) para <b>."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html.escape(msg))


def _teclado(botoes: list[Botao] | None):
    if not botoes:
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton(b.texto, callback_data=b.dado) for b in botoes]])


class NotificadorTelegram:
    def __init__(self, app: Application):
        self.app = app

    async def texto(self, chat_id: int, msg: str, botoes: list[Botao] | None = None) -> None:
        await self.app.bot.send_message(chat_id, _html(msg)[:4096], parse_mode=ParseMode.HTML,
                                        reply_markup=_teclado(botoes))

    async def video(self, chat_id: int, arquivo: Path, legenda: str, botoes: list[Botao] | None = None) -> None:
        with open(arquivo, "rb") as f:
            await self.app.bot.send_video(chat_id, f, caption=_html(legenda)[:1024], parse_mode=ParseMode.HTML,
                                          reply_markup=_teclado(botoes), supports_streaming=True,
                                          read_timeout=600, write_timeout=600)

    async def foto(self, chat_id: int, arquivo: Path, legenda: str = "") -> None:
        with open(arquivo, "rb") as f:
            await self.app.bot.send_photo(chat_id, f, caption=_html(legenda)[:1024], parse_mode=ParseMode.HTML)


class Bot:
    def __init__(self, cfg: Config, criar_servico):
        """criar_servico(notificador) -> Servico (o serviço precisa do notificador, que precisa do app)."""
        self.cfg = cfg
        b = ApplicationBuilder().token(cfg.telegram_token).concurrent_updates(True)
        if cfg.telegram_api_url:  # Bot API local: arquivos de até 2 GB
            b = (b.base_url(f"{cfg.telegram_api_url}/bot").base_file_url(f"{cfg.telegram_api_url}/file/bot")
                 .local_mode(True))
        b = b.read_timeout(120).write_timeout(600).media_write_timeout(600).post_init(self._iniciar)
        self.app = b.build()
        self.servico: Servico = criar_servico(NotificadorTelegram(self.app))
        self._parar = asyncio.Event()
        self._tarefas: list[asyncio.Task] = []
        a = self.app
        a.add_handler(CommandHandler(["start", "ajuda", "help"], self.cmd_start))
        a.add_handler(CommandHandler("id", self.cmd_id))
        a.add_handler(CommandHandler("fila", self.cmd_fila))
        a.add_handler(CommandHandler("modelos", self.cmd_modelos))
        a.add_handler(CommandHandler("cancelar", self.cmd_cancelar))
        a.add_handler(CommandHandler("refazer", self.cmd_refazer))
        a.add_handler(CommandHandler("status", self.cmd_status))
        a.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, self.on_video))
        a.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_texto))
        a.add_handler(CallbackQueryHandler(self.on_botao))

    # ---------------------------------------------------------------- ciclo de vida
    async def _iniciar(self, app: Application):
        s = self.servico
        self._tarefas = [asyncio.create_task(s.loop_edicao(self._parar)),
                         asyncio.create_task(s.loop_agendador(self._parar))]
        if self.cfg.chat_avisos:
            app.job_queue.run_daily(self._heartbeat, dtime(hour=self.cfg.hora_heartbeat, tzinfo=self.cfg.tz))
            await s.n.texto(self.cfg.chat_avisos, "🟢 Sistema iniciado." + (" [MODO ENSAIO]" if self.cfg.modo_ensaio else ""))

    async def _heartbeat(self, ctx: ContextTypes.DEFAULT_TYPE):
        await self.servico.n.texto(self.cfg.chat_avisos, "🟢 Estou no ar. Fila:\n" + self.servico.resumo_fila())

    def rodar(self):
        self.app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)

    # ---------------------------------------------------------------- utilidades
    def _autorizado(self, update: Update) -> bool:
        u = update.effective_user
        return bool(u and u.id in self.cfg.usuarios_autorizados)

    async def _negar(self, update: Update):
        uid = update.effective_user.id if update.effective_user else "?"
        if update.effective_message:
            await update.effective_message.reply_text(
                f"Este bot é privado. Seu ID é {uid}: peça para liberarem esse número.")

    # ---------------------------------------------------------------- handlers
    async def cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        await update.effective_message.reply_html(AJUDA)

    async def cmd_id(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        await update.effective_message.reply_text(f"Seu ID: {update.effective_user.id}")

    async def cmd_fila(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        await update.effective_message.reply_text(self.servico.resumo_fila())

    async def cmd_modelos(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        from .interpretar import catalogo
        await update.effective_message.reply_text(catalogo())

    async def _com_id(self, update: Update, ctx) -> int | None:
        if not ctx.args or not ctx.args[0].isdigit():
            await update.effective_message.reply_text("Informe o número do job, ex.: /cancelar 12")
            return None
        return int(ctx.args[0])

    async def cmd_cancelar(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        if (jid := await self._com_id(update, ctx)) is not None:
            await self.servico.descartar(jid)

    async def cmd_refazer(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        if (jid := await self._com_id(update, ctx)) is not None:
            job = await self.servico.refazer(jid)
            await update.effective_message.reply_text(
                f"🔁 Job #{jid} voltou para a fila." if job and job.estado == "na_fila" else "Esse job não está com erro.")

    async def cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        linhas = [f"Modo: {'ENSAIO (não publica)' if self.cfg.modo_ensaio else 'PRODUÇÃO'}",
                  f"Editor: {type(self.servico.editor).__name__}"]
        pub = self.servico.pub
        if pub is not None and hasattr(pub, "verificar"):
            try:
                conta = await asyncio.to_thread(pub.verificar)
                linhas.append(f"Instagram: conectado como @{conta}")
            except Exception as e:  # noqa: BLE001
                linhas.append(f"Instagram: ERRO ({e})")
        linhas += [f"Problema: {p}" for p in self.cfg.problemas()]
        await update.effective_message.reply_text("\n".join(linhas))

    async def on_video(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        msg = update.effective_message
        anexo = msg.video or msg.document
        if not self.cfg.telegram_api_url and (anexo.file_size or 0) > 20 * 1024 * 1024:
            return await msg.reply_text("Esse vídeo passa de 20 MB, o limite do Telegram sem o servidor local "
                                        "(TELEGRAM_API_URL). Configure o Bot API local ou mande um arquivo menor.")
        await msg.reply_text("📥 Recebendo o vídeo…")
        arq = await anexo.get_file()
        entrada = self.cfg.dados / "entrada"
        entrada.mkdir(parents=True, exist_ok=True)
        nome = getattr(anexo, "file_name", None) or f"{anexo.file_unique_id}.mp4"
        destino = entrada / f"{datetime.now():%Y%m%d_%H%M%S}_{Path(nome).name}"
        await arq.download_to_drive(destino)
        await self.servico.novo_pedido(msg.chat_id, destino, msg.caption or "")

    async def on_texto(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._autorizado(update):
            return await self._negar(update)
        chat, texto = update.effective_chat.id, update.effective_message.text
        if await self.servico.receber_ajuste(chat, texto):
            return
        if await self.servico.responder_info(chat, texto):
            return
        await update.effective_message.reply_html("Para começar, mande um vídeo. " + AJUDA)

    async def on_botao(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        if not self._autorizado(update):
            await q.answer("Sem permissão.")
            return
        await q.answer()
        acao, _, jid = (q.data or "").partition(":")
        if not jid.isdigit():
            return
        jid = int(jid)
        try:
            await q.edit_message_reply_markup(reply_markup=None)  # evita clique duplo
        except Exception:  # noqa: BLE001
            pass
        if acao == "aprovar":
            await self.servico.aprovar(jid)
        elif acao == "descartar":
            await self.servico.descartar(jid)
        elif acao == "ajustar":
            await self.servico.iniciar_ajuste(update.effective_chat.id, jid)
