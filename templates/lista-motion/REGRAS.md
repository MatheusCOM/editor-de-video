# Modelo: lista-motion

**Origem**: reel de George Vitko, "Making videos with Claude…" (instagram.com/reels/De2dMErAprH), analisado em 11/2026: 56s, ~30 cortes (um a cada ~1,2s; mais densos no início e no fim), 5 punch-ins nos cortes do apresentador (1,04–1,14×), 11 planos com zoom contínuo, ~213 palavras/min, −14 LUFS, música baixa.

Herda a mecânica do `reels`. Modelo neutro: tudo nas cores e fontes da marca. Aplique sempre o `guia` da marca e as regras do segmento. Se o guia limitar efeitos (ex.: marcas sóbrias), mantenha a estrutura de lista e o ritmo, mas suavize: menos cenas cheias, sem rotação de cartões, transições mais lentas.

## Estrutura
1. **Gancho (0–3s)**: afirmação que quebra expectativa + promessa da lista ("…aqui estão 5 X que você precisa"). Título `title` curto no topo. Cortes já no gancho (2 nos primeiros 3s).
2. **Itens 1..N**: para cada item:
   - `cena` (fundo da marca em tela cheia, 1,5–3s) + `item_numerado` (`numero`, `titulo`, `subtitulo` em mono, ex.: autor/fonte), entrando quando a pessoa diz "primeiro…", "segundo…", "número 3…";
   - em seguida, 1 a 3 `cartao` mostrando o item (print, imagem ou vídeo que o usuário mandar; sem mídia, cartão de texto com `titulo` + `texto`), enquanto a pessoa explica. O cartão fica no `topo` com a pessoa visível embaixo, ou no `centro` sobre uma `cena`.
   - alternar: pessoa (com punch-in no corte) → cena/cartão → pessoa. Planos de 1–2s.
3. **Fecho/CTA**: CTA de engajamento ("comente X que eu te mando", "salve para depois"). `cta` em `overlay` nos últimos ~3s, com o texto do botão = a palavra-chave a comentar.

## Como montar a partir da fala
- Leia a transcrição e marque onde cada item começa (palavras ordinais, "número", "outra coisa", "por fim").
- Cada `item_numerado` dura do início do item até o primeiro cartão (~1,5–2,5s). Os cartões cobrem as frases de explicação.
- **Peça ao usuário as mídias de cada item** (prints, fotos, vídeos curtos). Sem elas, use cartões de texto com a ideia-chave em até 6 palavras + 1 frase de apoio.
- Não cubra a pessoa por mais de ~60% do tempo: o rosto gera conexão.
- Cartão no `topo` só quando o rosto da pessoa está da metade da tela para baixo. O componente limita o cartão a 36% da altura, mas se a gravação tiver o rosto alto (close), use `cena` + cartão no `centro`, ou `limite` menor. Confira na prévia se o cartão cobre os olhos.

## Legendas
- 2–3 palavras por vez, peso 700, palavra ativa na cor de acento, centro-baixo (~60%). Continuam visíveis sobre cenas e cartões.

## Ritmo e movimento
- Pausa máx. ~0,25s. Punch-in de 1,10× alternado nos cortes da pessoa (automático).
- Zoom de ênfase `smooth` 1,12–1,18 em revelações ("e o mais louco…").
- Transições: os componentes já entram com desfoque→nítido e mola (~0,3–0,4s). Não empilhe mais de 2 elementos entrando ao mesmo tempo.

## Áudio
- Música de fundo ritmada e baixa (−20 a −22 dB, ducking), se o usuário mandar. Efeito sonoro sutil (whoosh) nas entradas de `cena` é opcional (`audio.sfx`).
