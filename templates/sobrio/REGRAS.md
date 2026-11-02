# Modelo: sobrio

Herda o `reels`. Leia `templates/reels/REGRAS.md` para a mecânica (retakes, gancho, sync). **As regras abaixo têm prioridade**: o estilo aqui é o oposto de "viral barulhento", com presença discreta, muito respiro e hierarquia por espaço e contraste.

Modelo neutro: as cores e fontes vêm da marca. Aplique sempre o `guia` da marca e as regras do segmento (`regras/<segmento>.md`).

## Princípios visuais
- **Um único acento por tela**: a palavra ativa da legenda OU o destaque do título OU o botão do CTA. Nunca dois ao mesmo tempo, nem superfícies inteiras na cor de acento.
- Pouco texto na tela. Títulos leves e amplos (fonte `title` da marca).
- Proibido neste modelo: emojis, setas, flash, contador chamativo, caixa alta em legendas, contorno grosso.
- Dados e rótulos (datas, medidas, "SEMANA 6") em `rotulo` (fonte mono da marca).
- Grade quase neutro, sem filtro colorido.

## Cortes e ritmo
- Mais calmo que o reels: pausa máx. ~0,45s, preservando o respiro natural entre ideias. Corte retakes, hesitações e frases abandonadas, mas não acelere a fala.
- Jump-cut zoom bem sutil (1,05×, automático). Zooms de ênfase só `smooth`, 1,08–1,12, no máximo 1 a cada ~10s, nas frases centrais.

## Legendas
- 4 palavras por vez, minúsculas (como a fala), sombra suave, palavra ativa na cor de acento. Posição ~72% da altura.
- `emphasis`: raro (1 a cada 2–3 frases), só em termos-chave. Com `emphasis_scale` 1.0 o destaque é só a cor.

## Estrutura padrão
1. **Gancho (0–3s)**: `title` com uma frase curta e calma. **Sem `*destaque*`**, porque a legenda já usa o acento na palavra ativa. Use `*palavra*` só em títulos que aparecem sem legenda.
2. **Assinatura (3–6,5s)**: automática se a marca tiver `assinatura.nome`. O draft remove o overlay quando a marca não tem assinatura.
3. **Conteúdo**: explicação; `rotulo` para contextualizar e `lower_third` com moderação.
4. **CTA (últimos ~3,5s)**: tela cheia (`mode: full`), título leve e botão no acento (o único acento da tela), com o texto do botão vindo de `cta_default` da marca. Título sem `*`.

## Acabamento
- Logo da marca (imagem ou texto) no topo esquerdo, opacidade 0,75.
- Barra de progresso fina (4px) embaixo. Remova-a se a tela já tiver outro elemento de acento por muito tempo.
- Áudio: redução de ruído ligada, −14 LUFS. Música só se o usuário enviar, baixa (−22 a −26 dB), instrumental e sóbria.
