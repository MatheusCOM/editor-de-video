# Modelo: clinico (Instituto Clayton Guimarães)

Herda o `reels`. Leia `templates/reels/REGRAS.md` para a mecânica (retakes, gancho, sync). **As regras abaixo têm prioridade**, porque o estilo aqui é o oposto de "viral barulhento": *precisão clínica, presença discreta*.

> Modelo-base criado a partir do guia de marca. Quando houver modelos criados das referências reais do Dr. Clayton, prefira-os e use este só como fallback.

## Identidade (guia de marca)
- Fundo quase-preto, tipografia leve e ampla (Sora Light nos títulos, tracking negativo), **um único acento dourado (#C9A15A) por tela**: a palavra ativa da legenda OU um destaque do título OU o botão do CTA. Nunca dois ao mesmo tempo. Superfícies inteiras douradas são proibidas.
- A hierarquia vem do espaço e do contraste, não da cor. Pouco texto na tela, muito respiro.
- **Proibido neste modelo**: emojis, setas, flash, contador animado chamativo, caixa alta em legendas, texto com contorno grosso, cores fora da paleta (Obsidiana #08090D, Grafite #12141A, Ouro #C9A15A, Marfim #F2F1EE, Texto secundário #A8A5A0). As cores Sucesso #6FA88B e Atenção #C2705A só aparecem em dados clínicos.
- Rótulos e dados (datas, medidas, "SEMANA 6") vão em `rotulo` (JetBrains Mono, caixa alta, espaçado).
- Fotografia: luz baixa, fundo escuro, **sem filtro colorido** (grade quase neutro). Antes/depois sempre no mesmo enquadramento e com o mesmo grade nos dois lados.

## Tom de voz nos textos da tela
- Direto e clínico. Frases curtas. Vocabulário: *ajuste, leitura, acompanhamento, protocolo, avaliação*.
- **Sem promessa de número ou de resultado** ("perca 10 kg", "resultado garantido", "cura"). Se a fala do médico tiver isso, não reforce na tela e avise o usuário.

## Publicidade médica (conferir com o usuário)
Siga as regras do CFM para publicidade médica (Resolução CFM nº 2.336/2023; confirme a versão vigente com o Instituto):
- Toda peça identifica o médico com **nome + CRM** (e **RQE** quando cita especialidade). O overlay `assinatura` faz isso usando `brand.json → medico`. **Não renderize a versão final com CRM vazio**: peça o número ao usuário.
- Nada de sensacionalismo, garantia de resultado ou comparação depreciativa com outros profissionais.
- Antes/depois e depoimentos de pacientes têm restrições: só use se o usuário confirmar que estão dentro das regras e autorizados pelo paciente.
- Não exponha dados identificáveis de pacientes (nome, rosto, prontuário) sem autorização.

## Cortes e ritmo
- Mais calmo que o reels: pausa máx. ~0,45s, preservando o respiro natural entre ideias. Corte retakes, hesitações e frases abandonadas, mas não acelere a fala.
- Jump-cut zoom bem sutil (1,05×, automático). Zooms de ênfase só `smooth`, 1,08–1,12, no máximo 1 a cada ~10s, nas frases centrais.

## Legendas
- 4 palavras por vez, minúsculas (como a fala), Sora 600, marfim, sombra suave, palavra ativa em dourado. Posição ~72% da altura.
- `emphasis`: raro (1 a cada 2–3 frases), só em termos clínicos-chave. Com `emphasis_scale` 1.0 o destaque é só a cor.
- Corrija termos médicos, nomes de exames, medicamentos e siglas na transcrição.

## Estrutura padrão
1. **Gancho (0–3s)**: `title` com uma frase curta e calma (ex.: "Seu metabolismo, *lido* em tempo real"); `*palavra*` vira dourado, no máximo uma palavra.
2. **Assinatura (3–6,5s)**: nome + CRM/RQE (automático).
3. **Conteúdo**: explicação; use `rotulo` para contextualizar ("PROTOCOLO · SEMANA 6") e `lower_third` com moderação.
4. **CTA (últimos ~3,5s)**: tela cheia escura (`mode: full`), título leve e botão dourado (o único dourado da tela). Título no tom da marca: "Agende sua *avaliação*" não leva destaque se o botão já é dourado. Prefira sem `*`.

## Acabamento
- Logo/assinatura em texto mono no topo esquerdo (opacidade 0,75) durante o vídeo.
- Barra de progresso fina (4px) dourada embaixo. Remova-a se a tela já tiver outro elemento dourado preenchido por muito tempo.
- Áudio: redução de ruído ligada, −14 LUFS. Música só se o usuário enviar, e baixa (−22 a −26 dB), instrumental e sóbria.
