"""Publicação de Reels pela API oficial do Instagram (Graph API, conta profissional ligada a uma Página).

Fluxo: criar container REELS com upload resumível → enviar o arquivo para rupload.facebook.com →
aguardar processamento (status_code FINISHED) → media_publish → buscar o permalink.
Não precisa hospedar o vídeo em URL pública.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import httpx


class ErroInstagram(RuntimeError):
    pass


@dataclass
class Publicado:
    media_id: str
    permalink: str | None


class Instagram:
    def __init__(self, ig_user_id: str, token: str, versao: str = "v23.0", http: httpx.Client | None = None,
                 espera_s: float = 5.0, limite_espera_s: float = 600.0, dormir=time.sleep):
        self.ig = ig_user_id
        self.token = token
        self.v = versao
        self.http = http or httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0))
        self.espera_s = espera_s
        self.limite_espera_s = limite_espera_s
        self.dormir = dormir

    @property
    def graph(self) -> str:
        return f"https://graph.facebook.com/{self.v}"

    def _ok(self, r: httpx.Response) -> dict:
        try:
            dados = r.json()
        except ValueError:
            dados = {}
        if r.status_code >= 400 or "error" in dados:
            err = dados.get("error", {})
            raise ErroInstagram(f"{r.status_code} {err.get('type', '')}: {err.get('message', r.text[:300])}")
        return dados

    def criar_container(self, legenda: str, capa_ms: int | None = None) -> tuple[str, str]:
        params = {"media_type": "REELS", "upload_type": "resumable", "caption": legenda,
                  "share_to_feed": "true", "access_token": self.token}
        if capa_ms is not None:
            params["thumb_offset"] = str(capa_ms)
        d = self._ok(self.http.post(f"{self.graph}/{self.ig}/media", data=params))
        if "id" not in d or "uri" not in d:
            raise ErroInstagram(f"resposta inesperada ao criar container: {d}")
        return d["id"], d["uri"]

    def enviar_arquivo(self, uri: str, arquivo: Path):
        dados = arquivo.read_bytes()
        r = self.http.post(uri, content=dados, headers={
            "Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(len(dados))})
        d = self._ok(r)
        if d.get("success") is False:
            raise ErroInstagram(f"upload recusado: {d}")

    def aguardar(self, container_id: str):
        gasto = 0.0
        while True:
            d = self._ok(self.http.get(f"{self.graph}/{container_id}",
                                       params={"fields": "status_code,status", "access_token": self.token}))
            st = d.get("status_code")
            if st == "FINISHED":
                return
            if st in ("ERROR", "EXPIRED"):
                raise ErroInstagram(f"processamento do vídeo falhou: {d.get('status', st)}")
            if gasto >= self.limite_espera_s:
                raise ErroInstagram("o Instagram demorou demais para processar o vídeo")
            self.dormir(self.espera_s)
            gasto += self.espera_s

    def publicar_container(self, container_id: str) -> str:
        d = self._ok(self.http.post(f"{self.graph}/{self.ig}/media_publish",
                                    data={"creation_id": container_id, "access_token": self.token}))
        return d["id"]

    def permalink(self, media_id: str) -> str | None:
        try:
            d = self._ok(self.http.get(f"{self.graph}/{media_id}",
                                       params={"fields": "permalink", "access_token": self.token}))
            return d.get("permalink")
        except ErroInstagram:
            return None

    def publicar_reel(self, arquivo: Path, legenda: str) -> Publicado:
        cid, uri = self.criar_container(legenda)
        self.enviar_arquivo(uri, arquivo)
        self.aguardar(cid)
        mid = self.publicar_container(cid)
        return Publicado(mid, self.permalink(mid))

    def verificar(self) -> str:
        """Confere token e conta (usado no /status). Retorna o @ da conta."""
        d = self._ok(self.http.get(f"{self.graph}/{self.ig}", params={"fields": "username", "access_token": self.token}))
        return d.get("username", "?")


def renovar_token_longo(app_id: str, app_secret: str, token: str, versao: str = "v23.0",
                        http: httpx.Client | None = None) -> tuple[str, int | None]:
    """Troca um token de usuário por um de longa duração (~60 dias). Tokens de usuário do sistema (Business
    Manager) não expiram e dispensam isto — é o recomendado no DEPLOY.md."""
    http = http or httpx.Client(timeout=30.0)
    r = http.get(f"https://graph.facebook.com/{versao}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": app_id, "client_secret": app_secret, "fb_exchange_token": token})
    d = r.json()
    if r.status_code >= 400 or "access_token" not in d:
        raise ErroInstagram(f"não consegui renovar o token: {d.get('error', d)}")
    return d["access_token"], d.get("expires_in")
