# Catálogos de vendas

O módulo fica disponível em **Gestão → Catálogos e Pedidos**. O usuário cria um
link público com produtos e preços selecionados; o comprador monta o carrinho e
gera um pedido.

Sem uma conta de pagamento vinculada, a confirmação abre o WhatsApp informado
no catálogo (ou o telefone da empresa) com o resumo do pedido. Os pedidos
sempre ficam registrados no painel.

## Mercado Pago por vendedor

Para habilitar o pagamento online, configure no servidor a aplicação OAuth do
Mercado Pago e cadastre exatamente a URL de retorno abaixo na aplicação:

`https://SEU-DOMINIO/admin/catalogos-vendas/pagamentos/mercadopago/retorno`

Variáveis exigidas:

```env
PAYMENT_MASTER_KEY=chave-mestra-longa-e-exclusiva
MERCADOPAGO_OAUTH_CLIENT_ID=seu-app-id
MERCADOPAGO_OAUTH_CLIENT_SECRET=sua-chave-secreta
MERCADOPAGO_OAUTH_REDIRECT_URI=https://SEU-DOMINIO/admin/catalogos-vendas/pagamentos/mercadopago/retorno
```

Depois disso, cada empresa vincula a própria conta pelo botão **Conectar Mercado
Pago**. Os tokens são mantidos criptografados no banco e o comprador é levado
ao Checkout Pro do Mercado Pago. Não armazene dados de cartão no EmiteMax.

## Banco de dados

A migração `database/migrations/015_create_catalogo_vendas.sql` cria as tabelas
de catálogos, itens, pedidos e contas de pagamento. Ela já foi aplicada na base
configurada neste ambiente.
