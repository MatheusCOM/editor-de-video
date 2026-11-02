---
name: criar-modelo
description: Cria um novo modelo de edição de vídeo por engenharia reversa de vídeos de referência — disseca ritmo de cortes, legendas, zooms, motion graphics, cor, áudio e estrutura, e salva como modelo reutilizável (template.json + REGRAS.md + componentes). Use quando o usuário mandar um vídeo de referência e pedir "cria um modelo igual a esse", "quero editar nesse estilo", "transforma isso em modelo", ou quiser ajustar um modelo existente a partir de novas referências.
---

# Criar modelo a partir de referências

`ROOT` = a pasta do plugin, dois níveis acima deste SKILL.md (`<diretório-base-da-skill>/../..`).

Fluxo ideal: o usuário cola links → você baixa, analisa, agrupa por estilo e só pede confirmação dos grupos e do nome de cada modelo.

Objetivo: transformar o **estilo de edição** de uma ou mais referências num modelo que a skill `editar-video` aplica em qualquer bruto. Copiamos o estilo (ritmo, tipografia, animações, estrutura), **nunca o conteúdo nem os assets** da referência (música, imagens, logos de terceiros).

## 1. Receber as referências
- **Links** (Instagram, TikTok, YouTube, Facebook, Kwai…): baixe todos de uma vez:
  ```bash
  python3 $ROOT/engine/baixar_referencia.py LINK1 LINK2 ... --out REFS_DIR
  ```
  (ou `--lista links.txt`). `REFS_DIR` = `./referencias/<nome-do-lote>/`. O script pula repetidos, espera entre downloads e no fim lista o que baixou e o que falhou, com o motivo.
  - Falha "pediu login" (comum no Instagram): peça ao usuário um `cookies.txt` exportado do navegador logado (extensão "Get cookies.txt LOCALLY") e rode de novo com `--cookies`. **Nunca peça senha.**
  - Falha "rede bloqueada": o ambiente não alcança o site. Leia a documentação do ambiente sobre rede e passe ao usuário os domínios a liberar (`*.instagram.com`, `*.cdninstagram.com`, `*.fbcdn.net`, `*.tiktok.com`, `*.tiktokcdn.com`, `*.tiktokv.com`, `*.youtube.com`, `*.googlevideo.com`, `*.ytimg.com`). Em servidores de nuvem o Instagram pode recusar mesmo assim; no computador do usuário funciona melhor.
  - Com vários links, rode `python3 $ROOT/engine/ranking_instagram.py REFS_DIR` para ver quais performaram melhor (cada perfil é comparado só com ele mesmo) e dê mais peso a eles.
- **Arquivos** (mp4/mov) enviados direto também servem.
- Pergunte o nome do modelo (curto, minúsculo, com hífen: `podcast-cortes`, `ugc-depoimento`) e, se não estiver claro: para que plataforma/formato ele serve e se deve seguir a **marca do usuário** ou as **cores/fontes da referência**.
- Várias referências do mesmo estilo dão um modelo mais robusto: analise todas e consolide o que é comum.

### Escolhendo as referências pelo desempenho
Se o usuário trouxer a pasta de metadados do Instaloader (arquivos `*.json.xz`), rode `python3 $ROOT/engine/ranking_instagram.py PASTA --top 30` e mostre o `ranking.md`. Ajude a escolher: os de maior **desempenho** (1,0 = normal para a época) são as melhores referências. Agrupe por estilo (duração, tema pela legenda) e peça para baixar só os escolhidos (`baixar.sh`). Os vídeos que mais performaram devem pesar mais nas regras do modelo.

## 2. Dissecar (medições automáticas)
```bash
python3 $ROOT/engine/analyze.py REF.mp4 --out MODELO_DIR/referencia/<ref-nome> --transcribe
```
`MODELO_DIR`:
- **Padrão quando `$ROOT` é um clone git do repositório** (`git -C $ROOT rev-parse` funciona), ou seja, quem mantém o plugin: `$ROOT/templates/<nome>`. Assim o modelo vai para todos que usam o plugin depois do commit/push.
- Caso contrário (plugin instalado, só usando): `~/.editor-video/templates/<nome>`, que fica só nesta máquina e sobrevive a atualizações.

**Marca**: por padrão o modelo segue a marca do Instituto (`brand.json`). Copie da referência o ritmo, a estrutura, as animações e a *forma* da tipografia (peso, tamanho, posição, caixa), mas use as cores e fontes da marca, a não ser que o usuário peça explicitamente as cores da referência. Leia também `$ROOT/templates/clinico/REGRAS.md` (regras de publicidade médica valem para todo modelo).

Leia o `resumo.md` gerado. Ele traz ritmo (cortes/min, duração dos planos, cortes no gancho, curva por terços), punch-zooms nos cortes e zooms contínuos, cor (paleta, saturação, contraste, grade sugerido), áudio (loudness, música de fundo, pausas, efeitos nos cortes) e fala (palavras/min, texto do gancho).

## 3. Dissecar (olhando os frames)
**Abra e examine as imagens**: `folha_geral.jpg`, `gancho_0-3s_10fps.jpg`, `folha_cortes_*.jpg` e as sequências em `denso/`. Se precisar de mais detalhe num trecho, extraia frames você mesmo:
```bash
ffmpeg -ss 12.0 -i REF.mp4 -t 1 -vf "fps=15,scale=360:-1,tile=5x3" -frames:v 1 trecho.jpg
```
Responda, com medidas aproximadas (fração da largura/altura):
1. **Legenda**: posição vertical (0–1), altura da letra (~fração da largura), peso/estilo da fonte (grossa, condensada, serifada, manuscrita), caixa alta?, cor base, como a palavra ativa é marcada (cor, caixa, sublinhado, escala), contorno/sombra/faixa de fundo, palavras por vez, animação de entrada (pop, slide, fade, máquina de escrever, palavra por palavra) e emojis.
2. **Gancho**: o que acontece nos 3 primeiros segundos (texto, corte, zoom, som).
3. **Motion graphics**: cada tipo de elemento, quando aparece, como entra e sai, cores e posição.
4. **Enquadramento**: altura dos olhos, fundo desfocado (`reframe.mode: blur`) ou recorte (`cover`), tela dividida, b-roll em tela cheia ou janela.
5. **Transições**: corte seco, flash, zoom, whip.
6. **Estrutura e CTA**: sequência narrativa e card final.

## 4. Escrever o modelo
Crie `MODELO_DIR/template.json`. Use `extends` (`"reels"` ou `"anuncio-meta"`) para herdar o que for igual e sobrescreva só o necessário. Mapeamento das medições:
- ritmo/pausas → `cut.max_pause` ≈ `pause_p90` da referência (limite entre 0,2 e 0,6); muitos cortes/min → menor `max_pause`
- punch-zoom nos cortes → `zoom.jump_cut_scale` = escala medida (ex.: 1,15); sem punch → `null`
- zoom contínuo na maioria dos planos → `zoom.slow_push` (ex.: 1,06)
- legenda → bloco `captions` (`style`: `pop`/`karaoke`/`box`/`plain`/`typewriter`; `reveal`: `page`/`word`; `words_per_line`, `position`, `size`, `uppercase`, `stroke`, `color`, `highlight_color`, `box_color`, `background`, `animation`, `font`)
- cor → `grade` (parta de `grade_suggestion` e ajuste olhando os frames)
- áudio → `audio.loudness_lufs` (medido, entre −16 e −12), `sfx_on_cuts` se provável (peça um arquivo de whoosh ao usuário ou deixe documentado), música de fundo como recomendação no REGRAS.md
- overlays sempre presentes (título de gancho, barra de progresso, logo, CTA) → `overlays` com `anchor` e placeholders `{{...}}` para o texto que muda a cada vídeo
- cores/fontes da referência (se o modelo NÃO seguir a marca): `highlight_color`/`color` nos blocos e `props.color` nos overlays. Fonte diferente da marca: coloque o arquivo (.woff2/.ttf, de licença livre, como Google Fonts via npm `@fontsource/<fonte>`) em `brand/fonts` e cite-a no REGRAS.md. Não dá para garantir a fonte exata da referência; use a mais parecida e diga isso ao usuário.

Escreva `MODELO_DIR/REGRAS.md` no formato dos modelos existentes (`$ROOT/templates/reels/REGRAS.md`): objetivo, cortes, gancho, legendas, zoom, motion graphics (quando usar cada um e com que props), estrutura narrativa, CTA e acabamento. **Seja específico** (tempos, frequências, tamanhos), porque é isso que guia as decisões em cada vídeo futuro. Inclua a seção "Origem" listando as referências e as medições-chave.

## 5. Elementos que a biblioteca não tem → componente novo
Se a referência usa um motion graphic que nenhum overlay nativo reproduz bem (ver catálogo na skill `editar-video`), crie um componente Remotion:
- arquivo `~/.editor-video/components/<nome_snake>.tsx` (ou `$ROOT/render/src/components/custom/` + registro em `custom/index.ts`, se for para o plugin)
- `export default` de um `React.FC<{props, brand, safe, duration}>`; use `useCurrentFrame()` (começa em 0 quando o overlay entra), `useVideoConfig()`, `spring`, `interpolate` do pacote `remotion`. Helpers: `import { fontCss } from "../../../lib/fonts"` e `import { textShadow, popIn, exitProgress } from "../../../lib/anim"` (caminhos relativos a `custom/user/`).
- dimensione tudo relativo a `width` (`k = width/1080`) para funcionar em todos os formatos; respeite `safe`.
- use no modelo como `{"type": "<nome_snake>", ...}` e documente as props no REGRAS.md.
- confira com `cd $ROOT/render && npx tsc --noEmit` e numa prévia.

## 6. Validar o modelo
1. Pegue um bruto de teste do usuário (ou, sem bruto, use o próprio áudio/vídeo da referência só para teste) e rode o fluxo da skill `editar-video` com o novo modelo até a prévia.
2. Compare lado a lado:
```bash
python3 $ROOT/engine/compare.py REF.mp4 JOB/out/<arquivo>.mp4 -o JOB/comparacao.jpg --n 6
```
   Para uma prévia ainda não renderizada, compare os frames de `JOB/preview` com as folhas da referência.
3. Olhe a comparação, liste as diferenças (tamanho/posição da legenda, ritmo, cor, animações) e ajuste o modelo. Repita até ficar próximo.
4. Mostre ao usuário a comparação e o vídeo de teste e peça aprovação. Ajustes aprovados ("legenda mais grossa", "zoom mais forte") vão para o `template.json`/`REGRAS.md`.

## 7. Finalizar
- `python3 $ROOT/engine/templates.py` deve listar o novo modelo.
- Diga ao usuário: o nome do modelo, o que foi capturado, o que é aproximado (fonte, efeitos que não deu para replicar) e como usar ("edita esse vídeo no modelo <nome>").
- Modelo no plugin (`$ROOT/templates`): faça commit no repositório do plugin se o usuário pedir.
