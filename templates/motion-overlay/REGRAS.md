# Modelo: motion-overlay (só motion, sem reeditar)

Para vídeos **já editados** (cortes, legenda e cor prontos) em que o usuário só quer motion graphics por cima. O draft mantém o vídeo inteiro (`cut.mode: none`), não gera legenda nova e não mexe em cor. O áudio só é normalizado a −14 LUFS.

Aplique sempre o `guia` da marca e as regras do segmento.

## Antes de posicionar qualquer coisa
1. Rode `analyze.py --transcribe` e **olhe a folha geral**: anote onde está o rosto, onde está a legenda gravada (faixa vertical) e onde há outros elementos gravados (enquetes, prints, stickers) e em que tempos.
2. Defina as **zonas livres** (ex.: topo 3–12%, base 78–92%). Motion só entra nelas. Nunca cubra rosto, boca nem legenda gravada.
3. Se o vídeo tiver legenda gravada, deixe `captions.enabled: false`. Se não tiver, ligue a legenda do modelo (`captions.enabled: true` + estilo).

## O que adicionar (ancorado na fala, tempo de saída = tempo do vídeo)
- **Tese/gancho** (0–3s): `title` leve no topo ou `rotulo`.
- **Listas faladas** (estereótipos, fatores, passos): `chips`, com cada item entrando na palavra exata (`em` = segundos desde o início do overlay). Para "derrubar mitos", use `riscar_em` no momento da virada ("só que…", "mas…").
- **Frase-chave**: `title` com 1 `*destaque*` na base, 3–5s.
- **Assinatura** cedo (3–8s), na zona livre, se a marca tiver.
- **Cartões** (`cartao` de texto) só se houver zona livre grande; prefira elementos baixos e largos.
- CTA final só se houver tempo **depois** da fala; não cubra a fala final.

## Ritmo
- Um elemento novo a cada ~5–8s, nunca dois entrando ao mesmo tempo, e nada na tela por mais de ~6s seguidos (exceto chips que crescem com a fala).
- Respeite a regra de acento da marca: no máximo 1 elemento preenchido com o acento por tela.
