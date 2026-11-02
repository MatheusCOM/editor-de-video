#!/usr/bin/env python3
"""Ranqueia vídeos do Instagram a partir dos metadados baixados pelo Instaloader.

Uso:
  python3 engine/ranking_instagram.py PASTA_DO_PERFIL [-o saida/] [--top 30]

PASTA_DO_PERFIL = pasta criada pelo Instaloader (arquivos *.json.xz ou *.json).
Gera em -o (padrão: PASTA/ranking/):
  ranking.csv   todos os vídeos com métricas
  ranking.md    top N com links, para escolher as referências
  baixar.sh     comandos `instaloader -- -CODIGO` para baixar só o top N

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
    is_video = node.get("is_video") or node.get("__typename") in ("GraphVideo", "XDTGraphVideo") \
        or node.get("product_type") == "clips"
    if not is_video:
        return None
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
        "url": f"https://www.instagram.com/reel/{node['shortcode']}/",
        "data": date.strftime("%Y-%m-%d") if date else "",
        "_ts": ts or 0,
        "duracao_s": round(node.get("video_duration") or 0, 1),
        "views": int(views) if views else None,
        "curtidas": int(likes),
        "comentarios": int(comments),
        "legenda": caption.replace("\n", " ")[:140],
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
        raise SystemExit(f"Nenhum vídeo encontrado em {pasta} (procurei *.json.xz / *.json do Instaloader).")

    posts.sort(key=lambda p: p["_ts"])
    has_views = sum(1 for p in posts if p["views"]) >= len(posts) * 0.5
    base_key = "views" if has_views else "curtidas"
    for i, p in enumerate(posts):
        viz = [q[base_key] for q in posts[max(0, i - 5): i + 6] if q is not p and q[base_key]]
        med = statistics.median(viz) if viz else None
        v = p[base_key]
        p["desempenho"] = round(v / med, 2) if v and med else None
        p["engajamento_%"] = round(100 * (p["curtidas"] + p["comentarios"]) / p["views"], 2) if p["views"] else None

    ranked = sorted(posts, key=lambda p: (p["desempenho"] or 0, p[base_key] or 0), reverse=True)
    cols = ["codigo", "data", "duracao_s", "views", "curtidas", "comentarios", "engajamento_%", "desempenho", "url", "legenda"]
    with open(out / "ranking.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(ranked)

    top = ranked[: a.top]
    L = [f"# Ranking de vídeos — {pasta.name}", "",
         f"{len(posts)} vídeos · ranqueado por **desempenho relativo de {base_key}** "
         f"(1,0 = normal para a época)" + ("" if has_views else " · ⚠️ sem contagem de views nos metadados; usando curtidas"),
         "", "| # | desempenho | views | curtidas | coment. | eng. % | duração | data | legenda | link |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for i, p in enumerate(top, 1):
        L.append(f"| {i} | {p['desempenho'] or '–'} | {p['views'] or '–'} | {p['curtidas']} | {p['comentarios']} | "
                 f"{p['engajamento_%'] or '–'} | {p['duracao_s']}s | {p['data']} | {p['legenda'][:60]} | [abrir]({p['url']}) |")
    (out / "ranking.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    (out / "baixar.sh").write_text(
        "#!/usr/bin/env bash\n# Baixa só os vídeos do topo do ranking. Rode na pasta onde quer os arquivos.\n"
        "# Adicione --login=SUA_CONTA se o Instagram pedir login.\n"
        + "".join(f"instaloader --no-captions --no-video-thumbnails -- -{p['codigo']}\n" for p in top),
        encoding="utf-8")
    print("\n".join(L[:12 + min(10, len(top))]))
    print(f"\n→ {out/'ranking.csv'}  {out/'ranking.md'}  {out/'baixar.sh'}")


if __name__ == "__main__":
    main()
