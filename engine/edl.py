#!/usr/bin/env python3
"""Cria e sincroniza o EDL (lista de decisões de edição).

  draft  — gera um rascunho automático a partir do modelo + transcrição:
           python3 engine/edl.py draft --source bruto.mp4 --template reels \
               --transcript job/transcript.json --out job/edl.json

  sync   — recalcula a linha do tempo depois que você (Claude) editou os
           segmentos, a transcrição ou os overlays. Gera legendas em tempo de
           saída, zooms automáticos e imprime a transcrição já no tempo final:
           python3 engine/edl.py sync job/edl.json

Convenções de tempo:
  * segments[].in/out  → tempo do BRUTO (segundos)
  * transcript.json    → tempo do BRUTO (é a fonte das legendas; corrija o texto lá)
  * zooms/overlays/broll/sfx → tempo da SAÍDA (vídeo já cortado)
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common import fmt_time, load_brand, load_json, load_template, log, probe, run, save_json

HESITATIONS = {"é", "ée", "éé", "ééé", "ã", "ãã", "ãh", "ah", "ahn", "hã", "hum", "humm", "hmm", "eh", "uh", "um", "hm"}


def norm(w: str) -> str:
    return re.sub(r"[^\wà-ú]", "", w.lower())


# ---------------------------------------------------------------- segmentos
def segments_from_words(words, cut, duration):
    pad_in = cut.get("pad_before", 0.08)
    pad_out = cut.get("pad_after", 0.14)
    max_pause = cut.get("max_pause", 0.35)
    drop_hes = cut.get("remove_hesitations", True)
    keep = [w for w in words if not (drop_hes and norm(w["text"]) in HESITATIONS)]
    if not keep:
        return [{"in": 0.0, "out": round(duration, 3)}]
    segs = []
    cur = [keep[0]["start"], keep[0]["end"]]
    for w in keep[1:]:
        if w["start"] - cur[1] <= max_pause:
            cur[1] = max(cur[1], w["end"])
        else:
            segs.append(cur)
            cur = [w["start"], w["end"]]
    segs.append(cur)
    out = []
    for a, b in segs:
        a, b = max(0.0, a - pad_in), min(duration, b + pad_out)
        if out and a <= out[-1]["out"]:
            out[-1]["out"] = round(b, 3)
        else:
            out.append({"in": round(a, 3), "out": round(b, 3)})
    # trecho curto (ex.: um "Sim." isolado) é FALA: nunca descartar. Junta com o vizinho mais próximo,
    # mantendo a pausa entre eles, para não gerar um corte picado.
    min_len = cut.get("min_segment", 0.25)
    i = 0
    while len(out) > 1 and i < len(out):
        s = out[i]
        if s["out"] - s["in"] >= min_len:
            i += 1
            continue
        gap_prev = s["in"] - out[i - 1]["out"] if i > 0 else float("inf")
        gap_next = out[i + 1]["in"] - s["out"] if i + 1 < len(out) else float("inf")
        if gap_prev <= gap_next:
            out[i - 1]["out"] = s["out"]
            out.pop(i)
        else:
            out[i + 1]["in"] = s["in"]
            out.pop(i)
    return out


def segments_from_silence(src, cut, duration):
    noise = cut.get("silence_db", -35)
    max_pause = cut.get("max_pause", 0.35)
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", src, "-vn",
               "-af", f"silencedetect=noise={noise}dB:d={max_pause}", "-f", "null", "-"], check=False)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", res.stderr)]
    silences = list(zip(starts, ends + [duration] * (len(starts) - len(ends))))
    pad_in, pad_out = cut.get("pad_before", 0.08), cut.get("pad_after", 0.14)
    segs, t = [], 0.0
    for s, e in silences:
        if s > t:
            segs.append({"in": round(max(0, t - pad_in if t > 0 else 0), 3), "out": round(min(duration, s + pad_out), 3)})
        t = e
    if t < duration:
        segs.append({"in": round(max(0, t - pad_in), 3), "out": round(duration, 3)})
    return [s for s in segs if s["out"] - s["in"] >= cut.get("min_segment", 0.25)] or [{"in": 0, "out": duration}]


# ---------------------------------------------------------------- timeline
def seg_len(s):
    return (s["out"] - s["in"]) / (s.get("speed", 1) or 1)


def total_duration(segments):
    return round(sum(seg_len(s) for s in segments), 3)


def map_words(words, segments):
    """Leva palavras do tempo do bruto para o tempo de saída."""
    out, offset = [], 0.0
    for s in segments:
        for w in words:
            if w.get("drop"):
                continue
            mid = (w["start"] + w["end"]) / 2
            if s["in"] <= mid < s["out"] and norm(w["text"]) not in HESITATIONS:
                sp = s.get("speed", 1) or 1
                o = {
                    "text": w["text"],
                    "start": round(offset + (max(w["start"], s["in"]) - s["in"]) / sp, 3),
                    "end": round(offset + (min(w["end"], s["out"]) - s["in"]) / sp, 3),
                }
                for k in ("emphasis", "color", "emoji"):
                    if w.get(k):
                        o[k] = w[k]
                out.append(o)
        offset += seg_len(s)
    return out


def segment_bounds(segments):
    bounds, t = [], 0.0
    for s in segments:
        d = seg_len(s)
        bounds.append((round(t, 3), round(t + d, 3)))
        t += d
    return bounds


def auto_zooms(edl, tpl):
    rule = tpl.get("zoom", {})
    zooms = [z for z in edl.get("zooms", []) if not z.get("auto")]
    jump = rule.get("jump_cut_scale")
    if jump and jump > 1:
        for i, (a, b) in enumerate(segment_bounds(edl["segments"])):
            if i % 2 == 1:
                zooms.append({"start": a, "end": b, "scale": jump, "type": "punch", "auto": True})
    slow = rule.get("slow_push")
    if slow and slow > 1:
        zooms.append({"start": 0, "end": edl["duration"], "scale": slow, "type": "slow", "auto": True})
    return sorted(zooms, key=lambda z: z["start"])


def resolve_overlays(overlays, duration):
    out = []
    for ov in overlays:
        ov = dict(ov)
        anchor = ov.get("anchor")
        if anchor == "full":
            ov["start"], ov["end"] = 0.0, duration
        elif anchor == "start":
            ov["start"] = ov.get("offset", 0.0)
            ov["end"] = ov["start"] + ov.get("duration", 2.0)
        elif anchor == "end":
            ov["end"] = duration - ov.get("offset", 0.0)
            ov["start"] = max(0.0, ov["end"] - ov.get("duration", 3.0))
        ov["start"], ov["end"] = round(ov["start"], 3), round(min(ov["end"], duration), 3)
        out.append(ov)
    return out


def timeline_text(edl):
    lines = [f"# duração final {fmt_time(edl['duration'])} ({edl['duration']:.2f}s)", "# cortes:"]
    for i, ((a, b), s) in enumerate(zip(segment_bounds(edl["segments"]), edl["segments"])):
        lines.append(f"  seg{i:02d} saída {a:7.2f}-{b:7.2f}  | bruto {s['in']:7.2f}-{s['out']:7.2f}")
    lines.append("# fala (tempo de SAÍDA):")
    words = edl.get("captions", {}).get("words", [])
    line, t0 = [], None
    for w in words:
        if t0 is None:
            t0 = w["start"]
        line.append(w["text"])
        if len(line) >= 10 or re.search(r"[.!?]$", w["text"]):
            lines.append(f"  [{t0:6.2f}] {' '.join(line)}")
            line, t0 = [], None
    if line:
        lines.append(f"  [{t0:6.2f}] {' '.join(line)}")
    return "\n".join(lines)


def sync(edl_path):
    edl_path = Path(edl_path)
    edl = load_json(edl_path)
    tpl = load_template(edl["template"])
    # a ordem da lista É a ordem do vídeo final (pode reordenar para trazer o gancho ao início)
    edl["duration"] = total_duration(edl["segments"])
    tr_path = edl.get("transcript")
    if tr_path and not edl.get("captions", {}).get("manual"):
        tr = load_json(edl_path.parent / tr_path if not Path(tr_path).is_absolute() else tr_path)
        edl.setdefault("captions", {})["words"] = map_words(tr["words"], edl["segments"])
    edl["zooms"] = auto_zooms(edl, tpl)
    edl["overlays"] = resolve_overlays(edl.get("overlays", []), edl["duration"])
    save_json(edl, edl_path)
    txt = timeline_text(edl)
    (edl_path.parent / "timeline.txt").write_text(txt, encoding="utf-8")
    print(txt)
    return edl


# ---------------------------------------------------------------- draft
def draft(args):
    tpl = load_template(args.template)
    if not args.brand:
        from common import list_brands
        raise SystemExit("Falta --brand. Marcas disponíveis: " + ", ".join(list_brands()) +
                         ". Pergunte ao usuário para qual marca é o vídeo antes de editar "
                         "(marca nova: skill configurar-marca).")
    brand = load_brand(args.brand)  # falha cedo se a marca não existir
    info = probe(args.source)
    out = Path(args.out)
    job = out.parent
    job.mkdir(parents=True, exist_ok=True)
    cut = tpl.get("cut", {})

    words = []
    tr_rel = None
    if args.transcript:
        tr = load_json(args.transcript)
        words = tr["words"]
        tr_rel = str(Path(args.transcript).resolve().relative_to(job.resolve())) \
            if Path(args.transcript).resolve().is_relative_to(job.resolve()) else str(Path(args.transcript).resolve())

    if cut.get("mode", "speech") == "none":
        segments = [{"in": 0.0, "out": round(info["duration"], 3)}]
    elif words:
        segments = segments_from_words(words, cut, info["duration"])
    elif info["has_audio"]:
        segments = segments_from_silence(args.source, cut, info["duration"])
    else:
        segments = [{"in": 0.0, "out": round(info["duration"], 3)}]

    edl = {
        "version": 1,
        "template": args.template,
        "brand": args.brand,
        "source": info["path"],
        "source_info": {k: info.get(k) for k in ("width", "height", "fps", "duration", "orientation", "has_audio")},
        "transcript": tr_rel,
        "fps": tpl.get("fps", 30),
        "formats": tpl.get("formats", ["9x16"]),
        "reframe": tpl.get("reframe", {"mode": "cover"}),
        "segments": segments,
        "captions": {**tpl.get("captions", {}), "words": []},
        "zooms": [],
        # assinatura só entra se a marca tiver quem assinar
        "overlays": [dict(o) for o in tpl.get("overlays", [])
                     if o["type"] != "assinatura" or (brand.get("assinatura") or {}).get("nome")],
        "broll": [],
        "grade": tpl.get("grade", {}),
        "audio": tpl.get("audio", {}),
        "notes": "",
    }
    save_json(edl, out)
    sync(out)
    if args.focus:
        from focus import add_focus
        add_focus(out)
    log(f"rascunho salvo em {out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draft")
    d.add_argument("--source", required=True)
    d.add_argument("--template", required=True)
    d.add_argument("--brand", help="slug da marca (engine/marcas.py lista as disponíveis)")
    d.add_argument("--transcript")
    d.add_argument("--out", required=True)
    d.add_argument("--no-focus", dest="focus", action="store_false",
                   help="não detectar rosto para enquadrar")
    s = sub.add_parser("sync")
    s.add_argument("edl")
    args = ap.parse_args()
    if args.cmd == "draft":
        draft(args)
    else:
        sync(args.edl)


if __name__ == "__main__":
    sys.exit(main())
