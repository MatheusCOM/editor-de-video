#!/usr/bin/env python3
"""Compara referência x resultado lado a lado (validação de modelo).

Uso: python3 engine/compare.py referencia.mp4 resultado.mp4 -o comparacao.jpg [--n 6] [--at 0.5 2 4]

Linha de cima = referência, linha de baixo = resultado, nos mesmos pontos
relativos do vídeo (ou nos tempos absolutos de --at).
"""
import argparse

import cv2
import numpy as np

from analyze import grab, label
from common import fmt_time, probe


def row(path, times, width):
    cap = cv2.VideoCapture(path)
    imgs = []
    for t in times:
        f = grab(cap, t, width)
        imgs.append(label(f, fmt_time(t)) if f is not None else None)
    cap.release()
    return imgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref")
    ap.add_argument("out")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--at", nargs="*", type=float)
    ap.add_argument("--width", type=int, default=260)
    a = ap.parse_args()
    d1, d2 = probe(a.ref)["duration"], probe(a.out)["duration"]
    fr = a.at and [t / d1 for t in a.at] or [(k + 0.5) / a.n for k in range(a.n)]
    top = row(a.ref, [f * d1 for f in fr], a.width)
    bot = row(a.out, [f * d2 for f in fr], a.width)
    h = max(i.shape[0] for i in top + bot if i is not None)
    pad = lambda i: cv2.resize(i, (a.width, h)) if i is not None else np.zeros((h, a.width, 3), np.uint8)
    grid = np.vstack([np.hstack([pad(i) for i in top]), np.full((8, a.width * len(fr), 3), 255, np.uint8),
                      np.hstack([pad(i) for i in bot])])
    cv2.imwrite(a.output, grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(a.output)


if __name__ == "__main__":
    main()
