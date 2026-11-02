#!/usr/bin/env python3
"""Transcreve o áudio em português com timestamps por palavra.

Uso: python3 engine/transcribe.py video.mp4 -o job/transcript.json [--model small]

Saída:
{
  "language": "pt",
  "duration": 61.2,
  "segments": [{"start":0.0,"end":3.1,"text":"..."}],
  "words": [{"text":"Olá","start":0.12,"end":0.40,"prob":0.98}, ...]
}

O modelo Whisper é baixado do huggingface.co na primeira execução (ou lido de
$WHISPER_MODEL_DIR, se você já tiver os arquivos baixados).
"""
import argparse
import os

from common import log, require_bin, run, save_json


def load_audio(src: str):
    """Decodifica com o ffmpeg para float32 mono 16 kHz (não depende do PyAV)."""
    import subprocess

    import numpy as np

    require_bin("ffmpeg")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--model", default=os.environ.get("WHISPER_MODEL", "small"),
                    help="tiny | base | small | medium | large-v3 (padrão: small)")
    ap.add_argument("--language", default="pt")
    args = ap.parse_args()

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise SystemExit("faster-whisper não instalado. Rode scripts/setup.sh")

    model_ref = os.environ.get("WHISPER_MODEL_DIR") or args.model
    log(f"carregando Whisper '{model_ref}' ...")
    try:
        model = WhisperModel(model_ref, device="auto", compute_type="int8")
    except Exception as e:  # rede bloqueada, modelo ausente etc.
        raise SystemExit(
            "Não consegui carregar o modelo Whisper. Se a rede bloqueia huggingface.co, libere esse domínio "
            "ou baixe o modelo e aponte WHISPER_MODEL_DIR para a pasta.\n"
            f"Detalhe: {e}"
        )

    if True:
        audio = load_audio(args.video)
        log("transcrevendo ...")
        segments, info = model.transcribe(
            audio, language=args.language, word_timestamps=True, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
        )
        out_segments, words = [], []
        for seg in segments:
            out_segments.append({"start": round(seg.start, 3), "end": round(seg.end, 3), "text": seg.text.strip()})
            for w in seg.words or []:
                txt = w.word.strip()
                if not txt:
                    continue
                words.append({"text": txt, "start": round(w.start, 3), "end": round(w.end, 3),
                              "prob": round(w.probability, 3)})

    result = {"language": info.language, "duration": round(info.duration, 3),
              "segments": out_segments, "words": words}
    save_json(result, args.out)
    log(f"{len(words)} palavras → {args.out}")


if __name__ == "__main__":
    main()
