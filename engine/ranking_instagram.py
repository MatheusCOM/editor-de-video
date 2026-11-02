#!/usr/bin/env python3
"""Ranqueia os posts do Instagram (vídeos, imagens e carrosséis) a partir dos metadados do Instaloader.

Uso:
  python3 engine/ranking_instagram.py PASTA_DO_PERFIL [-o saida/] [--top 30]

PASTA_DO_PERFIL = pasta criada pelo Instaloader (arquivos *.json.xz ou *.json).
Gera em -o (padrão: PASTA/ranking/):
  ranking.csv   todos os vídeos com métricas
  ranking.md    top N com links, para escolher as referências
  baixar.sh     comandos `instaloader -- -CODIGO` para baixar só o top N

Cada tipo é ranqueado separadamente (vídeo × imagem × carrossel), porque o
Instagram não informa visualizações de fotos:
  vídeos        desempenho por views (se faltar, por interações)
  imagens/carrosséis  desempenho por interações (curtidas + comentários)

Métricas:
  views         video_play_count (reels) ou video_view_count
  engajamento   (curtidas + comentários) / views
  desempenho    views ÷ mediana de views dos ~10 vídeos mais próximos no tempo.
                1,0 = normal para a época; 3,0 = o triplo do usual. Compensa o
                crescimento da conta (vídeo antigo com poucas views pode ter ido bem).
"""
from __future__ import annotations

import argparse
import csv
import json
import lzma
import statistics
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path):
    raw = lzma.open(path).read() if path.suffix == ".xz" else path.read_bytes()
    return json.loads(raw)


def g(node, *keys):
    cur = node
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def parse(node):
    if not node.get("shortcode"):
        return None  # metadado do perfil, não de post
    typename = node.get("__typename") or ""
    is_video = bool(node.get("is_video")) or typename in ("GraphVideo", "XDTGraphVideo") \
        or node.get("product_type") in ("clips", "igtv")
    if "Sidecar" in typename or node.get("edge_sidecar_to_children"):
        tipo = "carrossel"
    elif is_video:
        tipo = "video"
    else:
        tipo = "imagem"
    views = node.get("video_play_count") or node.get("video_view_count") or g(node, "iphone_struct", "play_count")
    likes = g(node, "edge_media_preview_like", "count") or g(node, "edge_liked_by", "count") or 0
    comments = g(node, "edge_media_to_comment", "count") or g(node, "edge_media_to_parent_comment", "count") or 0
    caption = ""
    edges = g(node, "edge_media_to_caption", "edges") or []
    if edges:
        caption = (g(edges[0], "node", "text") or "").strip()
    ts = node.get("taken_at_timestamp") or node.get("date")
    date = datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, (int, float)) else None
    return {
        "codigo": node["shortcode"],
        "tipo": tipo,
        "url": f"https://www.instagram.com/{'reel' if tipo == 'video' else 'p'}/{node['shortcode']}/",
        "data": date.strftime("%Y-%m-%d") if date else "",
        "_ts": ts or 0,
        "duracao_s": round(node.get("video_duration") or 0, 1),
        "views": int(views) if views else None,
        "curtidas": int(likes),
        "comentarios": int(comments),
        "interacoes": int(likes) + int(comments),
        "legenda": caption.replace("\n", " ")[:140],
        "slides": len(g(node, "edge_sidecar_to_children", "edges") or []) or None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("-o", "--out")
    ap.add_argument("--top", type=int, default=30)
    a = ap.parse_args()
    pasta = Path(a.pasta)
    out = Path(a.out) if a.out else pasta / "ranking"
    out.mkdir(parents=True, exist_ok=True)

    posts, seen = [], set()
    for f in sorted(list(pasta.rglob("*.json.xz")) + list(pasta.rglob("*.json"))):
        if "ranking" in f.parts:
            continue
        try:
            data = load(f)
        except Exception:
            continue
        p = parse(data.get("node", data))
        if p and p["codigo"] not in seen:
            seen.add(p["codigo"])
            posts.append(p)
    if not posts:
        raise SystemExit(f"Nenhum post encontrado em {pasta} (procurei *.json.xz / *.json do Instaloader).")

    rotulos = {"video": "Vídeos", "imagem": "Imagens", "carrossel": "Carrosséis"}
    ranked_all, top_all, L = [], [], [f"# Ranking de posts — {pasta.name}", "",
                                      "Desempenho = métrica ÷ mediana dos ~10 posts do mesmo tipo mais próximos no tempo "
                                      "(1,0 = normal para a época). Cada tipo é comparado só com ele mesmo."]
    for tipo in ("video", "carrossel", "imagem"):
        grupo = sorted([p for p in posts if p["tipo"] == tipo], key=lambda p: p["_ts"])
        if not grupo:
            continue
        has_views = tipo == "video" and sum(1 for p in grupo if p["views"]) >= len(grupo) * 0.5
        key = "views" if has_views else "interacoes"
        for i, p in enumerate(grupo):
            viz = [q[key] for q in grupo[max(0, i - 5): i + 6] if q is not p and q[key]]
            med = statistics.median(viz) if viz else None
            p["metrica"] = key
            p["desempenho"] = round(p[key] / med, 2) if p[key] and med else None
            p["engajamento_%"] = round(100 * p["interacoes"] / p["views"], 2) if p.get("views") else None
        ranked = sorted(grupo, key=lambda p: (p["desempenho"] or 0, p[key] or 0), reverse=True)
        ranked_all += ranked
        top = ranked[: a.top]
        top_all += top
        L += ["", f"## {rotulos[tipo]} — {len(grupo)} posts · desempenho por **{key}**", ""]
        if tipo == "video":
            L += ["| # | desempenho | views | curtidas | coment. | eng. % | duração | data | legenda | link |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
            for i, p in enumerate(top, 1):
                L.append(f"| {i} | {p['desempenho'] or '–'} | {p['views'] or '–'} | {p['curtidas']} | {p['comentarios']} | "
                         f"{p['engajamento_%'] or '–'} | {p['duracao_s']}s | {p['data']} | {p['legenda'][:60]} | [abrir]({p['url']}) |")
        else:
            L += ["| # | desempenho | curtidas | coment. | " + ("slides | " if tipo == "carrossel" else "") + "data | legenda | link |",
                  "|---|---|---|---|" + ("---|" if tipo == "carrossel" else "") + "---|---|---|"]
            for i, p in enumerate(top, 1):
                sl = f"{p['slides'] or '–'} | " if tipo == "carrossel" else ""
                L.append(f"| {i} | {p['desempenho'] or '–'} | {p['curtidas']} | {p['comentarios']} | {sl}"
                         f"{p['data']} | {p['legenda'][:60]} | [abrir]({p['url']}) |")

    cols = ["tipo", "codigo", "data", "metrica", "desempenho", "views", "curtidas", "comentarios", "interacoes",
            "engajamento_%", "duracao_s", "slides", "url", "legenda"]
    with open(out / "ranking.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(ranked_all)
    (out / "ranking.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out / "baixar.sh").write_text(
        "#!/usr/bin/env bash\n# Baixa só os posts do topo do ranking (vídeos, imagens e carrosséis).\n"
        "# Rode na pasta onde quer os arquivos. Adicione --login=SUA_CONTA se o Instagram pedir login.\n"
        + "".join(f"instaloader --no-captions --no-video-thumbnails -- -{p['codigo']}   # {p['tipo']}\n" for p in top_all),
        encoding="utf-8")
    print("\n".join(L))
    print(f"\n→ {out/'ranking.csv'}  {out/'ranking.md'}  {out/'baixar.sh'}")


if __name__ == "__main__":
    main()
