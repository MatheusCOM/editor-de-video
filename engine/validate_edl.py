#!/usr/bin/env python3
"""Valida o EDL antes de renderizar.

Uso: python3 engine/validate_edl.py job/edl.json

Erros bloqueiam o render; avisos só informam.
"""
import re
import sys
from pathlib import Path

from common import SCHEMAS_DIR, load_brand, load_json, load_template

KNOWN_OVERLAYS = {"title", "text_pop", "lower_third", "cta", "emoji", "progress", "logo", "flash",
                  "image", "arrow", "checklist", "counter", "custom", "rotulo", "assinatura",
                  "capa", "cena", "item_numerado", "cartao", "chips"}


def resolve(p, base):
    p = Path(p)
    return p if p.is_absolute() else (base / p)


def validate(edl_path):
    edl_path = Path(edl_path)
    edl = load_json(edl_path)
    base = edl_path.parent
    errors, warns = [], []

    try:
        import jsonschema
        jsonschema.validate(edl, load_json(SCHEMAS_DIR / "edl.schema.json"))
    except ImportError:
        warns.append("jsonschema não instalado, validação de schema pulada")
    except Exception as e:  # jsonschema.ValidationError
        path = "/".join(str(x) for x in getattr(e, "absolute_path", []))
        errors.append(f"schema: {path}: {getattr(e, 'message', e)}")
        return errors, warns

    try:
        load_template(edl["template"])
    except SystemExit as e:
        errors.append(str(e))

    if not Path(edl["source"]).exists():
        errors.append(f"bruto não encontrado: {edl['source']}")
    src_dur = (edl.get("source_info") or {}).get("duration") or 1e9
    for i, s in enumerate(edl["segments"]):
        if s["out"] <= s["in"]:
            errors.append(f"segments[{i}]: out <= in")
        if s["out"] > src_dur + 0.05:
            errors.append(f"segments[{i}].out {s['out']} passa da duração do bruto {src_dur}")
        if s["out"] - s["in"] < 0.2:
            warns.append(f"segments[{i}] muito curto ({s['out'] - s['in']:.2f}s)")
    # a ordem pode ser livre (gancho movido para o início), mas trechos não podem se repetir sem querer
    ordered = sorted(enumerate(edl["segments"]), key=lambda x: x[1]["in"])
    for (i, a), (j, b) in zip(ordered, ordered[1:]):
        if b["in"] < a["out"] - 1e-3 and not (a.get("repeat") or b.get("repeat")):
            warns.append(f"segments[{i}] e segments[{j}] usam o mesmo trecho do bruto (sobreposição) — intencional? marque \"repeat\": true")
    if any(b[1]["in"] < a[1]["in"] for a, b in zip(enumerate(edl["segments"]), list(enumerate(edl["segments"]))[1:])):
        warns.append("segmentos fora da ordem do bruto (ok se for para trazer o gancho ao início)")

    expected = round(sum((s["out"] - s["in"]) / (s.get("speed", 1) or 1) for s in edl["segments"]), 3)
    if abs(expected - edl["duration"]) > 0.05:
        errors.append(f"duration {edl['duration']} ≠ soma dos segmentos {expected} — rode `edl.py sync`")
    dur = edl["duration"]

    for key in ("zooms", "overlays", "broll"):
        for i, item in enumerate(edl.get(key, [])):
            if "start" not in item or "end" not in item:
                errors.append(f"{key}[{i}] sem start/end — rode `edl.py sync`")
                continue
            if item["end"] <= item["start"]:
                errors.append(f"{key}[{i}]: end <= start")
            if item["start"] > dur + 0.01:
                errors.append(f"{key}[{i}] começa depois do fim do vídeo ({item['start']} > {dur})")
            if item["end"] > dur + 0.05:
                warns.append(f"{key}[{i}] termina depois do fim ({item['end']} > {dur}); será cortado")

    for i, ov in enumerate(edl.get("overlays", [])):
        if ov["type"] not in KNOWN_OVERLAYS:
            warns.append(f"overlays[{i}]: tipo '{ov['type']}' não é nativo — precisa existir em render/src/components/custom")
        blob = str(ov.get("props", {}))
        if re.search(r"\{\{.+?\}\}", blob):
            errors.append(f"overlays[{i}] ({ov['type']}) ainda tem placeholder: {re.findall(r'{{.+?}}', blob)}")
        for k in ("src", "image", "imagem", "icone"):
            v = ov.get("props", {}).get(k)
            if v and not v.startswith(("brand:", "http")) and not resolve(v, base).exists():
                errors.append(f"overlays[{i}].props.{k} não encontrado: {v}")

    if not edl.get("brand"):
        errors.append("EDL sem 'brand': pergunte ao usuário para qual marca é o vídeo e preencha (engine/marcas.py)")
        return errors, warns
    try:
        brand = load_brand(edl["brand"])
    except SystemExit as e:
        errors.append(str(e))
        return errors, warns
    ass = brand.get("assinatura") or {}
    if any(o["type"] == "assinatura" for o in edl.get("overlays", [])):
        if not ass.get("nome"):
            warns.append("overlay 'assinatura' mas a marca não tem assinatura.nome: remova o overlay ou preencha a marca")
        elif brand.get("segmento") == "saude" and not ass.get("registro"):
            warns.append(f"assinatura sem {ass.get('registro_tipo') or 'registro profissional'}: preencha "
                         f"brands/{edl['brand']}/brand.json → assinatura.registro. Publicidade em saúde exige identificação.")

    for i, b in enumerate(edl.get("broll", [])):
        if not resolve(b["src"], base).exists():
            errors.append(f"broll[{i}].src não encontrado: {b['src']}")

    audio = edl.get("audio", {})
    music = audio.get("music") or {}
    if music.get("src") and not resolve(music["src"], base).exists():
        errors.append(f"audio.music.src não encontrado: {music['src']}")
    for i, s in enumerate(audio.get("sfx", [])):
        if not resolve(s["src"], base).exists():
            errors.append(f"audio.sfx[{i}].src não encontrado: {s['src']}")

    cap = edl.get("captions", {})
    if cap.get("enabled", True) and not cap.get("words"):
        warns.append("legendas ligadas mas sem palavras (sem transcrição?)")
    words = cap.get("words", [])
    for a, b in zip(words, words[1:]):
        if b["start"] < a["start"] - 1e-3:
            errors.append(f"legendas fora de ordem perto de '{a['text']}' ({a['start']})")
            break
    return errors, warns


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    errs, warns = validate(sys.argv[1])
    for w in warns:
        print("AVISO:", w)
    for e in errs:
        print("ERRO:", e)
    print("OK" if not errs else f"{len(errs)} erro(s)")
    sys.exit(1 if errs else 0)
