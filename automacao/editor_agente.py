"""Roda a edição com o Claude Agent SDK, usando as skills do plugin (editar-video), sem humano no meio.

O agente trabalha dentro da pasta do job, segue a skill completa (marca → transcrição → roteiro
visual → EDL → prévia → render) e devolve um JSON estruturado com o vídeo final e a legenda do post.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import ROOT, Config

SCHEMA_RESULTADO = {
    "type": "object",
    "properties": {
        "video_final": {"type": "string", "description": "caminho do mp4 final (9x16), relativo à pasta do job"},
        "previa": {"type": "string", "description": "caminho da folha de prévia (jpg), relativo à pasta do job"},
        "roteiro_resumo": {"type": "string", "description": "3 a 8 linhas: o que foi cortado e cada motion usado"},
        "legenda": {"type": "string", "description": "legenda do post do Instagram, pronta para publicar, com hashtags no fim"},
        "pendencias": {"type": "array", "items": {"type": "string"},
                       "description": "o que precisa de decisão humana ou ficou pendente (ex.: CRM vazio)"},
    },
    "required": ["video_final", "previa", "roteiro_resumo", "legenda", "pendencias"],
    "additionalProperties": False,
}

INSTRUCOES = """\
Você é o editor de vídeo do sistema automático. Não há humano acompanhando esta execução: \
quem aprova é o cliente, depois, pelo Telegram, olhando o vídeo final que você entregar.

Siga a skill `editar-video` do plugin do começo ao fim, nesta pasta de trabalho (a pasta atual):
- Bruto: {bruto}
- Marca: {marca} (já confirmada; não pergunte)
- Modelo: {modelo}
- Observações do cliente: {observacoes}

Regras desta execução automática:
1. Onde a skill mandaria perguntar ao usuário, decida você pelo REGRAS.md do modelo, pelo `guia` da \
marca e pelas regras do segmento. Registre a decisão em `pendencias` só se for algo que realmente \
precisa do cliente (ex.: registro profissional vazio, dado que você não pode confirmar).
2. Escreva o roteiro visual (passo 3b), confira a prévia olhando as imagens, corrija o que estiver \
errado e só então faça o render final em 9x16.
3. Escreva a legenda do post no tom da marca, respeitando as regras do segmento (em saúde: sem \
promessa de resultado, sem sensacionalismo), com 3 a 8 hashtags relevantes no final.
4. Não publique nada e não acesse contas: só edite.
5. Responda no final apenas com o JSON pedido (caminhos relativos a esta pasta).
"""

INSTRUCOES_AJUSTE = """\
O cliente viu o vídeo e pediu este ajuste: "{feedback}".
Aplique o ajuste no EDL (e na legenda, se for o caso), refaça a prévia, confira, faça o render final \
de novo e responda com o mesmo JSON (atualizado). Se o pedido for impossível ou contrariar as regras \
da marca/segmento, faça o mais próximo possível e explique em `pendencias`.
"""


@dataclass
class ResultadoEdicao:
    video_final: Path
    previa: Path | None
    roteiro_resumo: str
    legenda: str
    pendencias: list[str] = field(default_factory=list)
    custo_usd: float = 0.0
    sessao: str | None = None


class ErroEdicao(RuntimeError):
    pass


def _resolver(base: Path, p: str | None) -> Path | None:
    if not p:
        return None
    q = Path(p)
    return q if q.is_absolute() else (base / q)


class EditorAgente:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def _opcoes(self, pasta: Path, retomar: str | None):
        from claude_agent_sdk import ClaudeAgentOptions

        return ClaudeAgentOptions(
            cwd=str(pasta),
            plugins=[{"type": "local", "path": str(ROOT)}],
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"],
            permission_mode="bypassPermissions",  # roda isolado no container, dentro da pasta do job
            model=self.cfg.modelo_editor,
            effort=self.cfg.esforco_editor,
            max_budget_usd=self.cfg.teto_usd_por_job,
            output_format={"type": "json_schema", "schema": SCHEMA_RESULTADO},
            resume=retomar,
        )

    async def _rodar(self, prompt: str, pasta: Path, retomar: str | None = None) -> ResultadoEdicao:
        from claude_agent_sdk import ResultMessage, query

        resultado = None
        async for msg in query(prompt=prompt, options=self._opcoes(pasta, retomar)):
            if isinstance(msg, ResultMessage):
                resultado = msg
        if resultado is None:
            raise ErroEdicao("o agente terminou sem resultado")
        if resultado.is_error:
            raise ErroEdicao(f"o agente falhou ({resultado.subtype}): {(resultado.result or '')[:400]}")
        dados = resultado.structured_output
        if dados is None and resultado.result:
            try:
                dados = json.loads(resultado.result)
            except json.JSONDecodeError:
                dados = None
        if not isinstance(dados, dict):
            raise ErroEdicao("o agente não devolveu o JSON de resultado")
        video = _resolver(pasta, dados.get("video_final"))
        if not video or not video.exists():
            raise ErroEdicao(f"vídeo final não encontrado: {dados.get('video_final')}")
        return ResultadoEdicao(
            video_final=video,
            previa=_resolver(pasta, dados.get("previa")),
            roteiro_resumo=dados.get("roteiro_resumo", ""),
            legenda=dados.get("legenda", ""),
            pendencias=list(dados.get("pendencias") or []),
            custo_usd=float(resultado.total_cost_usd or 0.0),
            sessao=resultado.session_id,
        )

    async def editar(self, pasta: Path, bruto: Path, marca: str, modelo: str, observacoes: str) -> ResultadoEdicao:
        prompt = INSTRUCOES.format(bruto=bruto, marca=marca, modelo=modelo, observacoes=observacoes or "(nenhuma)")
        return await self._rodar(prompt, pasta)

    async def ajustar(self, pasta: Path, sessao: str | None, feedback: str) -> ResultadoEdicao:
        return await self._rodar(INSTRUCOES_AJUSTE.format(feedback=feedback), pasta, retomar=sessao)


class EditorSimulado:
    """Para testar o fluxo inteiro sem custo: copia o bruto como "editado" e gera uma prévia com ffmpeg."""

    async def editar(self, pasta: Path, bruto: Path, marca: str, modelo: str, observacoes: str) -> ResultadoEdicao:
        pasta.mkdir(parents=True, exist_ok=True)
        final = pasta / "out" / f"simulado_{modelo}_9x16.mp4"
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bruto, final)
        previa = pasta / "previa.jpg"
        if shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(final), "-frames:v", "1", str(previa)], check=False)
        return ResultadoEdicao(final, previa if previa.exists() else None,
                               f"(simulado) modelo {modelo}, marca {marca}", f"Legenda simulada ({marca}).",
                               ["edição simulada: EDITOR_SIMULADO=1"], 0.0, "sessao-simulada")

    async def ajustar(self, pasta: Path, sessao: str | None, feedback: str) -> ResultadoEdicao:
        finais = sorted((pasta / "out").glob("*.mp4"))
        if not finais:
            raise ErroEdicao("nada para ajustar")
        return ResultadoEdicao(finais[-1], None, f"(simulado) ajuste: {feedback}", "Legenda simulada ajustada.",
                               [], 0.0, sessao)
