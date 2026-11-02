#!/usr/bin/env python3
"""Disseca um vídeo de referência (engenharia reversa da edição).

Uso:
  python3 engine/analyze.py referencia.mp4 --out templates/<nome>/referencia [--transcribe]

Gera em --out:
  analise.json        métricas medidas (cortes, ritmo, zooms, cor, áudio, estrutura)
  resumo.md           leitura humana das métricas + perguntas a responder olhando os frames
  folha_cortes.jpg    1 frame logo após cada corte (com timestamp)
  folha_geral.jpg     frames a cada ~N s cobrindo o vídeo todo
  gancho_*.jpg        primeiros 3 s a 10 fps (o gancho é o mais importante)
  denso/              sequências densas para analisar animações de texto/legenda
  transcript.json     (com --transcribe e Whisper disponível)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

from common import fmt_time, log, probe, run, save_json

AW = 320  # largura de análise


# ------------------------------------------------------------------ leitura
def read_frames(path, every=1):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    i = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % every == 0:
            yield i / fps, fr
        i += 1
    cap.release()


def small(fr):
    h, w = fr.shape[:2]
    return cv2.resize(fr, (AW, int(h * AW / w)), interpolation=cv2.INTER_AREA)


def affine_between(g1, g2):
    """Estima escala/translação entre dois frames (cinza, pequenos)."""
    p1 = cv2.goodFeaturesToTrack(g1, maxCorners=200, qualityLevel=0.01, minDistance=7)
    if p1 is None or len(p1) < 12:
        return None
    p2, st, _ = cv2.calcOpticalFlowPyrLK(g1, g2, p1, None, winSize=(21, 21), maxLevel=3)
    good = st.reshape(-1) == 1
    if good.sum() < 12:
        return None
    m, inl = cv2.estimateAffinePartial2D(p1[good], p2[good], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if m is None or inl is None:
        return None
    ratio = float(inl.sum()) / len(p1)
    s = math.hypot(m[0, 0], m[1, 0])
    return {"scale": s, "tx": float(m[0, 2]), "ty": float(m[1, 2]), "inliers": ratio}


# ------------------------------------------------------------------ passe principal (cortes + movimento)
def visual_pass(path, info):
    fps = info["fps"] or 30
    prev_g, prev_h = None, None
    diffs, hdiffs, motion, times = [], [], [], []
    thumbs = {}
    for t, fr in read_frames(path):
        s = small(fr)
        g = cv2.cvtColor(s, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(s, cv2.COLOR_BGR2HSV)
        h = cv2.calcHist([hsv], [0, 1], None, [32, 16], [0, 180, 0, 256])
        cv2.normalize(h, h)
        if prev_g is not None:
            diffs.append(float(np.mean(cv2.absdiff(g, prev_g))))
            hdiffs.append(float(cv2.compareHist(prev_h, h, cv2.HISTCMP_BHATTACHARYYA)))
            motion.append(affine_between(prev_g, g))
            times.append(t)
        thumbs[round(t, 3)] = g
        prev_g, prev_h = g, h
    d = np.array(diffs) if diffs else np.zeros(1)
    hd = np.array(hdiffs) if hdiffs else np.zeros(1)

    # corte = pico isolado de diferença (pixel OU histograma) bem acima da vizinhança
    cuts = []
    win = 6
    for i in range(len(d)):
        lo, hi = max(0, i - win), min(len(d), i + win + 1)
        neigh = np.concatenate([d[lo:i], d[i + 1:hi]]) if hi - lo > 1 else d
        base = np.median(neigh) if len(neigh) else 0
        mo = motion[i]
        broken = mo is None or mo["inliers"] < 0.35
        pix_spike = d[i] > max(12, base * 3.0)
        hist_spike = hd[i] > 0.35 and hd[i] > np.median(hd[lo:hi]) * 2.5
        if (pix_spike and broken) or hist_spike:
            if not cuts or times[i] - cuts[-1]["t"] > 0.2:
                cuts.append({"t": round(times[i], 3), "diff": round(float(d[i]), 1), "hist": round(float(hd[i]), 3)})

    # punch-in: salto de escala num único frame com o mesmo conteúdo (jump cut com zoom)
    punch_idx = set()
    for i, mo in enumerate(motion):
        if mo and mo["inliers"] > 0.4 and abs(mo["scale"] - 1) > 0.04:
            punch_idx.add(i)
            if not any(abs(c["t"] - times[i]) < 0.2 for c in cuts):
                cuts.append({"t": round(times[i], 3), "diff": round(float(d[i]), 1), "kind": "zoom_punch",
                             "zoom_cut": round(mo["scale"], 3)})
    cuts.sort(key=lambda c: c["t"])

    # zoom no corte (jump-cut com escala diferente): compara frame antes x depois
    keys = sorted(thumbs.keys())
    for c in cuts:
        idx = np.searchsorted(keys, c["t"])
        if 1 <= idx < len(keys):
            a = affine_between(thumbs[keys[idx - 1]], thumbs[keys[idx]])
            if "zoom_cut" not in c and a and a["inliers"] > 0.4 and abs(a["scale"] - 1) > 0.04:
                c["zoom_cut"] = round(a["scale"], 3)

    # zooms contínuos: escala acumulada por plano
    bounds = [0.0] + [c["t"] for c in cuts] + [info["duration"]]
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        sc, tx, ty, n = 1.0, 0.0, 0.0, 0
        for i, (t, mo) in enumerate(zip(times, motion)):
            if a < t <= b and mo and mo["inliers"] > 0.3 and i not in punch_idx:
                sc *= mo["scale"]
                tx += mo["tx"]
                ty += mo["ty"]
                n += 1
        shot = {"start": round(a, 3), "end": round(b, 3), "dur": round(b - a, 3)}
        if n:
            shot["scale_total"] = round(sc, 3)
            if abs(sc - 1) > 0.04:
                shot["zoom"] = "in" if sc > 1 else "out"
            pan = math.hypot(tx, ty) / AW
            if pan > 0.08:
                shot["pan"] = round(pan, 3)
        shots.append(shot)

    # shake = muita translação de alta frequência
    jit = [abs(m["tx"]) + abs(m["ty"]) for m in motion if m]
    shake = float(np.percentile(jit, 90)) / AW if jit else 0
    return cuts, shots, round(shake, 4)


# ------------------------------------------------------------------ cor
def color_pass(path, info, n=36):
    cap = cv2.VideoCapture(str(path))
    dur = info["duration"]
    sats, vals, cons, warm, pix = [], [], [], [], []
    for k in range(n):
        cap.set(cv2.CAP_PROP_POS_MSEC, (dur * (k + 0.5) / n) * 1000)
        ok, fr = cap.read()
        if not ok:
            continue
        s = small(fr)
        hsv = cv2.cvtColor(s, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(s, cv2.COLOR_BGR2LAB)
        sats.append(hsv[..., 1].mean() / 255)
        vals.append(lab[..., 0].mean() / 255)
        cons.append(lab[..., 0].std() / 255)
        warm.append((lab[..., 2].mean() - 128) / 128)
        pix.append(s.reshape(-1, 3)[::7])
    cap.release()
    if not pix:
        return {}
    data = np.float32(np.concatenate(pix))
    _, labels, centers = cv2.kmeans(data, 6, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0), 3,
                                    cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.reshape(-1), minlength=6)
    order = np.argsort(-counts)
    palette = [{"hex": "#%02X%02X%02X" % tuple(int(c) for c in centers[i][::-1]), "share": round(counts[i] / counts.sum(), 3)}
               for i in order]
    sat, bri, con, wr = float(np.mean(sats)), float(np.mean(vals)), float(np.mean(cons)), float(np.mean(warm))
    # sugestão de grade relativa a um vídeo "neutro" de celular (sat≈0.30, contraste≈0.20)
    grade = {
        "saturation": round(min(1.6, max(0.6, sat / 0.30)), 2),
        "contrast": round(min(1.35, max(0.85, con / 0.20)), 2),
        "brightness": round(max(-0.08, min(0.08, (bri - 0.5) * 0.2)), 3),
        "warmth": round(max(-0.6, min(0.6, wr * 4)), 2),
    }
    return {"saturation": round(sat, 3), "brightness": round(bri, 3), "contrast": round(con, 3),
            "warmth": round(wr, 3), "palette": palette, "grade_suggestion": grade}


# ------------------------------------------------------------------ áudio
def audio_pass(path, info, cuts):
    if not info.get("has_audio"):
        return {"has_audio": False}
    out = {"has_audio": True}
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"], check=False)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)
    out["loudness_lufs"] = float(m[-1]) if m else None

    sr = 16000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    if len(x) < sr:
        return out
    hop = int(sr * 0.01)
    frames = len(x) // hop
    rms = np.sqrt(np.mean(x[: frames * hop].reshape(frames, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    out["floor_db_p10"] = round(float(np.percentile(db, 10)), 1)
    out["speech_db_p90"] = round(float(np.percentile(db, 90)), 1)
    # fundo musical: o "chão" de áudio nunca cai a silêncio
    out["music_bed_likely"] = bool(out["floor_db_p10"] > -42)

    # pausas (silêncio) → mostra o quanto a edição corta respiros
    quiet = db < (out["speech_db_p90"] - 30)
    pauses, run_len = [], 0
    for q in quiet:
        if q:
            run_len += 1
        elif run_len:
            pauses.append(run_len * 0.01)
            run_len = 0
    pauses = [p for p in pauses if p >= 0.08]
    out["pause_p50"] = round(float(np.median(pauses)), 3) if pauses else 0
    out["pause_p90"] = round(float(np.percentile(pauses, 90)), 3) if pauses else 0
    out["pause_max"] = round(float(max(pauses)), 3) if pauses else 0

    # transientes (onsets) perto dos cortes → efeito sonoro em cada corte?
    spec_hop = 512
    win = np.hanning(1024)
    n = (len(x) - 1024) // spec_hop
    if n > 10:
        S = np.abs(np.fft.rfft(np.stack([x[i * spec_hop:i * spec_hop + 1024] * win for i in range(n)]), axis=1))
        flux = np.maximum(0, np.diff(np.log1p(S), axis=0)).sum(axis=1)
        thr = np.median(flux) + 3 * np.std(flux)
        onset_t = (np.where(flux > thr)[0] + 1) * spec_hop / sr
        near = sum(1 for c in cuts if np.any(np.abs(onset_t - c["t"]) < 0.08))
        out["onsets_per_min"] = round(len(onset_t) / (len(x) / sr / 60), 1)
        out["cuts_with_transient"] = f"{near}/{len(cuts)}"
        out["sfx_on_cuts_likely"] = bool(cuts and near / len(cuts) > 0.6)
    return out


# ------------------------------------------------------------------ folhas de contato
def label(img, text):
    h, w = img.shape[:2]
    cv2.rectangle(img, (0, h - 34), (w, h), (0, 0, 0), -1)
    cv2.putText(img, text, (8, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return img


def grab(cap, t, width):
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0, t) * 1000)
    ok, fr = cap.read()
    if not ok:
        return None
    h, w = fr.shape[:2]
    return cv2.resize(fr, (width, int(h * width / w)), interpolation=cv2.INTER_AREA)


def sheet(path, times, out, cols=6, width=300):
    if not times:
        return None
    cap = cv2.VideoCapture(str(path))
    imgs = []
    for t in times:
        f = grab(cap, t, width)
        if f is not None:
            imgs.append(label(f, fmt_time(t)))
    cap.release()
    if not imgs:
        return None
    h = imgs[0].shape[0]
    imgs = [cv2.resize(i, (width, h)) for i in imgs]
    rows = math.ceil(len(imgs) / cols)
    blank = np.zeros_like(imgs[0])
    grid = [np.hstack(imgs[r * cols:(r + 1) * cols] + [blank] * (cols - len(imgs[r * cols:(r + 1) * cols])))
            for r in range(rows)]
    full = np.vstack(grid)
    cv2.imwrite(str(out), full, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return str(out)


def sheets(path, info, cuts, out: Path):
    dur = info["duration"]
    res = {}
    cut_times = [c["t"] + 0.12 for c in cuts]
    # até 48 por folha; divide em várias se precisar
    for k in range(0, max(1, len(cut_times)), 48):
        p = sheet(path, cut_times[k:k + 48], out / f"folha_cortes_{k // 48 + 1}.jpg")
        if p:
            res.setdefault("cortes", []).append(p)
    step = max(0.5, dur / 36)
    res["geral"] = sheet(path, list(np.arange(0.25, dur, step)), out / "folha_geral.jpg")
    res["gancho"] = sheet(path, list(np.arange(0, min(3.0, dur), 0.1)), out / "gancho_0-3s_10fps.jpg", cols=6, width=260)
    # sequências densas: 1,2 s a 12 fps em 4 pontos do meio (para ver animação de legenda/MG)
    dense = out / "denso"
    dense.mkdir(exist_ok=True)
    res["denso"] = []
    for frac in (0.2, 0.4, 0.6, 0.85):
        t0 = dur * frac
        p = sheet(path, list(np.arange(t0, min(dur, t0 + 1.2), 1 / 12)), dense / f"seq_{t0:06.2f}s.jpg", cols=7, width=240)
        if p:
            res["denso"].append(p)
    return res


# ------------------------------------------------------------------ resumo
def summarize(a):
    c, s = a["cuts"], a["shots"]
    durs = [x["dur"] for x in s]
    rhythm = {
        "cuts": len(c),
        "cuts_per_min": round(len(c) / (a["info"]["duration"] / 60), 1) if a["info"]["duration"] else 0,
        "shot_avg": round(float(np.mean(durs)), 2) if durs else 0,
        "shot_median": round(float(np.median(durs)), 2) if durs else 0,
        "shot_min": round(min(durs), 2) if durs else 0,
        "shot_max": round(max(durs), 2) if durs else 0,
        "first_3s_cuts": sum(1 for x in c if x["t"] < 3),
        "zoom_cuts": sum(1 for x in c if "zoom_cut" in x),
        "zoom_cut_scales": sorted({x["zoom_cut"] for x in c if "zoom_cut" in x}),
        "shots_with_slow_zoom": sum(1 for x in s if "zoom" in x),
    }
    # curva de ritmo por terços
    d = a["info"]["duration"]
    thirds = []
    for k in range(3):
        a0, b0 = d * k / 3, d * (k + 1) / 3
        thirds.append(sum(1 for x in c if a0 <= x["t"] < b0))
    rhythm["cuts_by_third"] = thirds
    return rhythm


def write_md(a, out: Path):
    r, col, au, info = a["rhythm"], a.get("color", {}), a.get("audio", {}), a["info"]
    L = [f"# Análise de referência — {Path(info['path']).name}", "",
         f"- Duração: {info['duration']:.1f}s · {info.get('width')}x{info.get('height')} ({info.get('orientation')}) · {info.get('fps')} fps",
         "", "## Ritmo de cortes",
         f"- {r['cuts']} cortes ({r['cuts_per_min']}/min) · plano médio {r['shot_avg']}s (mediana {r['shot_median']}s, min {r['shot_min']}s, máx {r['shot_max']}s)",
         f"- Cortes nos primeiros 3s: {r['first_3s_cuts']} · por terço do vídeo: {r['cuts_by_third']}",
         f"- Cortes com mudança de zoom (punch-in em jump cut): {r['zoom_cuts']} {r['zoom_cut_scales']}",
         f"- Planos com zoom contínuo: {r['shots_with_slow_zoom']} · tremor/shake (p90): {a['shake']}",
         "", "## Cor",
         f"- Saturação {col.get('saturation')} · brilho {col.get('brightness')} · contraste {col.get('contrast')} · temperatura {col.get('warmth')}",
         f"- Paleta dominante: {', '.join(p['hex'] for p in col.get('palette', []))}",
         f"- Grade sugerido: {col.get('grade_suggestion')}",
         "", "## Áudio",
         f"- Loudness {au.get('loudness_lufs')} LUFS · música de fundo provável: {au.get('music_bed_likely')}",
         f"- Pausas: mediana {au.get('pause_p50')}s, p90 {au.get('pause_p90')}s, máx {au.get('pause_max')}s",
         f"- Transientes nos cortes: {au.get('cuts_with_transient')} → efeito sonoro nos cortes provável: {au.get('sfx_on_cuts_likely')}",
         ]
    if a.get("speech"):
        sp = a["speech"]
        L += ["", "## Fala", f"- {sp['words']} palavras · {sp['wpm']} palavras/min",
              f"- Primeiras palavras (gancho): \"{sp['hook_text']}\""]
    L += ["", "## Olhe as imagens e responda (para escrever REGRAS.md)",
          "1. Legenda: posição vertical, tamanho (relativo à largura), fonte (peso/estilo), caixa alta?, cor base, cor/efeito da palavra ativa, contorno/sombra/caixa, quantas palavras por vez, animação de entrada (veja denso/).",
          "2. Gancho (gancho_0-3s): o que aparece nos 3 primeiros segundos? título? texto grande? corte rápido? zoom?",
          "3. Motion graphics: que elementos aparecem (títulos, setas, emojis, cards, checklist, contador, lower third, barra de progresso, logo)? quando e com que animação?",
          "4. Enquadramento: rosto centralizado? em que altura? fundo desfocado? tela dividida? b-roll em tela cheia ou janela?",
          "5. Transições: corte seco, flash, zoom, whip/slide?",
          "6. Estrutura narrativa e CTA: como termina? card final? texto do CTA?",
          "7. Algo que a biblioteca de componentes ainda não tem? → criar componente custom.",
          ]
    (out / "resumo.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", required=True)
    ap.add_argument("--transcribe", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    info = probe(args.video)
    log("passe visual (cortes, zooms) ...")
    cuts, shots, shake = visual_pass(args.video, info)
    log(f"{len(cuts)} cortes; cor ...")
    color = color_pass(args.video, info)
    log("áudio ...")
    audio = audio_pass(args.video, info, cuts)
    a = {"info": info, "cuts": cuts, "shots": shots, "shake": shake, "color": color, "audio": audio}
    a["rhythm"] = summarize(a)
    if args.transcribe:
        try:
            run([sys.executable, str(Path(__file__).parent / "transcribe.py"), args.video, "-o", str(out / "transcript.json")],
                capture=False)
            tr = json.loads((out / "transcript.json").read_text(encoding="utf-8"))
            w = tr["words"]
            speak = (w[-1]["end"] - w[0]["start"]) if w else 0
            a["speech"] = {"words": len(w), "wpm": round(len(w) / (speak / 60), 1) if speak else 0,
                           "hook_text": " ".join(x["text"] for x in w if x["start"] < 3.0)}
        except Exception as e:  # noqa
            log(f"transcrição indisponível: {e}")
    log("folhas de contato ...")
    a["images"] = sheets(args.video, info, cuts, out)
    save_json(a, out / "analise.json")
    write_md(a, out)
    print((out / "resumo.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
