# LegacySubscriptionAdapter

## Responsabilidade

`LegacySubscriptionAdapter` lê `AssinaturaCliente` e `PlanoNFe` e retorna uma visão comercial comum com `source=LEGACY`.

## Garantias

- somente leitura;
- não cria Account;
- não cria Subscription nova;
- não altera contador legado;
- não sincroniza automaticamente;
- não bloqueia emissão;
- não decide migração.

## Mapeamento

- assinatura ativa por `cliente_id` → estado legado;
- plano Básico/Pacote → `LEGACY_START_V1` quando aplicável;
- `quantidade_nfes` → limite legado informativo;
- `nfes_consumidas` → consumo legado informativo;
- preço contratado → desconhecido quando não preservado pelo legado.

## Ambiguidades preservadas

Ausência de histórico, desconto, gateway, versão, status de pagamento ou contrato não deve ser preenchida por inferência. O adapter deve retornar ausência/unknown e permitir revisão.

## Uso futuro

Em shadow mode, o adapter pode ser comparado ao novo modelo para identificar divergências antes de qualquer migração. O fluxo fiscal não deve depender dele sem uma fase de enforcement aprovada.
