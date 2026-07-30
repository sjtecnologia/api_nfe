# Analise NBS x LC116 na NFSe

Data: 2026-07-30

## Resumo

A revisao da documentacao do portal NFS-e mostrou dois conceitos que nao podem ser misturados no projeto:

- Codigo de servico nacional/LC 116: usado para ItemListaServico no XML, no formato como 01.01, 01.07, 17.01.
- Codigo NBS: usado em CodigoNbs no XML GISS, com restricao local de ate 9 caracteres no schema e validacao interna sem pontuacao.

## O que foi confirmado

- O schema local do GISS define CodigoNbs com maxLength 9 em docs/nfse_sjrp_giss/schemas_modificados_gissv2/Schemas_XSD_Servicos_Prestados/v2_04/tipos-v2_04.xsd.
- A pagina consultada no portal gov.br listada em codigos-de-tributacao-nacional-nbs expõe a lista nacional de servicos, que na pratica foi lida aqui como referencia para os codigos de servico/LC116.
- O projeto usa CodigoNbs de 9 digitos sem pontos em validacao e banco; a entrada pode vir pontuada e e normalizada antes da emissao.
- A documentacao de API do proprio repositorio tambem mostra exemplos de NBS com pontuacao, como 1.0107.10.00.

## Risco identificado

Se um cliente externo seguir a documentacao da API e enviar o NBS com pontuacao, o valor pode exceder o formato esperado pelo XML/schema caso nao seja normalizado antes da emissao e da persistencia.

## Ajuste aplicado

- A criacao compartilhada da NFSe agora normaliza codigo_nbs removendo pontuacao e preservando 9 digitos.
- Exemplo: 1.0107.10.00 -> 101071000.
- O dict de entrada tambem e atualizado, para que persistencia e geracao de XML usem o mesmo valor normalizado.

## Regra pratica para o projeto

- Continuar usando LC116 em codigo_servico/codigo_tributacao_nacional.
- Continuar usando NBS em codigo_nbs/CodigoNbs.
- Aceitar NBS com ou sem pontuacao na entrada, mas sempre persistir e emitir sem pontuacao.
