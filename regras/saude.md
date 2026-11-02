# Regras do segmento: saúde

Valem para **todo modelo** quando a marca tem `"segmento": "saude"`. Têm prioridade sobre as regras do modelo.

## Publicidade médica e de saúde
Siga as normas do conselho profissional (medicina: Resolução CFM nº 2.336/2023; odontologia: CFO; nutrição: CFN; psicologia: CFP etc.). **Confirme com o cliente a versão vigente.**
- **Identificação obrigatória**: toda peça mostra o profissional com nome + registro (`assinatura` na marca: `registro_tipo` + `registro`). O overlay `assinatura` faz isso automaticamente. **Não entregue a versão final com registro vazio**: peça o número ao usuário.
- **Especialidade só com registro de especialista** (RQE no caso médico). Sem RQE, não apresente a pessoa como "especialista em…" nem use o nome da especialidade como título, na tela ou nos textos. Se a fala fizer isso, avise o usuário. Restrições do profissional ficam em `guia.restricoes_profissional` da marca.
- **Sem promessa de resultado**: nada de "perca 10 kg", "garantido", "cura", "100%", prazos de resultado. Se a fala tiver isso, não reforce na tela e avise o usuário.
- Sem sensacionalismo, autopromoção exagerada ou comparação depreciativa com outros profissionais.
- **Antes/depois e depoimentos de pacientes** têm restrições: só use se o usuário confirmar que estão dentro das normas e autorizados por escrito pelo paciente. Antes/depois sempre no mesmo enquadramento, luz e grade.
- **Dados de pacientes**: não exponha nome, rosto, prontuário ou exames identificáveis sem autorização.
- Citações de estudos: mantenha a referência visível (ex.: `rotulo` com "Fonte: NEJM, 2022") quando o vídeo citar um estudo.

## Transcrição
- Corrija com cuidado termos médicos, nomes de exames, medicamentos, siglas e doses. Na dúvida, pergunte em vez de adivinhar.
