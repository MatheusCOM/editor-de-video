"""Regras do fluxo (independente do Telegram, para dar para testar tudo com simulações).

pedido → (pergunta o que faltar) → fila → edição pelo agente → prévia com botões →
aprovar | ajustar | descartar → agendado → publicado no horário (ou "publicaria" em modo ensaio).
"""
from __future__ import annotations

import asyncio
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from .config import Config
from .fila import Fila, Job, agora_utc
from .interpretar import DIAS, Pedido, interpretar, list_brands, list_templates


@dataclass
class Botao:
    texto: str
    dado: str  # callback_data, ex.: "aprovar:12"


class Notificador(Protocol):
    async def texto(self, chat_id: int, msg: str, botoes: list[Botao] | None = None) -> None: ...
    async def video(self, chat_id: int, arquivo: Path, legenda: str, botoes: list[Botao] | None = None) -> None: ...
    async def foto(self, chat_id: int, arquivo: Path, legenda: str = "") -> None: ...


class Publicador(Protocol):
    def publicar_reel(self, arquivo: Path, legenda: str): ...


def fmt_quando(dt: datetime | None, cfg: Config) -> str:
    if not dt:
        return "assim que aprovado"
    loc = dt.astimezone(cfg.tz)
    return f"{DIAS[loc.weekday()]} {loc:%d/%m às %H:%M}"


def botoes_aprovacao(job_id: int) -> list[Botao]:
    return [Botao("✅ Aprovar", f"aprovar:{job_id}"), Botao("✏️ Ajustar", f"ajustar:{job_id}"),
            Botao("🗑 Descartar", f"descartar:{job_id}")]


class Servico:
    def __init__(self, cfg: Config, fila: Fila, editor, notificador: Notificador, publicador: Publicador | None,
                 cliente_ia=None):
        self.cfg, self.fila, self.editor, self.n, self.pub, self.ia = cfg, fila, editor, notificador, publicador, cliente_ia
        self._trabalho = asyncio.Event()
        self._aguardando_ajuste: dict[int, int] = {}  # chat_id → job_id que espera o texto do ajuste

    # ---------------------------------------------------------------- pedidos
    def _pasta(self, job: Job) -> Path:
        return self.cfg.jobs_dir / job.pasta

    def _aplicar_pedido(self, job: Job, p: Pedido) -> Job:
        campos = {}
        if p.modelo:
            campos["modelo"] = p.modelo
        if p.marca:
            campos["marca"] = p.marca
        if p.publicar_em:
            campos["publicar_em"] = p.publicar_em.astimezone().isoformat()
        if p.publicar_agora:
            campos["extra"] = {**job.extra, "publicar_agora": True}
        if p.observacoes:
            campos["observacoes"] = (job.observacoes + " " + p.observacoes).strip()
        return self.fila.atualizar(job.id, **campos) if campos else job

    def _falta(self, job: Job) -> list[str]:
        f = []
        if not job.modelo:
            f.append("modelo")
        if not job.marca:
            f.append("marca")
        if not job.publicar_em and not job.extra.get("publicar_agora"):
            f.append("data")
        return f

    async def _perguntar(self, job: Job, falta: list[str]):
        partes = []
        if "modelo" in falta:
            partes.append("qual **modelo**? " + " · ".join(list_templates()))
        if "marca" in falta:
            partes.append("qual **marca**? " + " · ".join(list_brands()))
        if "data" in falta:
            partes.append("**quando publicar**? (ex.: \"quinta 19h\", \"amanhã 12h30\" ou \"assim que aprovar\")")
        await self.n.texto(job.chat_id, f"Recebi o vídeo (job #{job.id}). Falta só: " + "; ".join(partes))

    async def novo_pedido(self, chat_id: int, bruto: Path, texto: str) -> Job:
        job = self.fila.criar(chat_id, pedido=texto)
        pasta = self._pasta(job)
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"bruto{bruto.suffix.lower() or '.mp4'}"
        shutil.move(str(bruto), destino)
        job = self.fila.atualizar(job.id, bruto=str(destino))
        if texto.strip():
            job = self._aplicar_pedido(job, self._interpretar(texto))
        return await self._seguir(job)

    async def responder_info(self, chat_id: int, texto: str) -> Job | None:
        job = self.fila.aguardando_info(chat_id)
        if not job:
            return None
        job = self.fila.atualizar(job.id, pedido=(job.pedido + " | " + texto).strip(" |"))
        job = self._aplicar_pedido(job, self._interpretar(texto))
        return await self._seguir(job)

    def _interpretar(self, texto: str) -> Pedido:
        return interpretar(texto, self.cfg.tz, self.cfg.marca_padrao, cliente=self.ia,
                           modelo_ia=self.cfg.modelo_interpretador)

    async def _seguir(self, job: Job) -> Job:
        falta = self._falta(job)
        if falta:
            job = self.fila.atualizar(job.id, estado="aguardando_info")
            await self._perguntar(job, falta)
            return job
        job = self.fila.atualizar(job.id, estado="na_fila")
        fila_antes = len([j for j in self.fila.listar(("na_fila", "ajustando", "editando")) if j.id != job.id])
        await self.n.texto(job.chat_id, (
            f"✅ Job #{job.id} na fila: modelo **{job.modelo}**, marca **{job.marca}**, publicar "
            f"{fmt_quando(job.publicar_em_dt(), self.cfg)}."
            + (f" Há {fila_antes} vídeo(s) antes dele." if fila_antes else " Começando a edição.")))
        self._trabalho.set()
        return job

    # ---------------------------------------------------------------- edição
    async def processar_proximo(self) -> Job | None:
        job = self.fila.proximo_para_editar()
        if not job:
            return None
        ajuste = job.estado == "ajustando"
        job = self.fila.atualizar(job.id, estado="editando", tentativas=job.tentativas + 1)
        pasta = self._pasta(job)
        try:
            if ajuste:
                r = await self.editor.ajustar(pasta, job.sessao_agente, job.extra.get("ajuste", ""))
            else:
                await self.n.texto(job.chat_id, f"🎬 Editando o job #{job.id}… (leva alguns minutos)")
                r = await self.editor.editar(pasta, Path(job.bruto), job.marca, job.modelo, job.observacoes)
        except Exception as e:  # noqa: BLE001
            msg = str(e)[:500]
            job = self.fila.atualizar(job.id, estado="erro", erro=msg)
            await self.n.texto(job.chat_id, f"⚠️ A edição do job #{job.id} falhou: {msg}\n"
                                            f"Use /refazer {job.id} para tentar de novo.")
            return job
        job = self.fila.atualizar(job.id, estado="aguardando_aprovacao", video_final=str(r.video_final),
                                  previa=str(r.previa) if r.previa else None, legenda=r.legenda,
                                  roteiro=r.roteiro_resumo, sessao_agente=r.sessao or job.sessao_agente,
                                  custo_usd=round(job.custo_usd + r.custo_usd, 4), erro="")
        pend = ("\n\n⚠️ Pendências:\n- " + "\n- ".join(r.pendencias)) if r.pendencias else ""
        texto = (f"Job #{job.id} pronto ({job.modelo}). Publicação: {fmt_quando(job.publicar_em_dt(), self.cfg)}.\n\n"
                 f"O que fiz:\n{r.roteiro_resumo}\n\nLegenda do post:\n{r.legenda}{pend}")
        await self.n.video(job.chat_id, r.video_final, texto[:1000], botoes_aprovacao(job.id))
        if len(texto) > 1000:
            await self.n.texto(job.chat_id, texto[1000:4000])
        return job

    async def loop_edicao(self, parar: asyncio.Event):
        while not parar.is_set():
            job = await self.processar_proximo()
            if job is None:
                self._trabalho.clear()
                try:
                    await asyncio.wait_for(self._trabalho.wait(), timeout=30)
                except asyncio.TimeoutError:
                    pass

    # ---------------------------------------------------------------- decisões do cliente
    async def aprovar(self, job_id: int) -> Job | None:
        job = self.fila.obter(job_id)
        if not job or job.estado != "aguardando_aprovacao":
            return job
        quando = job.publicar_em_dt()
        agora = agora_utc()
        if job.extra.get("publicar_agora") or not quando or quando < agora:
            quando = agora
        job = self.fila.atualizar(job.id, estado="agendado", publicar_em=quando.isoformat())
        aviso = " (o horário pedido já passou, então vai agora)" if job.publicar_em and not job.extra.get(
            "publicar_agora") and quando == agora else ""
        await self.n.texto(job.chat_id, f"👍 Aprovado. Job #{job.id} será publicado {fmt_quando(quando, self.cfg)}{aviso}."
                           + (" [MODO ENSAIO: não publica de verdade]" if self.cfg.modo_ensaio else ""))
        return job

    async def descartar(self, job_id: int) -> Job | None:
        job = self.fila.obter(job_id)
        if not job or job.estado in ("publicado", "publicando"):
            return job
        job = self.fila.atualizar(job.id, estado="descartado")
        await self.n.texto(job.chat_id, f"🗑 Job #{job.id} descartado.")
        return job

    async def iniciar_ajuste(self, chat_id: int, job_id: int):
        self._aguardando_ajuste[chat_id] = job_id
        await self.n.texto(chat_id, f"✏️ O que ajustar no job #{job_id}? Escreva em uma mensagem "
                                    "(ex.: \"legenda maior\", \"tira o texto do começo\", \"muda a legenda do post para…\").")

    async def receber_ajuste(self, chat_id: int, texto: str) -> Job | None:
        job_id = self._aguardando_ajuste.pop(chat_id, None)
        if job_id is None:
            return None
        job = self.fila.obter(job_id)
        if not job or job.estado not in ("aguardando_aprovacao", "agendado"):
            return job
        job = self.fila.atualizar(job.id, estado="ajustando", extra={**job.extra, "ajuste": texto})
        await self.n.texto(chat_id, f"🔁 Ajustando o job #{job.id}…")
        self._trabalho.set()
        return job

    async def refazer(self, job_id: int) -> Job | None:
        job = self.fila.obter(job_id)
        if not job or job.estado != "erro":
            return job
        job = self.fila.atualizar(job.id, estado="na_fila", erro="")
        self._trabalho.set()
        return job

    # ---------------------------------------------------------------- publicação
    async def publicar_vencidos(self, agora: datetime | None = None) -> list[Job]:
        feitos = []
        for job in self.fila.vencidos(agora or agora_utc()):
            job = self.fila.atualizar(job.id, estado="publicando")
            if self.cfg.modo_ensaio or self.pub is None:
                job = self.fila.atualizar(job.id, estado="publicado", permalink="(ensaio)")
                await self.n.texto(job.chat_id, f"🧪 [ENSAIO] Job #{job.id} seria publicado agora no Instagram.")
                feitos.append(job)
                continue
            try:
                res = await asyncio.to_thread(self.pub.publicar_reel, Path(job.video_final), job.legenda)
            except Exception as e:  # noqa: BLE001
                tent = job.extra.get("tentativas_pub", 0) + 1
                if tent < 3:
                    novo = agora_utc() + timedelta(minutes=10 * tent)
                    job = self.fila.atualizar(job.id, estado="agendado", publicar_em=novo.isoformat(),
                                              erro=str(e)[:500], extra={**job.extra, "tentativas_pub": tent})
                    await self.n.texto(job.chat_id, f"⚠️ Falha ao publicar o job #{job.id} ({e}). "
                                                    f"Nova tentativa {fmt_quando(novo, self.cfg)}.")
                else:
                    job = self.fila.atualizar(job.id, estado="erro", erro=str(e)[:500])
                    await self.n.texto(job.chat_id, f"❌ Não consegui publicar o job #{job.id} após 3 tentativas: {e}")
                feitos.append(job)
                continue
            job = self.fila.atualizar(job.id, estado="publicado", permalink=res.permalink or "")
            await self.n.texto(job.chat_id, f"✅ Publicado! Job #{job.id}: {res.permalink or '(link indisponível)'}")
            feitos.append(job)
        return feitos

    async def loop_agendador(self, parar: asyncio.Event, intervalo: float = 30.0):
        while not parar.is_set():
            try:
                await self.publicar_vencidos()
            except Exception as e:  # noqa: BLE001
                print(f"[agendador] erro: {e}", file=sys.stderr)
            try:
                await asyncio.wait_for(parar.wait(), timeout=intervalo)
            except asyncio.TimeoutError:
                pass

    # ---------------------------------------------------------------- consultas
    def resumo_fila(self) -> str:
        ativos = self.fila.listar(("aguardando_info", "na_fila", "editando", "ajustando", "aguardando_aprovacao",
                                   "agendado", "publicando", "erro"))
        if not ativos:
            return "Nenhum job ativo."
        nomes = {"aguardando_info": "esperando informação", "na_fila": "na fila", "editando": "editando",
                 "ajustando": "ajustando", "aguardando_aprovacao": "esperando aprovação", "agendado": "agendado",
                 "publicando": "publicando", "erro": "erro"}
        return "\n".join(f"#{j.id} · {nomes[j.estado]} · {j.modelo or '?'} · "
                         f"{fmt_quando(j.publicar_em_dt(), self.cfg) if j.publicar_em else '—'}"
                         + (f" · {j.erro[:60]}" if j.estado == "erro" else "") for j in ativos)
