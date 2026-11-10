"""Fila de jobs em SQLite (um arquivo em dados/), segura para o bot, o worker e o agendador no mesmo processo."""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import MISSING, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ESTADOS = (
    "aguardando_info",       # falta modelo/data: o bot perguntou
    "na_fila",               # pronto para editar
    "editando",
    "aguardando_aprovacao",  # prévia enviada
    "ajustando",             # pedido de ajuste em andamento
    "agendado",              # aprovado, esperando o horário
    "publicando",
    "publicado",
    "descartado",
    "erro",
)
FINAIS = {"publicado", "descartado"}


def agora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    id: int
    chat_id: int
    estado: str
    criado_em: str
    atualizado_em: str
    bruto: str = ""
    pedido: str = ""
    modelo: str | None = None
    marca: str | None = None
    publicar_em: str | None = None      # ISO 8601 com fuso (UTC)
    observacoes: str = ""
    video_final: str | None = None
    previa: str | None = None
    legenda: str = ""
    roteiro: str = ""
    sessao_agente: str | None = None
    custo_usd: float = 0.0
    tentativas: int = 0
    erro: str = ""
    permalink: str | None = None
    extra: dict = field(default_factory=dict)

    @property
    def pasta(self) -> str:
        return f"job_{self.id:05d}"

    def publicar_em_dt(self) -> datetime | None:
        return datetime.fromisoformat(self.publicar_em) if self.publicar_em else None


_COLS = [f for f in Job.__dataclass_fields__ if f != "extra"]


class Fila:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        cols = ", ".join(
            f"{c} {'INTEGER PRIMARY KEY AUTOINCREMENT' if c == 'id' else 'REAL' if c == 'custo_usd' else 'INTEGER' if c in ('chat_id', 'tentativas') else 'TEXT'}"
            for c in _COLS
        )
        self._db.execute(f"CREATE TABLE IF NOT EXISTS jobs ({cols}, extra TEXT DEFAULT '{{}}')")
        self._db.execute("CREATE TABLE IF NOT EXISTS eventos (job_id INTEGER, em TEXT, texto TEXT)")
        self._db.commit()

    # ---------------------------------------------------------------- leitura
    def _row(self, r) -> Job:
        d = dict(r)
        d["extra"] = json.loads(d.get("extra") or "{}")
        return Job(**d)

    def obter(self, job_id: int) -> Job | None:
        with self._lock:
            r = self._db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return self._row(r) if r else None

    def listar(self, estados: tuple[str, ...] | None = None, limite: int = 50) -> list[Job]:
        q, args = "SELECT * FROM jobs", ()
        if estados:
            q += f" WHERE estado IN ({','.join('?' * len(estados))})"
            args = tuple(estados)
        q += " ORDER BY id DESC LIMIT ?"
        with self._lock:
            rows = self._db.execute(q, args + (limite,)).fetchall()
        return [self._row(r) for r in rows]

    def proximo_para_editar(self) -> Job | None:
        with self._lock:
            r = self._db.execute(
                "SELECT * FROM jobs WHERE estado IN ('na_fila','ajustando') ORDER BY id LIMIT 1").fetchone()
        return self._row(r) if r else None

    def vencidos(self, agora: datetime) -> list[Job]:
        """Jobs agendados cujo horário já chegou."""
        return [j for j in self.listar(("agendado",), 500)
                if j.publicar_em_dt() and j.publicar_em_dt() <= agora]

    def aguardando_info(self, chat_id: int) -> Job | None:
        with self._lock:
            r = self._db.execute(
                "SELECT * FROM jobs WHERE estado='aguardando_info' AND chat_id=? ORDER BY id DESC LIMIT 1",
                (chat_id,)).fetchone()
        return self._row(r) if r else None

    def eventos(self, job_id: int) -> list[tuple[str, str]]:
        with self._lock:
            return [tuple(r) for r in self._db.execute(
                "SELECT em, texto FROM eventos WHERE job_id=? ORDER BY rowid", (job_id,)).fetchall()]

    # ---------------------------------------------------------------- escrita
    def criar(self, chat_id: int, bruto: str = "", pedido: str = "", estado: str = "aguardando_info", **campos) -> Job:
        agora = agora_utc().isoformat()
        padroes = {k: f.default for k, f in Job.__dataclass_fields__.items()
                   if k not in ("id", "extra") and f.default is not MISSING}
        dados = {**padroes, "chat_id": chat_id, "estado": estado, "criado_em": agora, "atualizado_em": agora,
                 "bruto": bruto, "pedido": pedido, **campos}
        extra = json.dumps(dados.pop("extra", {}), ensure_ascii=False)
        with self._lock:
            cur = self._db.execute(
                f"INSERT INTO jobs ({','.join(dados)}, extra) VALUES ({','.join('?' * len(dados))}, ?)",
                tuple(dados.values()) + (extra,))
            self._db.commit()
            jid = cur.lastrowid
        self.registrar(jid, f"criado ({estado})")
        return self.obter(jid)

    def atualizar(self, job_id: int, **campos) -> Job:
        if "estado" in campos and campos["estado"] not in ESTADOS:
            raise ValueError(f"estado inválido: {campos['estado']}")
        campos["atualizado_em"] = agora_utc().isoformat()
        if "extra" in campos:
            campos["extra"] = json.dumps(campos["extra"], ensure_ascii=False)
        sets = ", ".join(f"{k}=?" for k in campos)
        with self._lock:
            self._db.execute(f"UPDATE jobs SET {sets} WHERE id=?", tuple(campos.values()) + (job_id,))
            self._db.commit()
        if "estado" in campos:
            self.registrar(job_id, f"estado → {campos['estado']}")
        return self.obter(job_id)

    def registrar(self, job_id: int, texto: str):
        with self._lock:
            self._db.execute("INSERT INTO eventos VALUES (?,?,?)", (job_id, agora_utc().isoformat(), texto))
            self._db.commit()

    def recuperar_interrompidos(self) -> list[Job]:
        """Ao reiniciar: jobs que ficaram no meio do caminho voltam para a fila (ou ficam agendados)."""
        voltar = []
        for j in self.listar(("editando", "publicando"), 500):
            novo = "na_fila" if j.estado == "editando" else "agendado"
            voltar.append(self.atualizar(j.id, estado=novo))
        return voltar
