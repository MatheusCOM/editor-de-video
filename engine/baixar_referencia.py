#!/usr/bin/env python3
"""Baixa vídeos de referência a partir de links (Instagram, TikTok, YouTube, Facebook, Kwai...).

Uso:
  python3 engine/baixar_referencia.py LINK [LINK ...] [--out referencias/] [--cookies cookies.txt]
  python3 engine/baixar_referencia.py --lista links.txt

Para cada link salva em --out:
  <plataforma>_<autor>_<id>.mp4        vídeo (até 1080p)
  <plataforma>_<autor>_<id>.info.json  legenda, autor, data, duração, views, curtidas, comentários, URL

Links que pedem login (o Instagram costuma pedir): exporte os cookies do navegador
logado (extensão "Get cookies.txt LOCALLY") e passe --cookies cookies.txt. O arquivo
fica só na sua máquina. Nunca use senha aqui.

Uso responsável: vídeos de terceiros servem só para estudar o estilo de edição.
Ficam locais e não são publicados nem reaproveitados.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

from common import log

KEEP = ["id", "extractor_key", "webpage_url", "uploader", "uploader_id", "channel", "title", "description",
        "upload_date", "timestamp", "duration", "view_count", "like_count", "comment_count", "repost_count",
        "width", "height", "fps"]


def slug(s, n=24):
    s = re.sub(r"[^\w.-]+", "-", str(s or "").strip().lower()).strip("-.")
    return (s or "x")[:n]


def motivo(err: str) -> str:
    e = err.lower()
    if "tunnel connection failed" in e or "unable to connect to proxy" in e:
        return "rede bloqueada: o ambiente não alcança um domínio que o site usa (veja o status do proxy e libere o domínio)"
    if "not a bot" in e:
        return ("o YouTube bloqueia servidores de nuvem (\"confirme que não é um robô\"): use --cookies cookies.txt "
                "exportado do navegador logado no YouTube, ou baixe no seu computador")
    if "login required" in e or "rate-limit reached" in e or "requested content is not available" in e:
        return ("o Instagram limitou os acessos (ou exige login para este post): espere uns minutos e tente de novo; "
                "se persistir, use --cookies cookies.txt")
    if "login" in e or "cookies" in e or "rate-limit" in e or "authentication" in e:
        return "o site pediu login: use --cookies cookies.txt (exportado do navegador logado)"
    if "private" in e or "privad" in e:
        return "conteúdo privado"
    if "not available" in e or "removed" in e or "404" in e or "does not exist" in e:
        return "vídeo removido ou indisponível"
    if "403" in e or "tunnel" in e or "proxy" in e or "unable to download webpage" in e or "connection" in e:
        return "rede bloqueada ou o site recusou o acesso (libere o domínio ou rode no seu computador)"
    if "unsupported url" in e:
        return "link não suportado"
    if "no video formats" in e or "no video in this post" in e:
        return "o post não tem vídeo (é foto ou carrossel de imagens)"
    return err.strip().splitlines()[-1][:200]


class _Silencioso:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("links", nargs="*")
    ap.add_argument("--lista", help="arquivo .txt com um link por linha")
    ap.add_argument("--out", default="referencias")
    ap.add_argument("--cookies", help="cookies.txt (formato Netscape) para sites que pedem login")
    ap.add_argument("--pausa", type=float, default=3.0, help="segundos entre downloads (evita bloqueio)")
    ap.add_argument("--max-altura", type=int, default=1080, help="limite do lado menor do vídeo (1080 = Full HD)")
    a = ap.parse_args()

    try:
        import yt_dlp
    except ImportError:
        raise SystemExit("yt-dlp não instalado. Rode scripts/setup.sh (ou: pip install yt-dlp)")

    links = list(a.links)
    if a.lista:
        links += [l.strip() for l in Path(a.lista).read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.strip().startswith("#")]
    links = list(dict.fromkeys(links))  # remove repetidos, mantém a ordem
    if not links:
        raise SystemExit(__doc__)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    existentes = {}
    for j in out.glob("*.info.json"):
        try:
            m = json.loads(j.read_text(encoding="utf-8"))
            if (out / m["arquivo"]).exists():
                existentes[str(m["id"])] = str(out / m["arquivo"])
        except Exception:
            pass

    ok, falhas = [], []
    for i, url in enumerate(links):
        opts = {
            "quiet": True, "no_warnings": True, "noprogress": True, "logger": _Silencioso(),
            # melhor vídeo até 1080 no lado MENOR (1080x1920 vertical ok); prefere h264 se a resolução empatar
            "format": "bv*+ba/b",
            "format_sort": [f"res:{a.max_altura}", "vcodec:h264", "acodec:aac"],
            "merge_output_format": "mp4",
            "outtmpl": str(out / "%(extractor_key)s_%(uploader_id,uploader,channel)s_%(id)s.%(ext)s"),
            "restrictfilenames": True,
            "retries": 3,
            "socket_timeout": 30,
        }
        if a.cookies:
            opts["cookiefile"] = a.cookies
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                # o Instagram limita acessos de forma intermitente: tenta de novo com espera crescente
                for tentativa, espera in enumerate([0, 8, 20, 40]):
                    if espera:
                        log(f"[{i + 1}/{len(links)}] limite do site, nova tentativa em {espera}s…")
                        time.sleep(espera)
                    try:
                        info = ydl.extract_info(url, download=False)
                        break
                    except Exception as ex:  # noqa
                        msg = str(ex).lower()
                        temporario = "rate-limit" in msg or "login required" in msg or "429" in msg
                        if not temporario or tentativa == 3:
                            raise
                if info.get("_type") == "playlist":
                    entries = [e for e in (info.get("entries") or []) if e]
                    if not entries:
                        raise RuntimeError("no video in this post")
                    info = entries[0]
                vid = str(info.get("id"))
                if vid in existentes:
                    log(f"[{i + 1}/{len(links)}] já baixado: {url}")
                    ok.append({"url": url, "arquivo": existentes[vid], "repetido": True})
                    continue
                log(f"[{i + 1}/{len(links)}] baixando {url}")
                ydl.process_ie_result(info, download=True)
            plat = slug(info.get("extractor_key"), 12)
            autor = slug(info.get("channel") or info.get("uploader_id") or info.get("uploader"))
            # padroniza o nome final
            baixado = next(iter(sorted(out.glob(f"*_{vid}.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)), None)
            if not baixado:
                raise RuntimeError("download terminou sem gerar mp4")
            final = out / f"{plat}_{autor}_{vid}.mp4"
            if baixado != final:
                baixado.replace(final)
            meta = {k: info.get(k) for k in KEEP}
            meta["arquivo"] = final.name
            final.with_suffix(".info.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            existentes[vid] = str(final)
            ok.append({"url": url, "arquivo": str(final)})
        except Exception as e:  # noqa
            falhas.append({"url": url, "motivo": motivo(str(e))})
            log(f"[{i + 1}/{len(links)}] ✘ {url}: {falhas[-1]['motivo']}")
        if i < len(links) - 1:
            time.sleep(a.pausa)

    print(f"\n✔ {len(ok)} baixado(s) em {out}")
    for o in ok:
        print(f"  {o['arquivo']}" + ("  (já existia)" if o.get("repetido") else ""))
    if falhas:
        print(f"✘ {len(falhas)} falha(s):")
        for f in falhas:
            print(f"  {f['url']}\n    → {f['motivo']}")
    (out / "_ultimo_download.json").write_text(json.dumps({"ok": ok, "falhas": falhas}, ensure_ascii=False, indent=2),
                                               encoding="utf-8")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
