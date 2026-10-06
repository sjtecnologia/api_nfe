# Inventário de Evidências Contratuais — Fase 4.6F.8

**Escopo:** fontes potenciais locais, sem conteúdo sensível versionado.

| Tipo | Localização | Cliente relacionado | Natureza | Confiança | Sensível? | Revisão humana | Usado como prova? |
|---|---|---|---|---|---|---|---|
| CONTRACT_TEMPLATE | `Documentacao/CONTRATO DE LICENÇA E TERMOS DE USO - EMITEMAX.docx` | Não | Template geral com planos e termos de uso | LOW | Não identificado | Sim | NÃO |
| CONTRACT_TEMPLATE | `Documentacao/CONTRATO DE LIC├çA E TERMOS DE USO - EMITEMAX.docx` | Não | Cópia/variante do template geral | LOW | Não identificado | Sim | NÃO |
| CONTRACT_SUMMARY | `Documentacao/RESUMO_CONTRATO_EMITEMAX.docx` | Não | Resumo comercial geral, sem identificação de cliente | LOW | Não identificado | Sim | NÃO |
| DATABASE_LEGACY | `clientes`, `planos_nfe`, `assinaturas_cliente` em `sjtnfe` | Sim, por ID interno | Cadastro e assinatura legada | MEDIUM | CPF/CNPJ não coletados | Sim | SIM, apenas como evidência de cadastro |
| DATABASE_AUDIT | `auditoria` em `sjtnfe` | Possível, por ID interno | Logs administrativos; sem correlação contratual suficiente | LOW | Não coletado | Sim | NÃO |
| BILLING_SHADOW | Tabelas não existentes em `sjtnfe` | Não | Representação shadow ausente | N/A | N/A | N/A | NÃO |

## Termos encontrados nos templates

Os documentos genéricos mencionam mensalidade, planos, NF-e/NFC-e, usuários, empresas, suporte, vigência, reajuste e opções de R$60/50 documentos. Como contêm placeholders e não identificam os cinco clientes, esses termos são apenas fonte potencial para revisão humana.

## Fontes não abertas

Arquivos `.pem`, certificados, backups de banco e documentos fiscais foram excluídos da análise por não serem necessários para reconstruir contrato comercial e por poderem conter segredos ou dados sensíveis.

## Critério

Nenhuma fonte foi convertida automaticamente em prova individual. Preço de catálogo permanece `PRICE_UNKNOWN` por cliente; direitos permanecem `UNKNOWN` até evidência vinculada ao contratante.
