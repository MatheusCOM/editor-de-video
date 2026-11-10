"""Configuração lida do ambiente (.env). Nenhuma credencial fica no código."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent  # raiz do plugin editor-de-video


def _bool(v: str | None, default: bool = False) -> bool:
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "sim", "yes", "on")


def _ids(v: str | None) -> set[int]:
    return {int(x) for x in (v or "").replace(";", ",").split(",") if x.strip().lstrip("-").isdigit()}


@dataclass
class Config:
    # Telegram
    telegram_token: str = ""
    telegram_api_url: str = ""          # Bot API local (ex.: http://telegram-bot-api:8081) — vazio = nuvem (limite 20 MB)
    usuarios_autorizados: set[int] = field(default_factory=set)
    chat_avisos: int | None = None      # para onde vão avisos do sistema (padrão: primeiro autorizado)
    # Anthropic
    modelo_editor: str = "claude-opus-5-5"
    modelo_interpretador: str = "claude-haiku-5-5"
    esforco_editor: str = "high"
    teto_usd_por_job: float = 3.0
    # Instagram
    ig_user_id: str = ""
    ig_token: str = ""
    graph_versao: str = "v23.0"
    meta_app_id: str = ""
    meta_app_secret: str = ""
    # Geral
    modo_ensaio: bool = True
    marca_padrao: str = "icg"
    fuso: str = "America/Sao_Paulo"
    dados: Path = ROOT / "dados"
    hora_heartbeat: int = 9

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.fuso)

    @property
    def db_path(self) -> Path:
        return self.dados / "fila.sqlite3"

    @property
    def jobs_dir(self) -> Path:
        return self.dados / "jobs"

    @classmethod
    def do_ambiente(cls) -> "Config":
        e = os.environ
        autorizados = _ids(e.get("TELEGRAM_USUARIOS"))
        chat = e.get("TELEGRAM_CHAT_AVISOS")
        return cls(
            telegram_token=e.get("TELEGRAM_TOKEN", ""),
            telegram_api_url=e.get("TELEGRAM_API_URL", "").rstrip("/"),
            usuarios_autorizados=autorizados,
            chat_avisos=int(chat) if chat and chat.lstrip("-").isdigit() else (min(autorizados) if autorizados else None),
            modelo_editor=e.get("MODELO_EDITOR", cls.modelo_editor),
            modelo_interpretador=e.get("MODELO_INTERPRETADOR", cls.modelo_interpretador),
            esforco_editor=e.get("ESFORCO_EDITOR", cls.esforco_editor),
            teto_usd_por_job=float(e.get("TETO_USD_POR_JOB", cls.teto_usd_por_job)),
            ig_user_id=e.get("IG_USER_ID", ""),
            ig_token=e.get("IG_TOKEN", ""),
            graph_versao=e.get("GRAPH_VERSAO", cls.graph_versao),
            meta_app_id=e.get("META_APP_ID", ""),
            meta_app_secret=e.get("META_APP_SECRET", ""),
            modo_ensaio=_bool(e.get("MODO_ENSAIO"), True),
            marca_padrao=e.get("MARCA_PADRAO", cls.marca_padrao),
            fuso=e.get("FUSO", cls.fuso),
            dados=Path(e.get("DADOS_DIR", str(ROOT / "dados"))),
            hora_heartbeat=int(e.get("HORA_HEARTBEAT", cls.hora_heartbeat)),
        )

    def problemas(self) -> list[str]:
        """O que falta para rodar (mensagens em português)."""
        p = []
        if not self.telegram_token:
            p.append("TELEGRAM_TOKEN vazio (crie o bot no @BotFather)")
        if not self.usuarios_autorizados:
            p.append("TELEGRAM_USUARIOS vazio (IDs de quem pode usar o bot)")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            p.append("ANTHROPIC_API_KEY vazio (console.anthropic.com)")
        if not self.modo_ensaio and not (self.ig_user_id and self.ig_token):
            p.append("IG_USER_ID/IG_TOKEN vazios — necessários quando MODO_ENSAIO=0")
        return p
