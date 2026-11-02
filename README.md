# Editor de vídeo

Plugin do Claude Code feito para o **Instituto Clayton Guimarães**.

Edição de vídeo automática por **modelos**, feita pelo Claude. Você envia o vídeo bruto, diz o modelo ("edita no modelo reels") e recebe o vídeo pronto: cortes de silêncio e retakes, legendas animadas em português, zooms, motion graphics, CTA, color grade, áudio normalizado e exportação em 9:16, 4:5 e 1:1.

Os modelos podem ser criados por **engenharia reversa**: mande um vídeo de referência e o Claude disseca a edição (ritmo, legendas, zooms, cor, áudio, estrutura) e transforma em modelo reutilizável.

## Instalação (Claude Code: desktop, CLI ou web)

Pré-requisitos na máquina: **ffmpeg**, **Python 3.10+** e **Node.js 18+**.

```bash
/plugin marketplace add <dono>/<repo>
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
| "Usa a minha marca" + logo/cores/fontes | `configurar-marca` |

## Modelos incluídos

- **reels**: 9:16, cortes secos, legenda palavra por palavra, zoom de jump cut, título-gancho, barra de progresso.
- **clinico**: identidade do Instituto (Sora leve, dourado só no essencial, assinatura com CRM, CTA sóbrio) e regras de publicidade médica. É o modelo-base até chegarem os modelos feitos das referências do Dr. Clayton.
- **anuncio-meta**: herda reels; gancho em 3s, legenda em caixa, CTA final, saídas 9:16 + 4:5 + 1:1, zonas seguras do Meta.

Modelos e marca **do usuário** ficam em `~/.editor-video/` (`templates/`, `brand/`, `components/`) e têm prioridade sobre os do plugin; atualizações do plugin não apagam essa pasta. Para distribuir um modelo para todo mundo, coloque-o em `templates/` deste repositório e publique.

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
- `brand/`: marca do Instituto Clayton Guimarães (Sora, Manrope, JetBrains Mono; licença OFL). Uma marca neutra de exemplo fica em `brand-exemplos/`.
- `schemas/edl.schema.json`: formato do EDL

Para rodar à mão:
```bash
python3 engine/edl.py draft --source bruto.mp4 --template reels --transcript job/transcript.json --out job/edl.json
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
