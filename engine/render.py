#!/usr/bin/env python3
"""Renderiza o EDL em vídeos finais (um por formato).

  python3 engine/render.py job/edl.json                # render final → job/out/
  python3 engine/render.py job/edl.json --preview      # só frames de prévia → job/preview/
  python3 engine/render.py job/edl.json --preview --at 1.2 5 9.5
  python3 engine/render.py job/edl.json --formats 9x16 # só alguns formatos

Etapas: valida → pré-corte do bruto com ffmpeg (cortes, velocidade, color grade)
→ mixagem de áudio (voz, música com ducking, efeitos, loudnorm) → Remotion
(enquadramento, zooms, legendas, motion graphics) → mux final.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

from common import FORMATS, RENDER_DIR, USER_HOME, load_brand, load_json, load_template, log, probe, require_bin, run, save_json
from validate_edl import validate

DEFAULT_SAFE = {
    "9x16": {"top": 0.10, "bottom": 0.18, "left": 0.06, "right": 0.06},
    "4x5": {"top": 0.06, "bottom": 0.08, "left": 0.06, "right": 0.06},
    "1x1": {"top": 0.06, "bottom": 0.07, "left": 0.06, "right": 0.06},
    "16x9": {"top": 0.07, "bottom": 0.09, "left": 0.05, "right": 0.05},
}
MAX_SIDE = 1920


def resolve(p: str, base: Path) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (base / q).resolve()


def even(n: float) -> int:
    return int(round(n / 2) * 2)


# ------------------------------------------------------------------ pré-corte
def grade_filter(g: dict) -> str:
    parts = []
    eq = []
    for k, ff in (("brightness", "brightness"), ("contrast", "contrast"), ("saturation", "saturation"), ("gamma", "gamma")):
        if k in g and g[k] is not None:
            eq.append(f"{ff}={g[k]}")
    if eq:
        parts.append("eq=" + ":".join(eq))
    w = g.get("warmth")
    if w:
        # warmth -1..1 → leve deslocamento de canais via colorbalance
        a = round(0.12 * w, 3)
        parts.append(f"colorbalance=rs={a}:bs={-a}:rm={a / 2}:bm={-a / 2}")
    if g.get("sharpen"):
        parts.append(f"unsharp=5:5:{g['sharpen']}:5:5:0")
    if g.get("vignette"):
        parts.append("vignette=PI/5")
    return ",".join(parts)


def precut(edl: dict, src_info: dict, build: Path) -> tuple[Path, Path, dict]:
    segs = edl["segments"]
    fps = edl["fps"]
    vw, vh = src_info["width"], src_info["height"]
    s = min(1.0, MAX_SIDE / max(vw, vh))
    tw, th = even(vw * s), even(vh * s)
    key = hashlib.md5(json.dumps([edl["source"], segs, edl.get("grade"), fps, tw, th], sort_keys=True).encode()).hexdigest()[:10]
    vid, voice = build / f"cut_{key}.mp4", build / f"voice_{key}.wav"
    if vid.exists() and voice.exists():
        log("pré-corte em cache")
        return vid, voice, {"width": tw, "height": th}

    has_audio = src_info.get("has_audio")
    grade = grade_filter(edl.get("grade") or {})
    fc, vlabels, alabels = [], [], []
    for i, sg in enumerate(segs):
        sp = sg.get("speed", 1) or 1
        a, b = sg["in"], sg["out"]
        d = (b - a) / sp
        v = f"[0:v]trim=start={a}:end={b},setpts=(PTS-STARTPTS)/{sp},fps={fps},scale={tw}:{th}:flags=lanczos,setsar=1,format=yuv420p[v{i}]"
        fc.append(v)
        vlabels.append(f"[v{i}]")
        if has_audio:
            tempo = f",atempo={sp}" if sp != 1 else ""
            fade = min(0.012, d / 4)
            fc.append(
                f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS{tempo},aformat=sample_rates=48000:channel_layouts=stereo,"
                f"afade=t=in:d={fade},afade=t=out:st={max(0, d - fade):.4f}:d={fade}[a{i}]"
            )
            alabels.append(f"[a{i}]")
    n = len(segs)
    fc.append("".join(vlabels) + f"concat=n={n}:v=1:a=0[vc]")
    fc.append(f"[vc]{grade}[vout]" if grade else "[vc]null[vout]")
    if has_audio:
        fc.append("".join(alabels) + f"concat=n={n}:v=0:a=1[aout]")
    graph = build / "precut.ffgraph"
    graph.write_text(";\n".join(fc), encoding="utf-8")

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", edl["source"], "-filter_complex_script", str(graph),
           "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-g", str(int(fps // 2)),
           "-pix_fmt", "yuv420p", "-an", str(vid)]
    if has_audio:
        cmd += ["-map", "[aout]", "-vn", "-c:a", "pcm_s16le", str(voice)]
    log(f"pré-corte: {n} segmentos → {tw}x{th}")
    run(cmd)
    if not has_audio:
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-t", str(edl["duration"]), "-c:a", "pcm_s16le", str(voice)])
    return vid, voice, {"width": tw, "height": th}


# ------------------------------------------------------------------ áudio
def loudnorm_two_pass(inp: Path, out: Path, target: float):
    res = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(inp), "-af",
               f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], check=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", res.stderr, re.S)
    if not m:
        run(["ffmpeg", "-y", "-v", "error", "-i", str(inp), "-af", f"loudnorm=I={target}:TP=-1.5", "-ar", "48000", str(out)])
        return
    st = json.loads(m.group(0))
    if float(st["input_i"]) < -70:  # silêncio total
        shutil.copy(inp, out)
        return
    af = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={st['input_i']}:measured_TP={st['input_tp']}:"
          f"measured_LRA={st['input_lra']}:measured_thresh={st['input_thresh']}:offset={st['target_offset']}:linear=true")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(inp), "-af", af, "-ar", "48000", str(out)])


def mix_audio(edl: dict, voice: Path, base: Path, build: Path) -> Path:
    a = edl.get("audio") or {}
    dur = edl["duration"]
    inputs = ["-i", str(voice)]
    fc = []
    vchain = "highpass=f=70"
    if a.get("denoise"):
        vchain += ",afftdn=nf=-25"
    if a.get("voice_gain_db"):
        vchain += f",volume={a['voice_gain_db']}dB"
    fc.append(f"[0:a]{vchain},asplit=2[voice][sc]")
    mix = ["[voice]"]
    idx = 1
    music = a.get("music") or {}
    if music.get("src"):
        inputs += ["-stream_loop", "-1", "-i", str(resolve(music["src"], base))]
        vol = music.get("volume_db", -18)
        start = music.get("start_at", 0)
        fade_st = max(0, dur - 1.5)
        fc.append(
            f"[{idx}:a]atrim=start={start}:duration={dur},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
            f"volume={vol}dB,afade=t=in:d=0.3,afade=t=out:st={fade_st}:d=1.5[m0]"
        )
        if music.get("duck", True):
            fc.append("[m0][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[m]")
        else:
            fc.append("[sc]anullsink;[m0]anull[m]")
        mix.append("[m]")
        idx += 1
    else:
        fc.append("[sc]anullsink")

    sfx = list(a.get("sfx") or [])
    if a.get("sfx_on_cuts"):
        t = 0.0
        for sg in edl["segments"][:-1]:
            t += (sg["out"] - sg["in"]) / (sg.get("speed", 1) or 1)
            sfx.append({"src": a["sfx_on_cuts"], "at": max(0.0, t - 0.05), "volume_db": a.get("sfx_on_cuts_db", -10)})
    for s in sfx:
        inputs += ["-i", str(resolve(s["src"], base))]
        delay = int(s["at"] * 1000)
        fc.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={s.get('volume_db', -6)}dB,"
                  f"adelay={delay}|{delay}[s{idx}]")
        mix.append(f"[s{idx}]")
        idx += 1

    fc.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,atrim=duration={dur}[mix]")
    raw = build / "mix_raw.wav"
    graph = build / "mix.ffgraph"
    graph.write_text(";\n".join(fc), encoding="utf-8")
    run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex_script", str(graph), "-map", "[mix]",
         "-ar", "48000", "-c:a", "pcm_s16le", str(raw)])
    out = build / "mix.wav"
    loudnorm_two_pass(raw, out, a.get("loudness_lufs", -14))
    return out


# ------------------------------------------------------------------ Remotion
def link(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def prepare_public(edl: dict, brand: dict, cut: Path, base: Path, public: Path) -> tuple[dict, dict, str]:
    if public.exists():
        shutil.rmtree(public)
    public.mkdir(parents=True)
    link(cut, public / "cut.mp4")
    bdir = Path(brand["_dir"])
    brand = json.loads(json.dumps(brand))
    for f in brand["fonts"].get("files", []):
        src = bdir / f["file"]
        f["file"] = f"brand/{Path(f['file']).name}"
        link(src, public / f["file"])
    if brand.get("logo", {}).get("file"):
        src = bdir / brand["logo"]["file"]
        brand["logo"]["file"] = f"brand/{Path(src).name}"
        link(src, public / brand["logo"]["file"])

    edl = json.loads(json.dumps(edl))
    for i, b in enumerate(edl.get("broll", [])):
        src = resolve(b["src"], base)
        name = f"broll/{i}_{src.name}"
        link(src, public / name)
        b["src"] = name
        b["kind"] = "image" if src.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") else "video"
    for i, ov in enumerate(edl.get("overlays", [])):
        props = ov.get("props") or {}
        for k in ("src", "image", "imagem", "icone"):
            v = props.get(k)
            if v and not str(v).startswith(("http", "brand/")):
                if str(v).startswith("brand:"):
                    src = bdir / v[len("brand:"):]
                else:
                    src = resolve(v, base)
                name = f"assets/{i}_{src.name}"
                link(src, public / name)
                props[k] = name
    return edl, brand, "cut.mp4"


def sync_user_components():
    """Copia ~/.editor-video/components/*.tsx para o projeto Remotion e gera o registro."""
    dst = RENDER_DIR / "src" / "components" / "custom" / "user"
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob("*.tsx"):
        old.unlink()
    files = sorted((USER_HOME / "components").glob("*.tsx")) if (USER_HOME / "components").exists() else []
    lines = ["// GERADO AUTOMATICAMENTE por engine/render.py a partir de ~/.editor-video/components — não edite.",
             'import type React from "react";']
    names = []
    for i, f in enumerate(files):
        shutil.copy2(f, dst / f.name)
        lines.append(f'import C{i} from "./{f.stem}";')
        names.append(f'  "{f.stem}": C{i},')
    lines.append("export const userRegistry: Record<string, React.FC<any>> = {")
    lines += names
    lines.append("};")
    (dst / "index.ts").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if files:
        log(f"componentes do usuário: {', '.join(f.stem for f in files)}")


def remotion(job: dict, build: Path):
    sync_user_components()
    require_bin("node")
    if not (RENDER_DIR / "node_modules").exists():
        raise SystemExit("Dependências do Remotion ausentes. Rode scripts/setup.sh")
    jf = build / "remotion_job.json"
    save_json(job, jf)
    run(["node", str(RENDER_DIR / "render.mjs"), str(jf)], capture=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edl")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--at", nargs="*", type=float, help="tempos (s) dos frames de prévia")
    ap.add_argument("--formats", nargs="*")
    ap.add_argument("--out")
    ap.add_argument("--concurrency", type=int)
    args = ap.parse_args()

    require_bin("ffmpeg")
    edl_path = Path(args.edl).resolve()
    base = edl_path.parent
    errs, warns = validate(edl_path)
    for w in warns:
        log("AVISO:", w)
    if errs:
        for e in errs:
            log("ERRO:", e)
        raise SystemExit("EDL inválido — corrija e rode de novo.")

    edl = load_json(edl_path)
    tpl = load_template(edl["template"])
    brand = load_brand(edl["brand"])
    src_info = probe(edl["source"])
    build = base / "build"
    build.mkdir(exist_ok=True)

    cut, voice, cut_size = precut(edl, src_info, build)
    public = build / "public"
    redl, rbrand, video = prepare_public(edl, brand, cut, base, public)

    formats = args.formats or edl["formats"]
    safe_tpl = tpl.get("safe_zones", {})
    jobs = []
    out_dir = Path(args.out) if args.out else base / ("preview" if args.preview else "out")
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.preview:  # limpa prévias antigas para a folha não misturar rodadas
        for old in out_dir.glob("*.jpg"):
            old.unlink()
    stem = Path(edl["source"]).stem
    d = edl["duration"]
    stills = args.at or [round(x, 2) for x in (0.4, d * 0.25, d * 0.5, d * 0.75, max(0, d - 1.0))]
    for fmt in formats:
        w, h = FORMATS[fmt]
        props = {
            "edl": redl, "brand": rbrand, "format": fmt, "width": w, "height": h, "video": video,
            "sourceSize": cut_size, "safe": {**DEFAULT_SAFE[fmt], **safe_tpl.get(fmt, {})},
        }
        if args.preview:
            jobs.append({"props": props, "out": str(out_dir), "stills": stills})
        else:
            jobs.append({"props": props, "out": str(build / f"video_{fmt}.mp4")})

    remotion({"publicDir": str(public), "jobs": jobs, "concurrency": args.concurrency}, build)

    if args.preview:
        sheets = []
        for fmt in formats:
            frames = sorted(out_dir.glob(f"{fmt}_*s.jpg"))
            if not frames:
                continue
            sheet = out_dir / f"folha_{fmt}.jpg"
            ins = sum((["-i", str(f)] for f in frames), [])
            stack = "".join(f"[{i}]" for i in range(len(frames))) + (f"hstack={len(frames)}" if len(frames) > 1 else "null")
            run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", f"{stack},scale='min(2400,iw)':-2", str(sheet)])
            sheets.append(str(sheet))
        log(f"prévias em {out_dir}")
        print("\n".join(sheets))
        return

    mix = mix_audio(edl, voice, base, build)
    results = []
    for fmt in formats:
        final = out_dir / f"{stem}_{edl['template']}_{fmt}.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-i", str(build / f"video_{fmt}.mp4"), "-i", str(mix),
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
             "-shortest", "-movflags", "+faststart", str(final)])
        results.append(str(final))
        log("✔", final)
    print("\n".join(results))


if __name__ == "__main__":
    sys.exit(main())
