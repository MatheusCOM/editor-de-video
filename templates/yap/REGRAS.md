# Modelo: yap

**Origem**: reel de @stella.soragi, "Seu Yap 1 em 4 linhas" (instagram.com/reel/DexZroRP8Kj), analisado em 11/2026: 74,7s, 1 take frontal em luz natural, 24 cortes (um a cada ~3s), pausas finais ≤0,18s, ~190 palavras/min, música baixa, −14 LUFS, 3 punch-ins e 4 planos com zoom lento. Quase tudo o que "edita" o vídeo é o **cabeçalho de contexto** no topo.

Herda a mecânica do `reels` (retakes, sync, transcrição). Modelo neutro: cores e fontes vêm da marca. Aplique sempre o `guia` da marca e as regras do segmento. Cortes: **só técnicos** (ver a skill).

## O que é um "Yap"
Fala corrida, olhando para a câmera, como quem conta algo a um amigo. O formato nasceu como série ("episódio 1 de…"): a pessoa diz **quem é numa cena**, **o que está vivendo**, **o que quer, com prazo** e fecha com **"esse é o episódio 1 de: como eu tô [objetivo]… me segue pra ver se eu consigo"**. Funciona também para opinião, bastidores e explicações curtas. A edição não compete com a fala: ela **organiza** a fala.

## Layout
- Pessoa em tela cheia (`reframe: cover`), rosto no terço de cima, sem tarjas.
- **Cabeçalho** (`cabecalho`) no topo, sempre presente: um por ideia, trocando com corte seco quando o assunto muda.
- **Legenda curta** (2 palavras, palavra falada destacada na cor de acento) **ao lado do rosto**, na altura do peito (`captions.x` ≈ 0,7, `position` ≈ 0,6). Se a pessoa estiver à direita do quadro, use `x` ≈ 0,3. Nunca em cima do rosto nem da boca.
- **Recortes** (`recorte`): imagens pequenas coladas no canto de cima (x 0,75–0,8, y 0,18–0,25), sob o cabeçalho, com borda branca.

## Cabeçalho: o vocabulário
Cada `cabecalho` dura do início de uma ideia até o início da próxima; não deixe buracos sem cabeçalho nem dois ao mesmo tempo. Um a cada 2–6s. **Represente a fala, não transcreva**: resuma a ideia em 2 a 6 palavras.
- **Título do bloco**: `{"linhas":[{"texto":"Como fazer um Yap?"}]}`
- **Título + subtítulo** (contexto extra, menor): `[{"texto":"Dezenas de pessoas fazendo esse vídeo"},{"texto":"e ganhando milhares de seguidores","estilo":"sub","em":1.2}]`
- **Lista que cresce** (cada item entra quando é falado, via `em` em segundos desde o início do cabeçalho): `[{"texto":"Como fazer Yap?"},{"texto":"Resultado","estilo":"item","icone":"x","em":2.0},{"texto":"Produto","estilo":"item","icone":"x","em":3.1}]`. Ícones: `x` (vermelho), `check` (verde) ou um emoji.
- **Citação digitando** (frase de exemplo, pergunta de seguidor): `{"texto":"“Me ajuda a destravar na câmera?” 💬","estilo":"citacao","dur_maquina":1.6}`. Ajuste `dur_maquina` para a digitação acabar junto com a fala.
- **Número de impacto**: `{"linhas":[{"texto":"R$ 670 mil","estilo":"numero"}],"emojis":"💵💵💵"}`
- **Passos numerados**: `"1. Quem você é (numa cena)"`, depois `"2. O que você tá vivendo agora"`… cada um como cabeçalho próprio, seguido da citação de exemplo.
- **Reação**: `{"linhas":[{"texto":"Resultado"}],"emojis":"😍👏"}` (emojis no máximo a cada ~15s).
- Use `*palavra*` para pintar 1 palavra com a cor de acento (marcas com "um acento por tela": a legenda já usa o acento; prefira não pintar o cabeçalho).
- Primeiro cabeçalho (`{{CABECALHO_GANCHO}}`): a tese do vídeo em até 6 palavras.

## Recortes e B-roll
- Quando a fala cita algo que existe (um estudo, um post, um exame, uma pessoa, um lugar), mostre um `recorte` pequeno por 2–4s: `{"src":"recortes/estudo.png","x":0.78,"y":0.2,"largura":0.26,"giro":-3}`.
- Fontes, nesta ordem (as três primeiras não custam nada):
  1. material que o usuário mandar (prints, fotos, logos);
  2. **print de página pública** (resumo de um estudo no PubMed, matéria, site oficial), feito com o Chromium do sistema (Playwright, `page.screenshot`), recortando o título e o trecho que importa. Cite a fonte no `legenda` do recorte;
  3. imagens geradas no próprio render (ícones, gráficos: `icone`, `grafico`, `diagrama`);
  4. só se nada disso servir e o ganho for claro: imagem gerada por IA (ex.: Magnific). Isso **tem custo**: pergunte antes ao usuário. Em saúde, nunca gere imagens de pacientes, de "antes e depois" ou de procedimentos.
- Nada de B-roll em tela cheia: o formato é a pessoa falando.

## Cortes e ritmo
- Corte toda pausa acima de ~0,2s: fala corrida (~190 palavras/min).
- Jump cuts sem zoom alternado. 2 a 4 **zooms lentos** (`slow`, 1,06–1,1×) nos momentos de confissão ou revelação, e 1 a 3 `punch` (1,08×) em viradas. Nunca dois em menos de 3s.

## Abertura e fecho
- Abertura: começa já na primeira palavra (sem "oi gente"; se houver, sugira cortar). Se a pessoa gravou um gesto de entrada (mão na câmera, aproximação), mantenha: ele faz parte do gancho.
- Fecho: o pedido para seguir ("me segue pra ver…") ganha cabeçalho próprio ("Me segue"). Sem card de CTA.

## Acabamento
- Assinatura (nome + registro) logo após o primeiro cabeçalho, se a marca tiver; em saúde é obrigatória.
- Música: uma trilha suave e constante, bem baixa (−24 dB, ducking). Se a marca tiver faixa padrão, use; senão, deixe sem música e avise.
- Cor: leve e quente (luz de janela). Não satures.

## Roteiro para quem grava (mande junto quando o usuário pedir ajuda com o conteúdo)
1. **Quem eu sou, numa cena**: "Sou [quem] e [um detalhe da rotina que dá pra imaginar]."
2. **O que estou vivendo**: "Faz [tempo exato] que eu [tento algo] e [o que não está dando certo]."
3. **O que eu quero, com prazo**: "Quero [objetivo com número] até [data]."
4. **Fecho**: "Esse é o episódio 1 de: como eu tô [objetivo] sendo [quem eu sou]. Me segue pra ver se eu consigo."
- Número exato vale mais que adjetivo; cena vale mais que título; até 60s; celular, luz de janela e apoio.
- **Em saúde**: o objetivo é do profissional (ex.: "levar informação séria a 10 mil pessoas até março"), **nunca** uma promessa de resultado para pacientes, e sem expor pacientes.
