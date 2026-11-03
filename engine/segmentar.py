#!/usr/bin/env python3
"""Recorta a pessoa do vídeo (fundo transparente) para efeitos de "texto atrás da pessoa".

Uso: python3 engine/segmentar.py entrada.mp4 saida.webm [--suavizar 0.6]

Gera um WebM VP9 com canal alfa (yuva420p): a pessoa opaca e o fundo transparente,
com as mesmas dimensões e fps da entrada. O modelo (MediaPipe Selfie Segmenter,
~250 KB) é baixado uma vez para ~/.editor-video/models/ e roda no LiteRT (TFLite puro,
sem dependências gráficas): pip install ai-edge-litert.
"""
from __future__ import annotations

import argparse
import subprocess
import urllib.request
from pathlib import Path

import cv2
import numpy as np

from common import USER_HOME, log, probe, run

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
             "selfie_segmenter/float16/latest/selfie_segmenter.tflite")


def model_path() -> Path:
    p = USER_HOME / "models" / "selfie_segmenter.tflite"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        log("baixando modelo de segmentação…")
        urllib.request.urlretrieve(MODEL_URL, p)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("--suavizar", type=float, default=0.6, help="0..0.9: estabilidade temporal da máscara")
    a = ap.parse_args()

    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        try:
            from tflite_runtime.interpreter import Interpreter  # alternativa antiga
        except ImportError:
            raise SystemExit("ai-edge-litert não instalado (pip install ai-edge-litert). "
                             "Necessário só para 'texto atrás da pessoa'.")

    info = probe(a.entrada)
    w, h, fps = info["width"], info["height"], info["fps"] or 30
    it = Interpreter(model_path=str(model_path()), num_threads=4)
    it.allocate_tensors()
    inp, outp = it.get_input_details()[0], it.get_output_details()[0]
    ih, iw = int(inp["shape"][1]), int(inp["shape"][2])

    tmp_mask = Path(a.saida).with_suffix(".mask.mkv")
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps),
         "-i", "-", "-c:v", "ffv1", str(tmp_mask)], stdin=subprocess.PIPE)
    cap = cv2.VideoCapture(a.entrada)
    prev = None
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(cv2.resize(fr, (iw, ih), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        it.set_tensor(inp["index"], (rgb.astype(np.float32) / 255.0)[None])
        it.invoke()
        m = it.get_tensor(outp["index"])[0, ..., 0]
        m = cv2.resize(m.astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR)
        if prev is not None:  # estabilidade temporal
            m = a.suavizar * prev + (1 - a.suavizar) * m
        prev = m
        # borda: contraste na transição + leve desfoque para não serrilhar
        edge = np.clip((m - 0.35) / 0.3, 0, 1)
        edge = cv2.GaussianBlur(edge, (0, 0), 1.6)
        enc.stdin.write((edge * 255).astype(np.uint8).tobytes())
        i += 1
    cap.release()
    enc.stdin.close()
    enc.wait()
    log(f"máscara: {i} frames; montando vídeo com alfa…")
    run(["ffmpeg", "-y", "-v", "error", "-i", a.entrada, "-i", str(tmp_mask),
         "-filter_complex", "[0:v]format=rgba[c];[1:v]format=gray[m];[c][m]alphamerge,format=yuva420p[v]",
         "-map", "[v]", "-an", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "28", "-row-mt", "1",
         "-deadline", "realtime", "-cpu-used", "8", "-auto-alt-ref", "0", str(a.saida)])
    tmp_mask.unlink(missing_ok=True)
    print(a.saida)


if __name__ == "__main__":
    main()
