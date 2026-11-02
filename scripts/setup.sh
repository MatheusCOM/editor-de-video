#!/usr/bin/env bash
# Instala as dependências do editor-video. Idempotente: pode rodar quantas vezes quiser.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ok()   { printf "  \033[32m✔\033[0m %s\n" "$*"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$*"; }
fail() { printf "  \033[31m✘\033[0m %s\n" "$*"; exit 1; }

echo "editor-video: verificando dependências"

command -v ffmpeg  >/dev/null || fail "ffmpeg não encontrado. Instale: macOS 'brew install ffmpeg' · Ubuntu 'sudo apt install ffmpeg' · Windows 'winget install ffmpeg'"
command -v ffprobe >/dev/null || fail "ffprobe não encontrado (vem junto com o ffmpeg)"
ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"

PY="$(command -v python3 || command -v python || true)"
[ -n "$PY" ] || fail "Python 3.10+ não encontrado"
"$PY" -c 'import sys; assert sys.version_info >= (3,10)' || fail "Python 3.10+ necessário"
ok "python $("$PY" --version | awk '{print $2}')"

command -v node >/dev/null || fail "Node.js 18+ não encontrado (https://nodejs.org)"
node -e 'process.exit(parseInt(process.versions.node) >= 18 ? 0 : 1)' || fail "Node.js 18+ necessário"
ok "node $(node --version)"

if "$PY" -c 'import faster_whisper, cv2, numpy, jsonschema, yt_dlp; assert hasattr(cv2, "CascadeClassifier")' 2>/dev/null; then
  ok "pacotes Python já instalados"
else
  echo "  instalando pacotes Python..."
  "$PY" -m pip install -q -r "$ROOT/requirements.txt" 2>/dev/null \
    || "$PY" -m pip install -q --user -r "$ROOT/requirements.txt" 2>/dev/null \
    || "$PY" -m pip install -q --break-system-packages -r "$ROOT/requirements.txt"
  ok "pacotes Python instalados"
fi

if [ -d "$ROOT/render/node_modules/remotion" ]; then
  ok "Remotion já instalado"
else
  echo "  instalando Remotion (npm)..."
  (cd "$ROOT/render" && npm ci --no-audit --no-fund --silent)
  ok "Remotion instalado"
fi

mkdir -p "$HOME/.editor-video/templates" "$HOME/.editor-video/components"
ok "pasta de dados: $HOME/.editor-video"

if [ "${SKIP_WHISPER:-0}" != "1" ]; then
  echo "  pré-baixando modelo Whisper (${WHISPER_MODEL:-small})..."
  if "$PY" -c "from faster_whisper import WhisperModel; WhisperModel('${WHISPER_MODEL:-small}', device='cpu', compute_type='int8')" 2>/dev/null; then
    ok "modelo Whisper pronto"
  else
    warn "não consegui baixar o modelo Whisper (huggingface.co bloqueado?). Transcrição/legendas ficam indisponíveis até liberar."
  fi
fi
echo "pronto."
