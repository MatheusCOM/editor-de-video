"""Ponto de entrada: python -m automacao

Lê o .env (ou variáveis de ambiente), recupera jobs interrompidos e liga o bot + editor + agendador.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .config import ROOT, Config


def carregar_env(caminho: Path):
    """Leitor mínimo de .env (CHAVE=valor por linha; # comenta). Não sobrescreve variáveis já definidas."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        k, v = linha.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    carregar_env(Path(os.environ.get("ENV_FILE", ROOT / "automacao" / ".env")))
    cfg = Config.do_ambiente()
    faltando = [p for p in cfg.problemas() if "ANTHROPIC" not in p or os.environ.get("EDITOR_SIMULADO") != "1"]
    if faltando:
        print("Configuração incompleta:\n- " + "\n- ".join(faltando), file=sys.stderr)
        sys.exit(2)

    from .bot import Bot
    from .editor_agente import EditorAgente, EditorSimulado
    from .fila import Fila
    from .servico import Servico

    fila = Fila(cfg.db_path)
    voltaram = fila.recuperar_interrompidos()
    if voltaram:
        print(f"[inicio] {len(voltaram)} job(s) interrompido(s) retomado(s)", file=sys.stderr)

    editor = EditorSimulado() if os.environ.get("EDITOR_SIMULADO") == "1" else EditorAgente(cfg)
    cliente_ia = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        import anthropic
        cliente_ia = anthropic.Anthropic()
    publicador = None
    # com credenciais, cria o publicador mesmo em ensaio: o /status testa a conexão,
    # e o Servico não publica enquanto MODO_ENSAIO=1
    if cfg.ig_user_id and cfg.ig_token:
        from .instagram import Instagram
        publicador = Instagram(cfg.ig_user_id, cfg.ig_token, cfg.graph_versao)

    def criar_servico(notificador):
        return Servico(cfg, fila, editor, notificador, publicador, cliente_ia)

    print(f"[inicio] modo {'ENSAIO' if cfg.modo_ensaio else 'PRODUÇÃO'} · editor {type(editor).__name__} · "
          f"dados em {cfg.dados}", file=sys.stderr)
    Bot(cfg, criar_servico).rodar()


if __name__ == "__main__":
    main()
