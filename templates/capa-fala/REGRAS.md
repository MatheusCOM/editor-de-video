# Modelo: capa-fala

**Origem**: reel do Dr. Clayton Guimarães, "Você vai trocar de dieta e continuar obeso?" (instagram.com/p/DeRxYHsBsHM), analisado em 11/2026: 61,6s, 1 take frontal com 6+ jump cuts discretos, pausas finais ≤0,29s, 207 palavras/min, música baixa, −14 LUFS, sem zoom nem movimento de câmera.

Herda a mecânica do `reels` (retakes, sync, transcrição). Modelo neutro: cores e fontes vêm da marca. Aplique sempre o `guia` da marca e as regras do segmento.

## Layout
- **Capa fixa** (overlay `capa`) nos 42% de cima durante o vídeo todo, funcionando como thumbnail permanente. A pessoa fica nos 58% de baixo (`reframe.region`), em cover com o rosto centralizado.
- Capa: título em 2 a 4 linhas, caixa alta, com 1 ou 2 trechos `*em destaque*` (caixa na cor de acento). Na referência: "VOCÊ VAI *TROCAR DE DIETA* E CONTINUAR *OBESO?*". Se o usuário mandar uma imagem para a capa (`props.imagem`, ex.: foto dos pratos), o título fica por cima dela com um degradê para leitura.
  - Marcas com regra de **um acento por tela** (ver `guia` da marca): use só 1 destaque e prefira `estilo_destaque: "cor"`.
- O título da capa é **a pergunta ou afirmação provocativa do vídeo**, não a primeira frase falada. Curta (até ~8 palavras).

## Cortes e ritmo
- Corte toda pausa acima de ~0,3s, além de hesitações e retakes. O resultado é uma fala corrida e densa (~200 palavras/min).
- **Sem zoom** (nem de ênfase) e sem efeitos: a energia vem da fala.

## Legendas
- Discretas: fonte do corpo, peso 600, 1 a 2 linhas, sem palavra destacada, perto do pé do vídeo (~86% da altura). Servem para quem assiste sem som, não como efeito.

## Estrutura (medida na referência)
1. **Gancho (0–5s)**: frase provocativa que antecipa a objeção ("Você pode ficar com raiva do que eu vou te falar, mas…") + a tese.
2. **Evidência**: um estudo ou dado concreto (cite a fonte; para saúde, deixe a referência visível com `rotulo` na parte do vídeo ou na legenda do post).
3. **Reflexão com o espectador**: "então para e pensa comigo…", aplicando à experiência dele.
4. **Solução/posicionamento**: como o profissional ou a marca resolve.
5. **Fecho**: CTA falado. Card de CTA final é opcional (não está na referência). Se usar, `cta` com `mode: overlay` nos últimos 3s.

## Acabamento
- Assinatura (nome + registro) logo após o gancho, se a marca tiver.
- Música opcional bem baixa (−24 dB, ducking). Redução de ruído ligada.
