#!/usr/bin/env python3
"""Marcas (identidades visuais) disponíveis.

  python3 engine/marcas.py                 # lista as marcas
  python3 engine/marcas.py ver <slug>      # mostra a marca resolvida + guia + regras do segmento
  python3 engine/marcas.py nova <slug>     # cria ~/.editor-video/brands/<slug>/ a partir da marca neutra

Antes de editar qualquer vídeo, confirme com o usuário para qual marca ele é.
"""
import json
import shutil
import sys

from common import BRANDS_DIR, USER_HOME, brand_dir, list_brands, load_brand, regras_segmento


def listar():
    marcas = list_brands()
    if not marcas:
        print("Nenhuma marca cadastrada. Use: marcas.py nova <slug>")
        return
    for s in marcas:
        b = load_brand(s)
        c = b.get("colors", {})
        origem = "usuário" if str(brand_dir(s)).startswith(str(USER_HOME)) else "plugin"
        ass = b.get("assinatura") or {}
        print(f"- {s:<14} [{origem}] {b.get('name', '')} · segmento: {b.get('segmento')} · "
              f"acento {c.get('accent')} · fundo {c.get('background', c.get('primary'))} · "
              f"fontes {b['fonts']['title']['family']}/{b['fonts']['caption']['family']}"
              + (f" · assinatura: {ass.get('nome')} {ass.get('registro_tipo', '')} {ass.get('registro') or '(registro pendente)'}"
                 if ass.get("nome") else ""))


def ver(slug):
    b = load_brand(slug)
    print(json.dumps({k: v for k, v in b.items() if not k.startswith("_")}, ensure_ascii=False, indent=2))
    r = regras_segmento(b)
    print(f"\n# pasta: {b['_dir']}")
    print(f"# regras do segmento: {r}" if r else "# segmento sem regras específicas")


def nova(slug):
    dst = USER_HOME / "brands" / slug
    if dst.exists():
        raise SystemExit(f"Já existe: {dst}")
    shutil.copytree(BRANDS_DIR / "neutra", dst)
    b = json.loads((dst / "brand.json").read_text(encoding="utf-8"))
    b["_comment"] = f"Marca '{slug}'. Preencha com a identidade do cliente (skill configurar-marca)."
    b["name"] = slug
    (dst / "brand.json").write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        listar()
    elif a[0] == "ver" and len(a) > 1:
        ver(a[1])
    elif a[0] == "nova" and len(a) > 1:
        nova(a[1])
    else:
        raise SystemExit(__doc__)
