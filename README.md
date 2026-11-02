# Editor de vídeo

Plugin do Claude Code para edição automática de vídeos **multi-marca**: qualquer identidade visual, qualquer cliente. Criado para o Instituto Clayton Guimarães (marca `icg` incluída).

Edição de vídeo automática por **modelos**, feita pelo Claude. Você envia o vídeo bruto, diz o modelo ("edita no modelo reels") e recebe o vídeo pronto: cortes de silêncio e retakes, legendas animadas em português, zooms, motion graphics, CTA, color grade, áudio normalizado e exportação em 9:16, 4:5 e 1:1.

Os modelos podem ser criados por **engenharia reversa**: mande um vídeo de referência e o Claude disseca a edição (ritmo, legendas, zooms, cor, áudio, estrutura) e transforma em modelo reutilizável.

## Instalação (Claude Code: desktop, CLI ou web)

Pré-requisitos na máquina: **ffmpeg**, **Python 3.10+** e **Node.js 18+**.

```bash
/plugin marketplace add MatheusCOM/editor-de-video
```
```bash
/plugin install editor-de-video@editor-de-video
```
Depois, peça ao Claude: *"roda o setup do editor de vídeo"* (ele executa `scripts/setup.sh`, que instala Remotion, faster-whisper e OpenCV e baixa o modelo de transcrição).

> Na primeira transcrição, o modelo Whisper é baixado de `huggingface.co`. Se a rede bloquear esse domínio, as legendas ficam indisponíveis até liberar.

## Como usar (é só conversar)

| Você diz | Skill |
|---|---|
| "Edita esse vídeo no modelo reels" + arquivo | `editar-video` |
| "Faz um anúncio com esse bruto, CTA: Compre com 30% off" | `editar-video` |
| "Legenda maior e tira o zoom do segundo 12" | `editar-video` (ajuste) |
| "Cria um modelo igual a esse vídeo" + referência | `criar-modelo` |
| "Novo cliente / usa a minha marca" + guia, logo, cores, fontes | `configurar-marca` |

## Marcas (identidade visual)

Antes de editar, o Claude **pergunta para qual marca é o vídeo**. Se for uma marca nova, ele pede a identidade (guia de marca, logo, cores, fontes, segmento, assinatura) e cadastra. Todos os modelos se adaptam à marca escolhida.

- `brands/icg/`: Instituto Clayton Guimarães (segmento saúde)
- `brands/neutra/`: marca neutra, base para marcas novas
- Marcas de clientes ficam em `~/.editor-video/brands/<slug>/`. `python3 engine/marcas.py` lista todas.
- Regras por segmento em `regras/` (ex.: `regras/saude.md`: publicidade em saúde, registro profissional).

## Modelos incluídos (todos neutros de marca)

- **capa-fala**: capa fixa no topo (título tipo thumbnail) + pessoa falando embaixo; jump cuts discretos, legenda pequena. Engenharia reversa de um reel do Dr. Clayton.
- **lista-motion**: "N coisas que…" com itens numerados, cartões animados (prints, imagens, texto) e cenas de tela cheia; cortes rápidos com punch-in. Engenharia reversa de um reel de George Vitko.
- **motion-overlay**: só motion por cima de um vídeo **já editado** (sem cortar, sem nova legenda): títulos, etiquetas sincronizadas com a fala, rótulos e assinatura nas zonas livres da tela.
- **sobrio**: elegante e discreto, um único acento por tela, assinatura e CTA em tela cheia.
- **reels**: 9:16, cortes secos, legenda palavra por palavra, zoom de jump cut, título-gancho, barra de progresso.
- **anuncio-meta**: herda reels; gancho em 3s, legenda em caixa, CTA final, saídas 9:16 + 4:5 + 1:1, zonas seguras do Meta.

Modelos e marcas **do usuário** ficam em `~/.editor-video/` (`templates/`, `brands/`, `components/`) e têm prioridade sobre os do plugin; atualizações do plugin não apagam essa pasta.

## Referências por link

Cole os links no chat ("cria um modelo a partir desses vídeos: …") e o Claude baixa, analisa e monta o modelo. Funciona com Instagram, TikTok, YouTube, Facebook e Kwai, via [yt-dlp](https://github.com/yt-dlp/yt-dlp). À mão:
```bash
python3 engine/baixar_referencia.py LINK1 LINK2 --out referencias/lote1
```
- O ambiente precisa alcançar os sites. Na nuvem do Claude, libere em Network access: `*.instagram.com`, `*.cdninstagram.com`, `*.fbcdn.net`, `*.tiktok.com`, `*.tiktokcdn.com`, `*.tiktokv.com`, `*.youtube.com`, `*.googlevideo.com`, `*.ytimg.com`.
- O Instagram às vezes pede login: exporte `cookies.txt` do navegador (extensão "Get cookies.txt LOCALLY") e use `--cookies cookies.txt`. Nunca use senha.
- Vídeos de terceiros são usados só para estudar o estilo: ficam locais e não são publicados.

## Escolher referências no Instagram (por desempenho)

1. No computador, com Python, instale o Instaloader e baixe **só os metadados** de todos os posts (vídeos, imagens e carrosséis, sem os arquivos). Use uma conta secundária no `--login`:
```bash
pip install instaloader
```
```bash
instaloader --login=CONTA --reels --no-pictures --no-videos --no-captions PERFIL
```
2. Ranqueie (ou mande a pasta `PERFIL/` para o Claude):
```bash
python3 engine/ranking_instagram.py PERFIL
```
   Gera `PERFIL/ranking/ranking.md`, com o top 30 de cada tipo por **desempenho relativo** (vídeos por views; imagens e carrosséis por curtidas + comentários, porque o Instagram não informa views de foto), e `baixar.sh`, com os comandos para baixar só os escolhidos.
3. Baixe só as referências escolhidas (`instaloader -- -CODIGO`) e peça: "cria um modelo a partir desses vídeos".

## Como funciona

```
bruto.mp4 ─► probe ─► transcribe (Whisper, PT-BR, tempo por palavra)
          ─► edl.py draft  (regras mecânicas do modelo → edl.json)
          ─► Claude edita edl.json (retakes, gancho, ênfases, motion graphics, CTA)
          ─► edl.py sync ─► validate ─► render --preview (frames para conferir)
          ─► render: ffmpeg (cortes, cor, áudio, loudnorm) + Remotion (enquadramento,
             zooms, legendas, motion graphics) ─► out/<bruto>_<modelo>_<formato>.mp4
```

- `engine/`: scripts Python (`probe`, `transcribe`, `edl`, `focus`, `validate_edl`, `render`, `analyze`, `compare`, `templates`)
- `render/`: projeto Remotion (React) com os componentes visuais
- `templates/<nome>/`: `template.json` (parâmetros) + `REGRAS.md` (regras editoriais que o Claude segue)
- `brands/<slug>/`: marcas (`brand.json` + fontes + logo); `regras/`: regras por segmento
- `schemas/edl.schema.json`: formato do EDL

Para rodar à mão:
```bash
python3 engine/edl.py draft --source bruto.mp4 --template reels --brand icg --transcript job/transcript.json --out job/edl.json
```
```bash
python3 engine/render.py job/edl.json --preview
```
```bash
python3 engine/render.py job/edl.json
```

## Licenças
- **Remotion** é gratuito para pessoas físicas e empresas com até 3 funcionários. Acima disso exige [licença da empresa](https://www.remotion.dev/license).
- Fontes Sora, Manrope, JetBrains Mono, Montserrat e Inter: SIL Open Font License.
