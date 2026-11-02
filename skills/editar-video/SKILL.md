---
name: editar-video
description: Edita um vídeo bruto automaticamente seguindo um modelo (reels, anúncio Meta Ads ou modelos criados a partir de referências) — cortes de silêncio e retakes, legendas animadas em português, zooms, motion graphics, CTA, música, color grade e exportação em 9:16/4:5/1:1. Use quando o usuário enviar um vídeo bruto e pedir para editar, "deixar no modelo X", "fazer um reels/anúncio", "cortar e legendar", ou ajustar um vídeo já editado por este sistema.
---

# Editar vídeo por modelo

Você é o editor. Os scripts fazem o trabalho mecânico; **você toma as decisões editoriais** escrevendo o `edl.json`.

`ROOT` = a pasta do plugin, dois níveis acima deste SKILL.md (o diretório-base da skill aparece quando ela é carregada; ROOT = `<base>/../..`). Todos os comandos abaixo são `python3 $ROOT/engine/<script>.py`.

## 0. Antes de começar
- Na primeira vez em uma máquina, rode `bash $ROOT/scripts/setup.sh` (é idempotente).
- Liste os modelos: `python3 $ROOT/engine/templates.py`. Se o usuário não disse qual modelo usar, mostre a lista e pergunte.
- **Conteúdo médico**: este plugin é usado pelo Instituto Clayton Guimarães. Siga as regras de publicidade médica descritas em `templates/clinico/REGRAS.md` em QUALQUER modelo: identificação com nome + CRM (+ RQE), sem promessa de resultado, sem sensacionalismo, cuidado com antes/depois e dados de pacientes.
- Pasta de trabalho: crie `./edicoes/<nome-do-video>/` no diretório atual (ou onde o usuário pedir). Tudo do job fica ali.

## 1. Medir e transcrever
```bash
python3 $ROOT/engine/probe.py BRUTO.mp4
python3 $ROOT/engine/transcribe.py BRUTO.mp4 -o JOB/transcript.json
```
- Se a transcrição falhar por rede (huggingface.co bloqueado), avise o usuário e siga **sem legendas** (o rascunho corta por silêncio), ou peça para liberar o domínio.
- Vídeo sem fala (produto, b-roll com música): pule a transcrição; use um modelo cujo `cut.mode` seja `"none"`, ou ajuste `segments` à mão olhando os frames (`analyze.py` ajuda a ver os planos).

## 2. Rascunho automático
```bash
python3 $ROOT/engine/edl.py draft --source BRUTO.mp4 --template MODELO --transcript JOB/transcript.json --out JOB/edl.json
```
Isso aplica as regras mecânicas do modelo (cortes de pausa, hesitações, zoom de jump cut, overlays padrão, enquadramento por rosto) e imprime a **linha do tempo** (`JOB/timeline.txt`).

## 3. Decisões editoriais (o seu trabalho)
Leia **`REGRAS.md` do modelo** (caminho em `templates.py MODELO`; se ele tiver `extends`, leia também as regras do modelo-pai) e a transcrição. Depois edite:

| O quê | Onde | Tempo |
|---|---|---|
| Erros de transcrição, nomes, números | `transcript.json` → `words[].text` | bruto |
| Palavras de destaque / emoji na legenda | `transcript.json` → `words[].emphasis: true`, `words[].emoji` | bruto |
| Retakes, frases ruins, ordem (gancho primeiro) | `edl.json` → `segments` (a ordem da lista = ordem final) | bruto |
| Acelerar trecho | `segments[].speed` (ex.: 1.2) | — |
| Zooms de ênfase | `edl.json` → `zooms` (`smooth`/`punch`/`slow`, `scale`) | **saída** |
| Textos e motion graphics | `edl.json` → `overlays` | **saída** |
| B-roll / imagens do usuário | `edl.json` → `broll` (`full`/`pip`/`split_top`) | **saída** |
| Música / efeitos | `edl.json` → `audio.music`, `audio.sfx`, `audio.sfx_on_cuts` | **saída** |
| Cor | `edl.json` → `grade` | — |

**Depois de mexer em `segments` ou `transcript.json`, SEMPRE rode** `python3 $ROOT/engine/edl.py sync JOB/edl.json`. Ele recalcula a duração, as legendas e os zooms automáticos e imprime a fala já em **tempo de saída**. Use esses tempos para posicionar zooms e overlays.

Placeholders `{{...}}` nos overlays do modelo (ex.: `{{GANCHO}}`, `{{CTA_TITULO}}`) **precisam** ser preenchidos; o validador bloqueia o render enquanto estiverem lá.

### Catálogo de overlays (`type` → `props`)
- `title`: `text` (use `*palavra*` para destacar), `position` (`top`/`center`/`bottom` ou 0–1), `size` (fração da largura, ~0.08), `bg` (`"brand"`, cor ou omitido = só contorno), `animation` (`pop`/`slide`/`typewriter`), `uppercase`, `color`, `rotate`
- `text_pop`: igual a `title`, centralizado e maior (palavra/número de impacto)
- `lower_third`: `title`, `subtitle`, `color`, `position`
- `cta`: `title`, `subtitle`, `button` (texto ou `false`), `mode` (`overlay`/`full`), `bg`, `show_logo`, `keep_captions`
- `checklist`: `title`, `items` [..], `icon`, `position`, `step` (s entre itens)
- `counter`: `from`, `to`, `prefix`, `suffix`, `decimals`, `label`, `position`, `size`
- `emoji`: `emoji`, `x`, `y` (0–1), `size`, `rotate`
- `arrow`: `x`, `y` (ponta), `angle` (graus), `length`, `color`
- `image`: `src` (arquivo do usuário ou `brand:arquivo`), `x`, `y`, `width`, `animation` (`pop`/`fade`), `rounded`, `shadow`
- `logo`: `position` (`top-right`…), `size`, `opacity`
- `progress`: `position` (`top`/`bottom`), `height`, `color`
- `flash`: `color`, `intensity` (transição branca de ~0.15s num corte)
- `rotulo`: `text`, `position`, `align`, `size`, `color` (texto mono pequeno em caixa alta: datas, medidas, "PROTOCOLO · SEMANA 6")
- `assinatura`: nome + CRM + RQE do médico (lidos de `brand.json → medico`; props podem sobrescrever `nome`, `crm`, `rqe`, `especialidade`), `position`
- Componentes customizados de modelos criados a partir de referência: veja o `REGRAS.md` do modelo.

Qualquer overlay aceita `anchor` (`start`/`end`/`full`) + `duration`/`offset` em vez de `start`/`end`, e `props.formats` para aparecer só em certos formatos.

## 4. Validar e pré-visualizar
```bash
python3 $ROOT/engine/validate_edl.py JOB/edl.json
python3 $ROOT/engine/render.py JOB/edl.json --preview            # 5 frames por formato
python3 $ROOT/engine/render.py JOB/edl.json --preview --at 0.5 3.2 12
```
**Abra as folhas `JOB/preview/folha_<formato>.jpg` e olhe de verdade**: texto cortado ou fora da zona segura, legenda colidindo com motion graphics, enquadramento cortando o rosto, legibilidade. Corrija e repita. Enquadramento errado: ajuste `segments[i].focus` (`x`,`y` 0–1 do ponto que deve ficar centralizado) e marque `"focus_locked": true`.

## 5. Render final e entrega
```bash
python3 $ROOT/engine/render.py JOB/edl.json
```
Saída: `JOB/out/<bruto>_<modelo>_<formato>.mp4` (H.264 + AAC, −14 LUFS por padrão). Leva alguns minutos por formato. Entregue os arquivos (no app, envie com a ferramenta de arquivos) com um resumo curto das decisões: o que cortou, gancho escolhido, overlays, duração final. Também ofereça ajustes.

## Ajustes pedidos pelo usuário
Traduza o pedido para mudanças no EDL ou na transcrição, rode `sync` → `--preview` → render. Exemplos: "legenda maior" → `captions.size`; "tira o zoom do segundo 12" → remova o item de `zooms`; "começa direto na frase X" → reordene ou remova `segments`; "mais rápido" → reduza `cut.max_pause` (refaça o draft) ou use `speed`. Se o pedido for uma **preferência permanente** do modelo, proponha atualizar `template.json`/`REGRAS.md` do modelo.

## Marca
A identidade visual vem de `brand.json` (em `~/.editor-video/brand/` se existir, senão a do plugin). Para configurar: skill `configurar-marca`.
