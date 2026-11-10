"""Interpreta o pedido em texto livre ("capa-fala, posta quinta 19h") → modelo, marca, data/hora.

Usa um modelo barato com saída estruturada; o resultado é sempre validado contra os modelos e
marcas que existem de verdade. Sem chave/API, cai num leitor simples por palavras-chave.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import ROOT

sys.path.insert(0, str(ROOT / "engine"))
from common import list_brands, list_templates, load_json, template_dir  # noqa: E402

SCHEMA = {
    "type": "object",
    "properties": {
        "modelo": {"type": ["string", "null"], "description": "nome exato de um dos modelos listados, ou null"},
        "marca": {"type": ["string", "null"], "description": "slug exato de uma das marcas listadas, ou null"},
        "publicar_em": {"type": ["string", "null"],
                        "description": "data e hora local no formato YYYY-MM-DDTHH:MM, ou null se não informada"},
        "publicar_agora": {"type": "boolean", "description": "true se pediu para publicar assim que aprovado"},
        "observacoes": {"type": "string", "description": "instruções extras de edição ou da legenda; vazio se nenhuma"},
    },
    "required": ["modelo", "marca", "publicar_em", "publicar_agora", "observacoes"],
    "additionalProperties": False,
}

DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]


@dataclass
class Pedido:
    modelo: str | None
    marca: str | None
    publicar_em: datetime | None      # com fuso
    publicar_agora: bool
    observacoes: str

    def falta(self) -> list[str]:
        f = []
        if not self.modelo:
            f.append("modelo")
        if not self.publicar_em and not self.publicar_agora:
            f.append("data")
        return f


def catalogo() -> str:
    linhas = ["Modelos:"]
    for n in list_templates():
        desc = load_json(template_dir(n) / "template.json").get("description", "")
        linhas.append(f"- {n}: {desc[:160]}")
    linhas.append("Marcas: " + ", ".join(list_brands()))
    return "\n".join(linhas)


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


def _validar(d: dict, tz: ZoneInfo, marca_padrao: str | None, agora: datetime) -> Pedido:
    modelos, marcas = set(list_templates()), set(list_brands())
    modelo = d.get("modelo") if d.get("modelo") in modelos else None
    marca = d.get("marca") if d.get("marca") in marcas else (marca_padrao if marca_padrao in marcas else None)
    quando = None
    if d.get("publicar_em"):
        try:
            quando = datetime.fromisoformat(d["publicar_em"])
            quando = quando.replace(tzinfo=tz) if quando.tzinfo is None else quando.astimezone(tz)
            if quando < agora - timedelta(minutes=5):
                quando = None  # no passado: pergunta de novo
        except ValueError:
            quando = None
    return Pedido(modelo, marca, quando, bool(d.get("publicar_agora")), d.get("observacoes") or "")


def interpretar(texto: str, tz: ZoneInfo, marca_padrao: str | None = None, agora: datetime | None = None,
                cliente=None, modelo_ia: str = "claude-haiku-5-5") -> Pedido:
    agora = (agora or datetime.now(tz)).astimezone(tz)
    if cliente is not None:
        try:
            prompt = (
                f"Agora é {DIAS[agora.weekday()]}, {agora:%Y-%m-%d %H:%M} (fuso {tz.key}).\n"
                f"{catalogo()}\n\n"
                "Extraia do pedido abaixo o modelo de edição, a marca e quando publicar. Datas relativas "
                "('quinta', 'amanhã', 'semana que vem') devem virar a próxima ocorrência futura. "
                "Hora sem minutos = minuto 00. Se não houver hora, use null. Não invente modelo ou marca: "
                "se o texto não corresponder claramente a um da lista, use null.\n\n"
                f"Pedido: {texto!r}"
            )
            r = cliente.messages.create(
                model=modelo_ia,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
            )
            bloco = next(b for b in r.content if b.type == "text")
            return _validar(json.loads(bloco.text), tz, marca_padrao, agora)
        except Exception as e:  # noqa: BLE001 — qualquer falha cai no leitor simples
            print(f"[interpretar] IA indisponível, usando leitor simples: {e}", file=sys.stderr)
    return interpretar_simples(texto, tz, marca_padrao, agora)


def interpretar_simples(texto: str, tz: ZoneInfo, marca_padrao: str | None, agora: datetime) -> Pedido:
    """Leitor por palavras-chave (sem IA). Entende: nome do modelo, 'agora', 'hoje'/'amanhã'/dia da semana,
    'dd/mm', e hora 'HHh', 'HH:MM' ou 'HHhMM'."""
    t = _norm(texto)
    modelo = next((m for m in sorted(list_templates(), key=len, reverse=True) if _norm(m) in t), None)
    marca = next((b for b in list_brands() if re.search(rf"\b{re.escape(b)}\b", t)), None)
    agora_flag = bool(re.search(r"\b(agora|ja|imediato|assim que aprovar)\b", t))
    dia = None
    if "amanha" in t:
        dia = agora.date() + timedelta(days=1)
    elif "hoje" in t:
        dia = agora.date()
    else:
        for i, d in enumerate(DIAS):
            if re.search(rf"\b{_norm(d)}\b", t):
                delta = (i - agora.weekday()) % 7
                dia = agora.date() + timedelta(days=delta or 7)
                break
        m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
        if m:
            ano = int(m.group(3)) if m.group(3) else agora.year
            ano = ano + 2000 if ano < 100 else ano
            try:
                dia = datetime(ano, int(m.group(2)), int(m.group(1))).date()
            except ValueError:
                pass
    hm = re.search(r"\b(\d{1,2})(?:h|:)(\d{2})?\b", t)
    quando = None
    if dia and hm:
        quando = datetime(dia.year, dia.month, dia.day, int(hm.group(1)), int(hm.group(2) or 0), tzinfo=tz)
    d = {"modelo": modelo, "marca": marca, "publicar_em": quando.isoformat() if quando else None,
         "publicar_agora": agora_flag and not quando, "observacoes": ""}
    return _validar(d, tz, marca_padrao, agora)
