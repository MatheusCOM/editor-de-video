#!/usr/bin/env bash
# Empacota o estado (dados/ + .env) para levar do PC do Instituto para o servidor, e confere o pacote.
#   No PC:      bash automacao/migrar.sh exportar        → gera editor-estado-AAAAMMDD.tar.gz
#   No servidor: bash automacao/migrar.sh importar ARQUIVO.tar.gz
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"
case "${1:-}" in
  exportar)
    [ -f automacao/.env ] || { echo "automacao/.env não encontrado"; exit 1; }
    (cd automacao && docker compose stop editor) || true   # garante a fila parada e consistente
    arq="editor-estado-$(date +%Y%m%d-%H%M).tar.gz"
    tar czf "$arq" dados automacao/.env
    echo "Pacote: $arq ($(du -h "$arq" | cut -f1))"
    tar tzf "$arq" | grep -q "dados/fila.sqlite3" && echo "✔ fila incluída" || echo "! fila não encontrada (nenhum job ainda?)"
    echo "Copie para o servidor (ex.: scp $arq usuario@servidor:~/editor-de-video/) e rode: bash automacao/migrar.sh importar $arq"
    ;;
  importar)
    arq="${2:?informe o arquivo .tar.gz}"
    [ -e dados/fila.sqlite3 ] && { echo "Já existe dados/fila.sqlite3 aqui. Mova-o antes para não sobrescrever."; exit 1; }
    tar xzf "$arq"
    echo "✔ estado importado. Agora: cd automacao && docker compose up -d --build"
    echo "Depois que o servidor estiver no ar e respondendo, DESLIGUE o do PC (dois bots com o mesmo token brigam)."
    ;;
  *) echo "uso: $0 exportar | importar ARQUIVO.tar.gz"; exit 1 ;;
esac
