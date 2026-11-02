---
name: configurar-marca
description: Cadastra ou ajusta a identidade visual (marca) de quem vai produzir os vídeos — logo, cores, fontes, guia de marca, segmento, assinatura/registro profissional e CTA padrão. Use antes da primeira edição para um cliente ou marca nova, quando o usuário mandar um guia de marca/logo/cores/fontes, disser "usa a minha marca", "é para outro cliente", "troca as cores", ou quando editar-video não encontrar a marca do vídeo.
---

# Configurar marca (onboarding de identidade visual)

`ROOT` = pasta do plugin (`<diretório-base-da-skill>/../..`).

O sistema é **multi-marca**: cada cliente ou produtor tem uma pasta de marca, e todos os modelos se adaptam a ela. **Nenhum vídeo é editado sem uma marca definida.**

Onde as marcas moram:
- `$ROOT/brands/<slug>/`: marcas que vão junto com o plugin para todo mundo (ex.: `icg`, `neutra`). Para alterar, é preciso commit/push no repositório do plugin.
- `~/.editor-video/brands/<slug>/`: marcas desta máquina (padrão para clientes novos). Têm prioridade sobre as do plugin.

```bash
python3 $ROOT/engine/marcas.py               # lista
python3 $ROOT/engine/marcas.py ver <slug>    # detalhes + regras do segmento
python3 $ROOT/engine/marcas.py nova <slug>   # cria a partir da neutra em ~/.editor-video/brands/<slug>/
```

## 1. Coletar a identidade (pergunte tudo de uma vez, numa mensagem só)
1. **Nome da marca** e um slug curto (`clinica-x`, `loja-y`).
2. **Guia de marca** (PDF ou imagens), se existir. É a melhor fonte: leia as páginas e extraia cores (hex), fontes, regras de uso e tom de voz.
3. **Logo** (PNG com fundo transparente ou SVG). Se não tiver, use um logo tipográfico com `logo.text`.
4. **Cores**, se não vierem do guia. Do logo dá para extrair com k-means (OpenCV) e propor para aprovação.
5. **Fontes** (nomes ou arquivos).
6. **Segmento**: saúde, advocacia, educação, varejo etc. Para `saude` existem regras obrigatórias em `$ROOT/regras/saude.md`.
7. **Assinatura**: quem aparece nos vídeos e o registro profissional, se houver (CRM, CRO, CRN, CRP, OAB…). Pergunte também por restrições, por exemplo "não tem RQE, não pode ser chamado de especialista".
8. **@ do perfil** e **CTA padrão** (texto do botão: "Agende sua avaliação", "Compre agora"…).

## 2. Montar a marca
`marcas.py nova <slug>` e preencha `brand.json`:
- `colors`: `primary` (cards e fundos de títulos), `secondary`, `accent` (palavra ativa, destaques, botão), `accent2`, `text` (texto sobre vídeo), `text_muted`, `text_dark` (texto sobre `accent`), `background` (fundo das cenas), `border`, `caption_stroke`. **Confira o contraste**: texto sobre `accent` legível; `text` legível sobre `background`.
- `fonts`: `title`, `caption`, `body`, `mono` (`family`, `weight`, `tracking` opcional, ex.: `"-0.03em"`) e `files` (cada peso usado, arquivo `.woff2`/`.ttf`/`.otf` em `fonts/`). Fonte do Google Fonts: `npm pack @fontsource/<nome>` e use `package/files/<nome>-latin-<peso>-normal.woff2` (o subset latin cobre os acentos do português). Fonte paga ou proprietária: peça o arquivo ao cliente. Se a fonte da marca for muito fina para legenda, use um peso maior (600–800) só no papel `caption`.
- `logo`: `file` (em `logo.*` na pasta da marca) ou `text`; `position`, `size`, `opacity`.
- `segmento`, `assinatura` (`nome`, `registro_tipo`, `registro`, `extra`, `cargo`), `handle`, `cta_default`, `radius`.
- `guia`: regras visuais e de tom, em texto curto e objetivo. Exemplos: regra de acento ("um único elemento na cor de acento por tela"), estilo (minimalista × chamativo, caixa alta ou não, emojis permitidos?), fotografia, tom de voz, palavras proibidas ou preferidas, restrições do profissional. **Essas regras valem para todos os modelos e têm prioridade sobre eles.**

## 3. Aprovar
Renderize uma prévia com um vídeo existente (ou o de teste do usuário) em 1–2 modelos, com `--brand <slug>`, e mostre a folha de prévia. Ajuste até o usuário aprovar.

## 4. Pendências
Se faltar algo obrigatório (ex.: registro profissional em marca de saúde), registre como pendente, avise o usuário e lembre na hora do render final (o validador avisa).
