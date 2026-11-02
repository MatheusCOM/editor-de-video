---
name: configurar-marca
description: Configura a identidade visual (logo, cores, fontes, @ e CTA padrão) usada em todas as edições de vídeo deste plugin. Use quando o usuário mandar logo, cores ou fontes da marca, disser "usa a minha marca", "troca as cores das legendas", ou quando editar-video perceber que ainda está na marca padrão.
---

# Configurar a marca

`ROOT` = pasta do plugin (`<diretório-base-da-skill>/../..`).

Onde a marca mora:
- `$ROOT/brand/` = **marca do Instituto Clayton Guimarães**, que vai junto com o plugin para todo mundo. Mudanças permanentes da marca do Instituto são feitas aqui e publicadas (commit/push).
- `~/.editor-video/brand/` = sobrescrita local, só nesta máquina (ex.: testar outra marca). Se existir, tem prioridade.
- `$ROOT/brand-exemplos/neutra/` = marca neutra de exemplo.

Os dados do médico (`medico.nome`, `crm`, `rqe`, `especialidade`) também ficam no `brand.json` e alimentam o overlay `assinatura`. O Dr. Clayton não tem RQE: deixe `rqe` e `especialidade` vazios (a assinatura omite campos vazios).

## Passos
1. Decida o destino (plugin ou sobrescrita local, ver acima). Para uma marca nova local, crie `~/.editor-video/brand/fonts/`, copie `$ROOT/brand/brand.json` como ponto de partida e copie as fontes de `$ROOT/brand/fonts/`.
2. **Logo**: salve o arquivo em `~/.editor-video/brand/logo.png` (de preferência PNG com fundo transparente; SVG também funciona). Se o logo tiver fundo sólido, avise que fica melhor com fundo transparente. Preencha `logo.file: "logo.png"`, `position` (`top-right`, `top-left`, `bottom-right`…), `size` (fração da largura, 0,10–0,20) e `opacity`.
3. **Cores** (hex): `primary` (fundos de cards/títulos), `secondary`, `accent` (palavra ativa da legenda, destaques, botão do CTA), `accent2` (palavras de ênfase, ícones), `text` (texto sobre vídeo, normalmente branco), `text_dark` (texto sobre `accent`), `caption_stroke` (contorno da legenda, normalmente preto). Confira o contraste: o texto sobre `accent` precisa ser legível. Se `accent` for claro, use `text_dark` escuro.
   Campos extras opcionais: `text_muted`, `background`, `border`, `success`, `warning`. Fontes aceitam `tracking` (ex.: `"-0.03em"`) e há o papel `mono` para rótulos. Se não houver logo em imagem, `logo.text` vira um logo tipográfico em fonte mono.
   - Se o usuário só mandar o logo, extraia as cores dele (abra a imagem e/ou use k-means com OpenCV) e proponha a paleta para aprovação.
4. **Fontes**: arquivos `.woff2`, `.woff`, `.ttf` ou `.otf` em `~/.editor-video/brand/fonts/`. Registre cada peso em `fonts.files` (`family`, `weight`, `file`) e escolha quais usar em `fonts.title`, `fonts.caption` e `fonts.body`. Se o usuário só disser o nome de uma fonte do Google Fonts, baixe via npm: `npm pack @fontsource/<nome-da-fonte>` → arquivos em `package/files/<fonte>-latin-<peso>-normal.woff2`. Para legenda, prefira peso 800–900.
5. `handle` (@ da marca) e `cta_default` (texto padrão do botão).
6. **Teste**: rode uma prévia de qualquer edição existente (ou do vídeo de teste) e mostre ao usuário a folha de prévia para aprovar.
