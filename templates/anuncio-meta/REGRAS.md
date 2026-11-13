# Modelo: anuncio-meta (Anúncio para Meta Ads: Facebook e Instagram)

Herda o modelo `reels`. Leia `templates/reels/REGRAS.md` primeiro; as regras abaixo **substituem ou complementam** as dele.

Objetivo: parar o scroll, comunicar UMA promessa e levar ao clique. A maioria assiste sem som, então a legenda é obrigatória e o texto na tela precisa contar a história sozinho.

## Estrutura (adapte ao conteúdo do bruto)
1. **Gancho (0–3s)**: dor, curiosidade, resultado ou pergunta direta. Título grande ({{GANCHO}}) com 3 a 6 palavras. Se a melhor frase de gancho estiver no meio, sugira trazer para o início (só mova se o usuário pedir).
2. **Problema / contexto (3–10s)**: por que isso importa.
3. **Solução / produto (10–25s)**: o que é e como resolve. Use `lower_third` para nome do produto/pessoa e `checklist` para benefícios.
4. **Prova**: números (`counter`), depoimento, antes/depois, demonstração (b-roll, se o usuário mandar).
5. **CTA (últimos 3–5s)**: o card `cta` já vem no fim. Preencha `title` ({{CTA_TITULO}}) com a ação + benefício (ex.: "Garanta *50% OFF* hoje") e `button` com o verbo que bate com o botão do anúncio ("Saiba mais", "Comprar agora", "Cadastre-se").

## Regras específicas
- Duração ideal: 15 a 30s. Máximo de 45s, a menos que o usuário peça outra coisa.
- Cortes mais agressivos (pausa máx. 0,3s). Introdução ("oi gente, tudo bem?"): sugira o corte ao usuário, mas não corte sem ele pedir.
- Legenda estilo `box` (palavra ativa numa caixa da cor de acento), 3 palavras por vez.
- **Zonas seguras do Meta**: no 9:16, nada de texto importante nos 14% de cima nem nos 20% de baixo. O modelo já configura isso, então não force `position` fora delas.
- 3 formatos do mesmo EDL: 9:16 (Stories/Reels), 4:5 (Feed) e 1:1. Confira a prévia dos três; textos longos podem quebrar diferente no 1:1. Overlays que só fazem sentido num formato podem usar `props.formats: ["9x16"]`.
- Evite promessas exageradas ou absolutas no texto da tela ("cura", "garantido", "100%"), porque as políticas do Meta reprovam. Se o bruto tiver isso, avise o usuário.
- Logo: se a marca tiver logo, mostre no CTA (padrão). Logo fixo no canto é opcional (`{"type":"logo","anchor":"full"}`).
