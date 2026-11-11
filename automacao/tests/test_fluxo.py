import asyncio
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest

from automacao.config import Config
from automacao.editor_agente import EditorSimulado
from automacao.fila import Fila
from automacao.instagram import ErroInstagram, Instagram
from automacao.interpretar import interpretar, interpretar_simples
from automacao.servico import Servico

TZ = ZoneInfo("America/Sao_Paulo")
# segunda-feira, 10/11/2025 10:00 em São Paulo
AGORA = datetime(2025, 11, 10, 10, 0, tzinfo=TZ)


class Notif:
    def __init__(self):
        self.msgs = []

    async def texto(self, chat_id, msg, botoes=None):
        self.msgs.append(("texto", chat_id, msg, [b.dado for b in botoes or []]))

    async def video(self, chat_id, arquivo, legenda, botoes=None):
        assert Path(arquivo).exists()
        self.msgs.append(("video", chat_id, legenda, [b.dado for b in botoes or []]))

    async def foto(self, chat_id, arquivo, legenda=""):
        self.msgs.append(("foto", chat_id, legenda, []))


class Pub:
    def __init__(self, falhas=0):
        self.chamadas, self.falhas = [], falhas

    def publicar_reel(self, arquivo, legenda):
        self.chamadas.append((arquivo, legenda))
        if self.falhas:
            self.falhas -= 1
            raise ErroInstagram("instabilidade")
        from automacao.instagram import Publicado
        return Publicado("999", "https://instagram.com/reel/abc")


@pytest.fixture
def bruto(tmp_path):
    p = tmp_path / "entrada.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=s=320x568:r=30:d=1",
                    "-pix_fmt", "yuv420p", str(p)], check=True)
    return p


def make(tmp_path, ensaio=True, pub=None):
    cfg = Config(dados=tmp_path / "dados", modo_ensaio=ensaio, usuarios_autorizados={1})
    fila = Fila(cfg.db_path)
    n = Notif()
    return Servico(cfg, fila, EditorSimulado(), n, pub), n, fila


# ------------------------------------------------------------------ interpretar
def test_interpretar_simples_dia_da_semana_e_hora():
    p = interpretar_simples("capa-fala, postar quinta 19h", TZ, "icg", AGORA)
    assert p.modelo == "capa-fala" and p.marca == "icg"
    assert p.publicar_em == datetime(2025, 11, 13, 19, 0, tzinfo=TZ)


def test_interpretar_simples_amanha_minutos_e_data():
    assert interpretar_simples("lista-motion amanhã 12h30", TZ, "icg", AGORA).publicar_em == \
        datetime(2025, 11, 11, 12, 30, tzinfo=TZ)
    assert interpretar_simples("sobrio 20/11 às 8:15", TZ, "icg", AGORA).publicar_em == \
        datetime(2025, 11, 20, 8, 15, tzinfo=TZ)


def test_interpretar_simples_falta_info_e_agora():
    p = interpretar_simples("edita esse aí", TZ, "icg", AGORA)
    assert p.falta() == ["modelo", "data"]
    p = interpretar_simples("motion-overlay, posta assim que aprovar", TZ, "icg", AGORA)
    assert p.modelo == "motion-overlay" and p.publicar_agora and p.falta() == []


def test_interpretar_ia_valida_resposta():
    class Bloco:
        type = "text"
        text = json.dumps({"modelo": "inventado", "marca": "icg", "publicar_em": "2025-11-13T19:00",
                           "publicar_agora": False, "observacoes": "sem música"})

    class Cliente:
        class messages:
            @staticmethod
            def create(**kw):
                assert kw["output_config"]["format"]["type"] == "json_schema"
                return type("R", (), {"content": [Bloco()]})()

    p = interpretar("qualquer", TZ, "icg", AGORA, cliente=Cliente())
    assert p.modelo is None  # modelo inexistente é descartado
    assert p.publicar_em == datetime(2025, 11, 13, 19, 0, tzinfo=TZ) and p.observacoes == "sem música"


def test_interpretar_ia_falha_cai_no_simples():
    class Cliente:
        class messages:
            @staticmethod
            def create(**kw):
                raise RuntimeError("sem rede")

    p = interpretar("capa-fala quinta 19h", TZ, "icg", AGORA, cliente=Cliente())
    assert p.modelo == "capa-fala"


# ------------------------------------------------------------------ fluxo completo
def test_fluxo_completo_ensaio(tmp_path, bruto):
    s, n, fila = make(tmp_path)

    async def go():
        job = await s.novo_pedido(1, bruto, "edita esse")
        assert job.estado == "aguardando_info" and "modelo" in n.msgs[-1][2]
        job = await s.responder_info(1, "capa-fala, amanhã 19h")
        assert job.estado == "na_fila" and job.modelo == "capa-fala"
        job = await s.processar_proximo()
        assert job.estado == "aguardando_aprovacao"
        tipo, _, legenda, botoes = n.msgs[-1]
        assert tipo == "video" and botoes == [f"aprovar:{job.id}", f"ajustar:{job.id}", f"descartar:{job.id}"]
        # ajuste
        await s.iniciar_ajuste(1, job.id)
        job = await s.receber_ajuste(1, "legenda maior")
        assert job.estado == "ajustando"
        job = await s.processar_proximo()
        assert job.estado == "aguardando_aprovacao" and "legenda maior" in job.roteiro
        # aprova → agendado no horário pedido (futuro)
        job = await s.aprovar(job.id)
        assert job.estado == "agendado"
        assert await s.publicar_vencidos(datetime.now(timezone.utc)) == []  # ainda não é hora
        feitos = await s.publicar_vencidos(job.publicar_em_dt() + timedelta(seconds=1))
        assert feitos and feitos[0].estado == "publicado" and feitos[0].permalink == "(ensaio)"
        assert "ENSAIO" in n.msgs[-1][2]

    asyncio.run(go())
    assert Path(fila.obter(1).bruto).exists() and "job_00001" in fila.obter(1).bruto


def test_publicacao_real_e_novas_tentativas(tmp_path, bruto):
    pub = Pub(falhas=1)
    s, n, fila = make(tmp_path, ensaio=False, pub=pub)

    async def go():
        job = await s.novo_pedido(1, bruto, "sobrio, assim que aprovar")
        job = await s.processar_proximo()
        job = await s.aprovar(job.id)
        agora = job.publicar_em_dt() + timedelta(seconds=1)
        r = await s.publicar_vencidos(agora)
        assert r[0].estado == "agendado" and "Nova tentativa" in n.msgs[-1][2]
        r = await s.publicar_vencidos(r[0].publicar_em_dt() + timedelta(seconds=1))
        assert r[0].estado == "publicado" and r[0].permalink.endswith("/abc")
        assert len(pub.chamadas) == 2

    asyncio.run(go())


def test_descartar_e_recuperar_interrompidos(tmp_path, bruto):
    s, n, fila = make(tmp_path)

    async def go():
        job = await s.novo_pedido(1, bruto, "capa-fala amanhã 9h")
        fila.atualizar(job.id, estado="editando")
        assert [j.estado for j in fila.recuperar_interrompidos()] == ["na_fila"]
        job = await s.descartar(job.id)
        assert job.estado == "descartado"

    asyncio.run(go())


def test_falha_na_edicao_vira_erro_e_refazer(tmp_path, bruto):
    s, n, fila = make(tmp_path)

    class Quebrado(EditorSimulado):
        async def editar(self, *a, **k):
            raise RuntimeError("render falhou")

    s.editor = Quebrado()

    async def go():
        job = await s.novo_pedido(1, bruto, "capa-fala amanhã 9h")
        job = await s.processar_proximo()
        assert job.estado == "erro" and "render falhou" in n.msgs[-1][2]
        s.editor = EditorSimulado()
        job = await s.refazer(job.id)
        assert job.estado == "na_fila"
        assert (await s.processar_proximo()).estado == "aguardando_aprovacao"

    asyncio.run(go())


# ------------------------------------------------------------------ Instagram (API simulada)
def test_instagram_fluxo_reels(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * 1234)
    status = iter(["IN_PROGRESS", "FINISHED"])
    vistos = []

    def handler(req: httpx.Request):
        vistos.append((req.method, req.url.host, req.url.path))
        if req.url.path.endswith("/17841/media") and req.method == "POST":
            body = dict(x.split("=") for x in req.content.decode().split("&"))
            assert body["media_type"] == "REELS" and body["upload_type"] == "resumable"
            return httpx.Response(200, json={"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v23.0/C1"})
        if req.url.host == "rupload.facebook.com":
            assert req.headers["file_size"] == "1234" and req.headers["Authorization"] == "OAuth TOK"
            return httpx.Response(200, json={"success": True})
        if req.url.path.endswith("/C1"):
            return httpx.Response(200, json={"status_code": next(status)})
        if req.url.path.endswith("/media_publish"):
            return httpx.Response(200, json={"id": "M1"})
        if req.url.path.endswith("/M1"):
            return httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/M1/"})
        return httpx.Response(404, json={"error": {"message": "?"}})

    ig = Instagram("17841", "TOK", http=httpx.Client(transport=httpx.MockTransport(handler)), dormir=lambda s: None)
    r = ig.publicar_reel(video, "legenda")
    assert r.media_id == "M1" and r.permalink.endswith("/M1/")
    assert ("POST", "rupload.facebook.com", "/ig-api-upload/v23.0/C1") in vistos


def test_instagram_erro_da_api(tmp_path):
    def handler(req):
        return httpx.Response(400, json={"error": {"type": "OAuthException", "message": "token expirado"}})

    ig = Instagram("1", "T", http=httpx.Client(transport=httpx.MockTransport(handler)), dormir=lambda s: None)
    with pytest.raises(ErroInstagram, match="token expirado"):
        ig.criar_container("x")


# ------------------------------------------------------------------ bot monta sem rede
def test_bot_monta(tmp_path):
    from automacao.bot import Bot, _html

    cfg = Config(telegram_token="123:ABC", usuarios_autorizados={1}, dados=tmp_path)
    fila = Fila(cfg.db_path)
    b = Bot(cfg, lambda n: Servico(cfg, fila, EditorSimulado(), n, None))
    assert len(b.app.handlers[0]) >= 8
    assert _html("modelo **capa-fala** <x>") == "modelo <b>capa-fala</b> &lt;x&gt;"


def test_opcoes_do_agente(tmp_path):
    from automacao.config import ROOT
    from automacao.editor_agente import SCHEMA_RESULTADO, EditorAgente

    cfg = Config(dados=tmp_path, teto_usd_por_job=2.5)
    o = EditorAgente(cfg)._opcoes(tmp_path, retomar="sess-1")
    assert o.cwd == str(tmp_path) and o.resume == "sess-1"
    assert o.plugins == [{"type": "local", "path": str(ROOT)}]
    assert o.model == "claude-opus-5-5" and o.max_budget_usd == 2.5
    assert o.output_format["schema"] is SCHEMA_RESULTADO
    assert (ROOT / ".claude-plugin" / "plugin.json").exists()


def test_notificador_nao_derruba_quando_telegram_recusa(tmp_path, capsys):
    from telegram.error import BadRequest

    from automacao.bot import NotificadorTelegram

    class BotFalso:
        async def send_message(self, *a, **k):
            raise BadRequest("Chat not found")

        async def send_video(self, *a, **k):
            raise BadRequest("Chat not found")

    class AppFalso:
        bot = BotFalso()

    n = NotificadorTelegram(AppFalso())
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")

    async def go():
        await n.texto(42, "oi")
        await n.video(42, video, "legenda", None)

    asyncio.run(go())  # não levanta
    err = capsys.readouterr().err
    assert "Iniciar" in err and "42" in err


def test_on_video_avisa_quando_nao_consegue_ler(tmp_path):
    from automacao.bot import Bot

    cfg = Config(telegram_token="123:ABC", usuarios_autorizados={1}, dados=tmp_path,
                 telegram_api_url="http://local:8081")
    fila = Fila(cfg.db_path)
    b = Bot(cfg, lambda n: Servico(cfg, fila, EditorSimulado(), n, None))
    respostas = []

    class Arq:
        async def download_to_drive(self, destino):
            raise PermissionError(13, "Permission denied")

    class Anexo:
        file_size, file_name, file_unique_id = 10, "v.mp4", "u1"

        async def get_file(self):
            return Arq()

    class Msg:
        video, document, caption, chat_id = Anexo(), None, "capa-fala, assim que aprovar", 1

        async def reply_text(self, t):
            respostas.append(t)

    class Upd:
        effective_user = type("U", (), {"id": 1})()
        effective_message = Msg()

    asyncio.run(b.on_video(Upd(), None))
    assert "permissão" in respostas[-1] and fila.listar() == []
