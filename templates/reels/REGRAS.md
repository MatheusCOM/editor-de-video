# Modelo: reels (Reels / TikTok / Shorts)

Objetivo: reter a atenção do primeiro ao último segundo. Vertical 9:16, ritmo rápido, legenda sempre visível.

## Cortes
- Corte seco em toda pausa acima de ~0,35s. Respiração e "é…", "ãh", "hum" saem sempre (o rascunho já faz isso).
- **Retakes**: quando a pessoa repete uma frase (errou e falou de novo), mantenha só a ÚLTIMA versão completa. Procure na transcrição frases quase iguais em sequência.
- Remova também: frases abandonadas no meio, "deixa eu ver", "pera", "corta", conversa com quem está filmando, e o silêncio do começo e do fim.
- Duração alvo: 15 a 60s. Se o bruto render mais de 90s de fala útil, priorize o melhor trecho e avise o usuário.
- "tipo" e "né" ficam, a menos que apareçam em excesso (mais de 1 a cada 10s). Aí remova os de "muleta", ajustando `segments`.

## Gancho (0–2s)
- A primeira frase precisa prender. Se o melhor gancho estiver no meio do vídeo (uma afirmação forte, um resultado, uma pergunta), **mova esse trecho para o começo**: os segments podem ficar fora da ordem do bruto (o render respeita a ordem da lista). Só faça isso se a frase fizer sentido sozinha.
- Preencha o `title` inicial ({{GANCHO}}) com 3 a 7 palavras que resumam a promessa do vídeo. Use `*palavra*` para destacar 1 palavra na cor de acento. Não repita literalmente o que está sendo falado; complemente.

## Legendas
- Palavra por palavra, 3 palavras por vez, caixa alta, palavra ativa na cor de acento (estilo `pop`).
- Corrija na `transcript.json` erros de transcrição, nomes próprios, marcas e números ("10 mil" em vez de "dez mil"). Depois rode `edl.py sync`.
- Marque `"emphasis": true` em 1 palavra-chave a cada 1–2 frases (números, resultados, benefícios, palavras emocionais). Use `"emoji"` com moderação: no máximo 1 a cada ~8s, só quando reforça o sentido.

## Zoom e movimento
- O jump-cut zoom (alternando 1,0× / 1,08× a cada corte) já vem automático.
- Some zooms de ênfase (`type: "smooth"`, `scale` 1,15–1,25) nas frases mais fortes, a cada 4 a 7s. Não faça dois zooms seguidos em menos de 2s.
- Use `punch` (seco) para piadas, viradas e revelações.

## Motion graphics (use quando enriquece, não para encher)
- `text_pop` para um número ou palavra de impacto (0,8–1,5s).
- `checklist` quando a pessoa enumera itens/passos.
- `counter` quando fala de números/resultados.
- `emoji`/`arrow` pontuais.
- Não sobreponha MG com a legenda: posicione o MG em `position: "top"` ou ajuste `y` (a legenda fica em ~66% da altura).

## Acabamento
- Barra de progresso no topo (já vem no modelo).
- Música: só se o usuário mandar uma faixa. Volume de −18 a −22 dB com ducking.
- Loudness final: −14 LUFS.
