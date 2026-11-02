#!/usr/bin/env python3
"""Detecta rostos para decidir o enquadramento (reframe) de cada segmento.

Uso: python3 engine/focus.py job/edl.json

Escreve segments[].focus = {"x":0..1, "y":0..1} (centro do rosto no quadro do
bruto). O render centraliza esse ponto ao recortar para 9:16 / 4:5 / 1:1.
Segmentos sem rosto ficam com o foco do segmento anterior (ou centro).
"""
import sys

import cv2

from common import load_json, log, save_json

_cascade = None


def detector():
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    return _cascade


def face_center(frame):
    h, w = frame.shape[:2]
    scale = 480 / max(h, w)
    small = cv2.resize(frame, (int(w * scale), int(h * scale)))
    gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
    faces = detector().detectMultiScale(gray, 1.1, 6, minSize=(int(24), int(24)))
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])  # maior rosto
    sw, sh = small.shape[1], small.shape[0]
    return ((x + fw / 2) / sw, (y + fh / 2) / sh, fw * fh / (sw * sh))


def add_focus(edl_path):
    edl = load_json(edl_path)
    cap = cv2.VideoCapture(edl["source"])
    if not cap.isOpened():
        log("focus: não consegui abrir o vídeo, mantendo centro")
        return
    last = {"x": 0.5, "y": 0.4}
    found = 0
    for seg in edl["segments"]:
        if seg.get("focus_locked"):
            last = seg.get("focus", last)
            continue
        pts = []
        for frac in (0.2, 0.5, 0.8):
            t = seg["in"] + (seg["out"] - seg["in"]) * frac
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ok, frame = cap.read()
            if ok:
                c = face_center(frame)
                if c:
                    pts.append(c)
        if pts:
            found += 1
            x = sum(p[0] for p in pts) / len(pts)
            y = sum(p[1] for p in pts) / len(pts)
            last = {"x": round(x, 3), "y": round(y, 3)}
        seg["focus"] = dict(last)
    cap.release()
    save_json(edl, edl_path)
    log(f"focus: rosto encontrado em {found}/{len(edl['segments'])} segmentos")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    add_focus(sys.argv[1])
