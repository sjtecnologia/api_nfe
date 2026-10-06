# LEGACY R$60 POLICY

**Fase:** 4.6F.5  
**Status:** proteção documental; sem migração ou cobrança

Clientes atuais cujo contrato conhecido seja aproximadamente R$60 não recebem `START_V1` nem limite de 50 NF-e automaticamente. O preço efetivo é `BillingSubscription.contracted_price` quando existente; `PlanoNFe.valor_mensal` é somente evidência do catálogo público/legado e não prova o preço contratado.

A classificação aproximada de R$60 é candidata a revisão, não decisão automática. O cliente permanece grandfathered até upgrade, aceite de migração, novo contrato, cancelamento seguido de retorno ou negociação formal. O preço e direitos atuais devem permanecer independentes do preço público vigente.

Se `contracted_price` não existir, o preview deve retornar `LEGACY_POLICY_REVIEW_REQUIRED`, preservar o contrato observado e não assumir 50, ilimitado ou qualquer capacidade. Clientes sem assinatura ativa também exigem revisão e permanecem fail-open.

`LEGACY_START_V1` é `CLOSED_FOR_NEW_SALES`. Novas contratações usam a versão vigente do catálogo, inicialmente `START_V1` com 50 NF-e/mês, sem aplicação retroativa.

Nenhuma cobrança, checkout, Stripe, enforcement de inadimplência ou alteração de subscription é implementada nesta fase.
