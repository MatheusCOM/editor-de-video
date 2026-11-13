---
name: editar-video
description: Edita um vídeo bruto automaticamente seguindo um modelo (reels, anúncio Meta Ads ou modelos criados a partir de referências) — cortes de silêncio e retakes, legendas animadas em português, zooms, motion graphics, CTA, música, color grade e exportação em 9:16/4:5/1:1. Use quando o usuário enviar um vídeo bruto e pedir para editar, "deixar no modelo X", "fazer um reels/anúncio", "cortar e legendar", ou ajustar um vídeo já editado por este sistema.
---

# Editar vídeo por modelo

Você é o editor. Os scripts fazem o trabalho mecânico; **você toma as decisões editoriais** escrevendo o `edl.json`.

`ROOT` = a pasta do plugin, dois níveis acima deste SKILL.md (o diretório-base da skill aparece quando ela é carregada; ROOT = `<base>/../..`). Todos os comandos abaixo são `python3 $ROOT/engine/<script>.py`.

## 0. Antes de começar
- Na primeira vez em uma máquina, rode `bash $ROOT/scripts/setup.sh` (é idempotente).
- **Marca primeiro: nunca edite sem saber para qual identidade visual é o vídeo.** Liste as marcas com `python3 $ROOT/engine/marcas.py` e pergunte ao usuário qual usar (mesmo que só haja uma, confirme). Se for uma marca nova, **pare e rode o onboarding da skill `configurar-marca`** antes de editar: peça o guia de marca/logo/cores/fontes de quem vai produzir.
- Leia a marca escolhida: `python3 $ROOT/engine/marcas.py ver <slug>`. O campo `guia` traz regras visuais e de tom da marca, que valem em qualquer modelo e **têm prioridade** sobre o REGRAS.md do modelo. Se a marca tiver segmento com regras (ex.: `saude` → `$ROOT/regras/saude.md`: publicidade médica, registro profissional, sem promessa de resultado), leia e siga também.
- Liste os modelos: `python3 $ROOT/engine/templates.py`. Se o usuário não disse qual modelo usar, mostre a lista e pergunte. Os modelos são neutros: a mesma edição muda de cara conforme a marca.
- Pasta de trabalho: crie `./edicoes/<nome-do-video>/` no diretório atual (ou onde o usuário pedir). Tudo do job fica ali.

**Vídeo já editado** ("só adiciona motion"): use o modelo `motion-overlay` e leia o REGRAS.md dele. Antes, rode `analyze.py --transcribe` e olhe as folhas para achar rosto, legenda gravada e zonas livres.

## 1. Medir e transcrever
```bash
python3 $ROOT/engine/probe.py BRUTO.mp4
python3 $ROOT/engine/transcribe.py BRUTO.mp4 -o JOB/transcript.json
```
- Se a transcrição falhar por rede (huggingface.co bloqueado), avise o usuário e siga **sem legendas** (o rascunho corta por silêncio), ou peça para liberar o domínio.
- Vídeo sem fala (produto, b-roll com música): pule a transcrição; use um modelo cujo `cut.mode` seja `"none"`, ou ajuste `segments` à mão olhando os frames (`analyze.py` ajuda a ver os planos).

## 2. Rascunho automático
```bash
python3 $ROOT/engine/edl.py draft --source BRUTO.mp4 --template MODELO --brand MARCA --transcript JOB/transcript.json --out JOB/edl.json
```
Isso aplica as regras mecânicas do modelo (cortes de pausa, hesitações, zoom de jump cut, overlays padrão, enquadramento por rosto) e imprime a **linha do tempo** (`JOB/timeline.txt`).

## 3. Decisões editoriais (o seu trabalho)

### Cortes: só técnicos (vale para todos os modelos e tem prioridade sobre o REGRAS.md deles)
- **Pode cortar sem perguntar**: pausas e silêncios, hesitações ("é…", "ãh", "hum"), respiração e **retakes** (a mesma frase dita de novo logo em seguida porque a pessoa errou: fica a última versão completa).
- **Não corte conteúdo sem o usuário pedir**: nenhuma frase, ideia, exemplo, introdução ou despedida sai do vídeo, mesmo que pareça fraca, longa ou que vá contra as regras do segmento (ex.: promessa de resultado em saúde). Se foi falado, há um motivo; quem decide é o usuário, depois de ver o vídeo editado.
- Também não reordene a fala sem pedir (ex.: trazer o gancho do meio para o começo).
- O que você cortaria ou moveria vira **sugestão**: liste com o tempo e o motivo (no modo automático, em `pendencias`; ex.: "0:42–0:47 'garanto que você emagrece': promessa de resultado (CFM). Cortar?"). Também não reforce esse trecho na tela (legenda normal, sem motion).
- Ao conferir, compare a transcrição com a fala de saída do `sync`: toda frase do bruto tem que estar lá (exceto retakes).

### Legendas
- A palavra que está sendo falada fica destacada (`captions.style`: `pop`, `box` ou `karaoke`). Não use `plain`.
Leia **`REGRAS.md` do modelo** (caminho em `templates.py MODELO`; se ele tiver `extends`, leia também as regras do modelo-pai) e a transcrição. Depois edite:

| O quê | Onde | Tempo |
|---|---|---|
| Erros de transcrição, nomes, números | `transcript.json` → `words[].text` | bruto |
| Palavras de destaque / emoji na legenda | `transcript.json` → `words[].emphasis: true`, `words[].emoji` | bruto |
| Retakes (frases ruins/ordem só se o usuário pedir) | `edl.json` → `segments` (a ordem da lista = ordem final) | bruto |
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
- `rotulo`: `text`, `position`, `align`, `size`, `color`, `bg` (`false` tira o fundo escuro) (texto mono pequeno em caixa alta: datas, medidas, "PROTOCOLO · SEMANA 6")
- `assinatura`: nome + registro profissional da marca (`brand.json → assinatura`: `nome`, `registro_tipo`, `registro`, `extra`, `cargo`; props podem sobrescrever), `position`. O draft remove esse overlay se a marca não tiver assinatura.
- `capa`: faixa fixa no topo (use com `reframe.region`): `titulo` (com `*destaques*`), `subtitulo`, `imagem` (fundo), `altura` (0.42), `estilo_destaque` (`caixa`/`cor`), `uppercase`, `alinhamento`
- `cena`: fundo da marca em tela cheia (esconde a pessoa): `estilo` (`gradiente`/`solido`)
- `item_numerado`: `numero`, `titulo`, `subtitulo` (mono), `icone` (imagem), `position`, `size`
- `chips`: etiquetas que entram uma a uma, no tempo da fala: `itens` [{`texto`, `em` (s desde o início do overlay)}], `titulo` (rótulo acima), `position`, `riscar_em` (s; risca todas, para "derrubar mitos"), `estilo` (`contorno`/`solido`), `destaque` (índice com fundo de acento)
- `icone`: ícone desenhado por traço. `nome` (Lucide, ~2.300: `dna`, `brain`, `scale`, `moon`, `pill`, `utensils`, `dumbbell`, `sofa`, `gavel`, `stethoscope`, `route`, `pointer`, `heart-pulse`, `trees`…; lista em `render/node_modules/lucide-static/icons/`), `x`, `y`, `size`, `cor` (`accent`/`text`/`muted`), `rotulo`, `fundo` (disco escuro, padrão sim), `pulso`, `desenhar` (s)
- `diagrama`: fatores ao redor de um centro, ligados por linhas: `itens` [{`icone`, `rotulo`, `em`}], `centro` {`icone`, `texto`}, `x`, `y`, `raio`, `arco` (`cheio`/`superior`/`inferior`), `convergir_em` (s: tudo converge ao centro)
- `balanca`: comparação que pesa: `esquerda`/`direita` {`rotulo`, `icone`, `em`}, `inclinar_para`, `inclinar_em`, `riscar` (lado), `riscar_em`, `titulo`, `x`, `y` (pivô), `largura`
- `grafico`: `tipo` (`barras`/`rosca`), `dados` [{`rotulo`, `valor`, `destaque`}], `sufixo`, `titulo`, `x`, `y`, `largura`
- `marcador`: traço "à mão": `tipo` (`circulo`/`sublinhado`/`seta`/`x`/`check`), `x`, `y`, `largura`, `altura`, `angulo`, `cor`, `espessura`
- `texto_fundo`: palavra grande **atrás da pessoa** (o render recorta a pessoa automaticamente): `texto`, `y`, `size`, `cor`, `peso`, `entrada` (`subir`/`escala`/`revelar`). Use nas áreas atrás da cabeça/ombros.
- `cartao`: `src` (imagem/vídeo/print) **ou** `titulo` + `texto` + `rotulo_topo`; `posicao` (`topo`/`centro`/0–1), `largura`, `proporcao`, `limite`, `rotulo` (chip), `rotacao`, `ajuste`
- Componentes customizados de modelos criados a partir de referência: veja o `REGRAS.md` do modelo.

Qualquer overlay aceita `anchor` (`start`/`end`/`full`) + `duration`/`offset` em vez de `start`/`end`, e `props.formats` para aparecer só em certos formatos.

## 3b. Roteiro visual (obrigatório quando houver motion)
Antes de posicionar motion, escreva `JOB/roteiro_visual.md`: uma tabela **tempo → fala (resumo) → ideia → representação visual → componente**.
- **Não repita a fala em texto** (a legenda já faz isso). Motion **representa**: metáfora (balança, convergência, causa→efeito), dado (gráfico), objeto/ícone (DNA = genética, cérebro = saúde mental, prato = dieta, lua = sono, pílula = remédio, martelo = julgamento, estetoscópio = cuidado), contraste (mito riscado × fato) ou interação com a pessoa (texto atrás dela, marcador desenhado apontando/circulando algo). Texto, no máximo 1–3 palavras-âncora.
- Pode ir **além da fala**, com contexto que enriquece: dados da legenda do post, fatores relacionados. Nunca invente dados nem promessas (em saúde, ver `regras/saude.md`).
- Ritmo: 1 beat forte a cada 4–8s, com respiro. Menos elementos, mais significado. Uma cena de tela cheia (`cena` + diagrama/gráfico) curta (≤6s) é ótima para listas e explicações.
- Mostre o roteiro ao usuário (é curto) junto com a primeira prévia.

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
Saída: `JOB/out/<bruto>_<modelo>_<formato>.mp4` (H.264 + AAC, −14 LUFS por padrão). Leva alguns minutos por formato.

No fim, o render procura **imagem congelada** (frames idênticos por mais de 0,5s) no pré-corte e no vídeo final e grava `build/congelamentos.json`. Se houver aviso, olhe os frames desses tempos e corrija antes de entregar: no pré-corte, a causa é a fonte ou o segmento; só no final, renderize de novo. Um overlay de tela cheia parado de propósito pode ser ignorado.

Entregue os arquivos (no app, envie com a ferramenta de arquivos) com um resumo curto: cortes técnicos feitos, **trechos que você sugere cortar** (com tempo e motivo), overlays, duração final. Também ofereça ajustes.

## Ajustes pedidos pelo usuário
Traduza o pedido para mudanças no EDL ou na transcrição, rode `sync` → `--preview` → render. Exemplos: "legenda maior" → `captions.size`; "tira o zoom do segundo 12" → remova o item de `zooms`; "começa direto na frase X" → reordene ou remova `segments`; "mais rápido" → reduza `cut.max_pause` (refaça o draft) ou use `speed`. Se o pedido for uma **preferência permanente** do modelo, proponha atualizar `template.json`/`REGRAS.md` do modelo.

## Marca
Cada edição usa uma marca (`edl.json → brand`). Marcas ficam em `$ROOT/brands/<slug>/` (do plugin) e `~/.editor-video/brands/<slug>/` (do usuário, com prioridade). Para criar ou ajustar uma: skill `configurar-marca`.
