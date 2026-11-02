#!/usr/bin/env python3
"""Lista os modelos disponíveis (do usuário e do plugin) e onde estão.

Uso: python3 engine/templates.py [nome]   # sem nome: lista; com nome: mostra o modelo resolvido
"""
import json
import sys

from common import BRAND_DIR, USER_HOME, list_templates, load_json, load_template, template_dir

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(json.dumps(load_template(sys.argv[1]), ensure_ascii=False, indent=2))
        regras = template_dir(sys.argv[1]) / "REGRAS.md"
        print(f"\n# regras: {regras}" if regras.exists() else "\n# (sem REGRAS.md)")
    else:
        print(f"# pasta do usuário: {USER_HOME}  ·  marca em uso: {BRAND_DIR}")
        for n in list_templates():
            d = template_dir(n)
            desc = load_json(d / "template.json").get("description", "")
            origem = "usuário" if str(d).startswith(str(USER_HOME)) else "plugin"
            print(f"- {n:<22} [{origem}] {desc}")
