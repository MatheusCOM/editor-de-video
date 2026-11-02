"""Utilitários compartilhados pelo engine."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Pasta de dados do usuário: modelos e marca próprios (sobrevive a atualizações do plugin)
USER_HOME = Path(os.environ.get("EDITOR_VIDEO_HOME", Path.home() / ".editor-video"))
TEMPLATES_DIR = ROOT / "templates"
TEMPLATE_DIRS = [USER_HOME / "templates", TEMPLATES_DIR]  # primeiro o do usuário


BRANDS_DIR = ROOT / "brands"
BRAND_DIRS = [USER_HOME / "brands", BRANDS_DIR]  # primeiro as do usuário
REGRAS_DIR = ROOT / "regras"
RENDER_DIR = ROOT / "render"
SCHEMAS_DIR = ROOT / "schemas"

FORMATS = {
    "9x16": (1080, 1920),
    "4x5": (1080, 1350),
    "1x1": (1080, 1080),
    "16x9": (1920, 1080),
}


def log(*args):
    print("[editor]", *args, file=sys.stderr, flush=True)


def run(cmd: list[str], capture: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd, capture_output=capture, text=True)
    if check and res.returncode != 0:
        tail = (res.stderr or "")[-3000:]
        raise RuntimeError(f"Comando falhou ({res.returncode}): {' '.join(cmd[:6])}...\n{tail}")
    return res


def require_bin(name: str):
    if shutil.which(name) is None:
        raise SystemExit(f"'{name}' não encontrado. Rode scripts/setup.sh ou instale {name}.")


def load_json(path: str | Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: str | Path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    return path


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_template(name: str) -> dict:
    """Carrega um modelo, resolvendo herança via campo "extends"."""
    path = template_dir(name) / "template.json"
    if not path.exists():
        disponiveis = ", ".join(list_templates())
        raise SystemExit(f"Modelo '{name}' não existe. Disponíveis: {disponiveis}")
    tpl = load_json(path)
    parent = tpl.get("extends")
    if parent:
        tpl = deep_merge(load_template(parent), {k: v for k, v in tpl.items() if k != "extends"})
    tpl["name"] = name
    return tpl


def template_dir(name: str) -> Path:
    for d in TEMPLATE_DIRS:
        if (d / name / "template.json").exists():
            return d / name
    return TEMPLATES_DIR / name


def list_templates() -> list[str]:
    names = set()
    for d in TEMPLATE_DIRS:
        names |= {p.parent.name for p in d.glob("*/template.json")}
    return sorted(names)


def list_brands() -> list[str]:
    names = set()
    for d in BRAND_DIRS:
        names |= {p.parent.name for p in d.glob("*/brand.json")}
    return sorted(names)


def brand_dir(slug: str) -> Path:
    if os.environ.get("EDITOR_BRAND_DIR"):
        return Path(os.environ["EDITOR_BRAND_DIR"])
    for d in BRAND_DIRS:
        if (d / slug / "brand.json").exists():
            return d / slug
    raise SystemExit(f"Marca '{slug}' não existe. Disponíveis: {', '.join(list_brands()) or '(nenhuma)'}. "
                     "Pergunte ao usuário qual é a marca do vídeo; para uma marca nova use a skill configurar-marca.")


def load_brand(slug: str) -> dict:
    d = brand_dir(slug)
    brand = load_json(d / "brand.json")
    # compatibilidade: campo antigo "medico" → "assinatura"
    if "assinatura" not in brand and brand.get("medico"):
        m = brand["medico"]
        brand["assinatura"] = {"nome": m.get("nome", ""), "registro_tipo": "CRM", "registro": m.get("crm", ""),
                               "extra": " · ".join(x for x in [f"RQE {m['rqe']}" if m.get("rqe") else "",
                                                                m.get("especialidade", "")] if x)}
    brand.setdefault("segmento", "geral")
    brand["_dir"] = str(d)
    brand["_slug"] = slug
    return brand


def regras_segmento(brand: dict) -> Path | None:
    p = REGRAS_DIR / f"{brand.get('segmento', 'geral')}.md"
    return p if p.exists() else None


def probe(path: str | Path) -> dict:
    require_bin("ffprobe")
    res = run([
        "ffprobe", "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(path),
    ])
    data = json.loads(res.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    info = {
        "path": str(Path(path).resolve()),
        "duration": float(data["format"].get("duration", 0)),
        "has_audio": a is not None,
        "has_video": v is not None,
    }
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        if "rotate" in (v.get("tags") or {}):
            rot = int(v["tags"]["rotate"])
        if abs(rot) in (90, 270):
            w, h = h, w
        num, den = (v.get("avg_frame_rate") or "30/1").split("/")
        fps = float(num) / float(den) if float(den) else 30.0
        info.update({
            "width": w, "height": h, "rotation": rot, "fps": round(fps, 3),
            "aspect": round(w / h, 4), "orientation": "vertical" if h > w else ("square" if h == w else "horizontal"),
            "vcodec": v.get("codec_name"),
        })
    if a:
        info.update({"sample_rate": int(a.get("sample_rate", 48000)), "channels": int(a.get("channels", 2))})
    return info


def fmt_time(t: float) -> str:
    m, s = divmod(max(t, 0), 60)
    return f"{int(m):02d}:{s:05.2f}"
