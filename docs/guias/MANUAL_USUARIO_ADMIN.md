# 📘 Manual do Usuário Administrador
## Sistema de Nota Fiscal Eletrônica (NFe/NFCe)

---

**Versão:** 1.0  
**Data:** Dezembro de 2025  
**Público-alvo:** Usuários com perfil Administrador  
**Sistema:** API NFe - SJ Tecnologia

---

## 📑 Índice

1. [Introdução](#1-introdução)
2. [Acesso ao Sistema](#2-acesso-ao-sistema)
3. [Dashboard Principal](#3-dashboard-principal)
4. [Gerenciamento de Clientes](#4-gerenciamento-de-clientes)
5. [Gerenciamento de Usuários](#5-gerenciamento-de-usuários)
6. [Gerenciamento de Produtos](#6-gerenciamento-de-produtos)
7. [Gerenciamento de Destinatários/Tomadores NFe](#7-gerenciamento-de-Destinatários/Tomadores-nfe)
8. [Gerenciamento de Regras Tributárias](#8-gerenciamento-de-regras-tributárias)
9. [Gerenciamento de Certificados Digitais](#9-gerenciamento-de-certificados-digitais)
10. [Perguntas Frequentes (FAQ)](#10-perguntas-frequentes-faq)
11. [Suporte Técnico](#11-suporte-técnico)

---

## 1. Introdução

### 1.1 Sobre o Sistema

O Sistema de Nota Fiscal Eletrônica foi desenvolvido para facilitar a emissão de NFe (Nota Fiscal Eletrônica) e NFCe (Nota Fiscal de Consumidor Eletrônica) de acordo com as normas da SEFAZ (Secretaria da Fazenda).

### 1.2 Perfil do Usuário Administrador

Como **Administrador**, você possui permissões para:

✅ Gerenciar clientes (visualizar, editar - apenas os que você tem acesso)  
✅ Cadastrar e gerenciar produtos dos clientes  
✅ Cadastrar e gerenciar Destinatários/Tomadores de NFe  
✅ Configurar regras tributárias (ICMS, PIS, COFINS, IPI)  
✅ Fazer upload e gerenciar certificados digitais  
✅ Criar e gerenciar usuários para os clientes  
✅ Emitir NFe/NFCe para os clientes vinculados  

❌ **Limitações:** Você **não** pode criar novos clientes (apenas Super Admin)

### 1.3 Fluxo de Trabalho Recomendado

```
1. Verificar dados do cliente (razão social, endereço, regime tributário)
   ↓
2. Fazer upload do certificado digital do cliente
   ↓
3. Cadastrar produtos do cliente
   ↓
4. Cadastrar Destinatários/Tomadores frequentes
   ↓
5. Configurar regras tributárias
   ↓
6. Criar usuários para o cliente (opcional)
   ↓
7. Emitir NFe/NFCe
```

---

## 2. Acesso ao Sistema

### 2.1 Realizar Login

**Passo 1:** Abra o navegador e acesse a URL do sistema fornecida pelo administrador.

**Passo 2:** Você verá a tela de login:

![Tela de Login](Documentacao/screenshots/tela%20de%20login.png)

**Passo 3:** Digite suas credenciais:
- **Usuário:** Seu nome de usuário ou e-mail
- **Senha:** Sua senha de acesso

**Passo 4:** Clique no botão **"Entrar"**

### 2.2 Esqueci minha senha

Se você esqueceu sua senha, entre em contato com o Super Admin ou com o suporte técnico.

### 2.3 Primeiro Acesso

No primeiro acesso, recomenda-se:
- Alterar sua senha padrão
- Verificar quais clientes você tem permissão de acesso
- Familiarizar-se com o menu de navegação

---

## 3. Dashboard Principal

Após o login bem-sucedido, você será direcionado ao **Dashboard Principal**.

![Dashboard do Admin](Documentacao/screenshots/Dashboard%20do%20Admin.png)

### 3.1 Elementos da Tela

#### Menu Lateral Esquerdo
- **🏠 Home / Dashboard:** Tela inicial com indicadores
- **👥 Clientes:** Gerenciamento de clientes
- **👤 Usuários:** Gerenciamento de usuários
- **📦 Produtos:** Cadastro de produtos (requer selecionar cliente)
- **🎯 Destinatários/Tomadores:** Cadastro de Destinatários/Tomadores NFe
- **⚖️ Regras Tributárias:** Configuração de tributos
- **🔐 Certificados:** Gerenciamento de certificados digitais
- **📄 Emitir NFe:** Emissão de notas fiscais
- **📋 Consultar NFes:** Histórico de notas emitidas

#### Área Central - Indicadores
- **Total de NFes Emitidas:** Quantidade de notas no período
- **Total de NFCes Emitidas:** Quantidade de NFCe no período
- **Valor Total:** Soma dos valores das notas
- **Clientes Ativos:** Número de clientes com acesso

#### Filtros de Período
Utilize os filtros de data para visualizar indicadores de períodos específicos.

---

## 4. Gerenciamento de Clientes

### 4.1 Listar Clientes

**Caminho:** Menu Lateral → **Clientes**

![Lista de Clientes](Documentacao/screenshots/Lista%20de%20clientes.png)

Nesta tela você visualiza:
- **Razão Social:** Nome empresarial do cliente
- **CNPJ:** Número de identificação fiscal
- **Nome Fantasia:** Nome comercial
- **Regime Tributário:** Simples Nacional, Lucro Presumido, etc.
- **Ambiente:** Homologação ou Produção
- **Status:** Ativo ou Inativo
- **Ações:** Editar, Visualizar Produtos, Certificados, etc.

#### Barra de Pesquisa
Use a barra de pesquisa no topo da tabela para filtrar clientes por:
- Razão Social
- CNPJ
- Nome Fantasia

### 4.2 Editar Cliente

**Observação:** Você **não** pode criar novos clientes, apenas editar os existentes.

**Passo 1:** Na lista de clientes, clique no botão **"✏️ Editar"** do cliente desejado.

**Passo 2:** Você verá o formulário de edição:

![Formulário de Cliente](Documentacao/screenshots/Formulário%20de%20cadastro:edição%20de%20cliente.png)

### 4.3 Abas do Formulário de Cliente

O formulário possui várias abas:

#### 🆔 Aba: Dados do Cliente

**Seção: Informações Básicas**
- **Razão Social:** Nome empresarial registrado (obrigatório)
- **Nome Fantasia:** Nome comercial
- **CNPJ:** Cadastro Nacional de Pessoa Jurídica (obrigatório)
- **Inscrição Estadual:** Registro estadual
- **Inscrição Municipal:** Registro municipal
- **Regime Tributário:** Selecione o regime (obrigatório)
  - Simples Nacional
  - Lucro Presumido
  - Lucro Real
- **Ambiente de Emissão de NFe:** (obrigatório)
  - **1 - Homologação (Testes):** Para testes, NFe não tem valor fiscal
  - **2 - Produção (NFe Válida):** NFe válida fiscalmente
- **CNAE:** Código de atividade econômica

**Seção: Endereço**
- **CEP:** Digite e clique em "Buscar" para preencher automaticamente
- **Logradouro:** Rua, Avenida, etc.
- **Número:** Número do estabelecimento
- **Complemento:** Sala, Bloco, etc. (opcional)
- **Bairro:** Bairro
- **Município:** Nome da cidade
- **UF:** Estado (sigla)

**Seção: Contato**
- **Email:** Email para contato
- **Telefone:** Telefone para contato

**Status**
- ☑️ **Cliente Ativo:** Marque para manter o cliente ativo

**Passo 3:** Após preencher/atualizar os campos, clique em **"Salvar Cliente"**

#### 📦 Aba: Produtos

Esta aba lista todos os produtos cadastrados para o cliente. Consulte a seção [6. Gerenciamento de Produtos](#6-gerenciamento-de-produtos).

#### 🔐 Aba: Certificados

Esta aba lista todos os certificados digitais do cliente. Consulte a seção [9. Gerenciamento de Certificados Digitais](#9-gerenciamento-de-certificados-digitais).

#### ⚖️ Aba: Regras Tributárias

Esta aba lista todas as regras tributárias configuradas. Consulte a seção [8. Gerenciamento de Regras Tributárias](#8-gerenciamento-de-regras-tributárias).

#### 🎯 Aba: Destinatários/Tomadores

Esta aba lista todos os Destinatários/Tomadores cadastrados. Consulte a seção [7. Gerenciamento de Destinatários/Tomadores NFe](#7-gerenciamento-de-Destinatários/Tomadores-nfe).

### 4.4 Dicas Importantes - Clientes

⚠️ **CNPJ:** Deve ser válido e não pode estar duplicado no sistema  
⚠️ **Ambiente:** Mantenha em "Homologação" até validar completamente o cliente  
⚠️ **Regime Tributário:** Certifique-se de selecionar o correto, pois afeta a tributação  
💡 **Busca CEP:** Use a busca automática para evitar erros de digitação no endereço

---

## 5. Gerenciamento de Usuários

### 5.1 Listar Usuários

**Caminho:** Menu Lateral → **Usuários**

![Lista de Usuários](Documentacao/screenshots/Lista%20de%20usuários.png)

Nesta tela você visualiza:
- **Nome de Usuário:** Login do usuário
- **Email:** Email cadastrado
- **Roles:** Perfis de acesso (admin, cliente, super_admin)
- **Status:** Ativo ou Inativo
- **Clientes Vinculados:** Quais clientes o usuário pode acessar
- **Ações:** Editar, Desativar, Excluir

### 5.2 Criar Novo Usuário

**Passo 1:** Clique no botão **"➕ Adicionar Novo Usuário"**

**Passo 2:** Preencha o formulário:

![Formulário de Usuário](Documentacao/screenshots/Formulário%20de%20cadastro:edição%20de%20usuário.png)

#### Campos do Formulário

**Informações de Login**
- **Nome de Usuário:** Login único (obrigatório)
- **Email:** Email válido (obrigatório)
- **Senha:** Senha de acesso (obrigatório no cadastro)
- **Confirmar Senha:** Digite a senha novamente

**Perfil de Acesso (Role)**
- **admin:** Pode gerenciar produtos, regras, Destinatários/Tomadores, etc.
- **cliente:** Apenas emitir NFe e consultar histórico
- **super_admin:** Acesso total (apenas Super Admin pode conceder)

**Vinculação a Clientes**
- Selecione um ou mais clientes que o usuário poderá acessar
- Use Ctrl+Clique (Windows) ou Cmd+Clique (Mac) para múltipla seleção

**Status**
- ☑️ **Usuário Ativo:** Marque para ativar o usuário

**Passo 3:** Clique em **"Salvar Usuário"**

### 5.3 Editar Usuário Existente

**Passo 1:** Na lista de usuários, clique no botão **"✏️ Editar"**

**Passo 2:** Atualize os campos necessários

**Observação:** Para alterar a senha, deixe os campos de senha em branco. Preencha apenas se quiser alterar.

**Passo 3:** Clique em **"Salvar Usuário"**

### 5.4 Desativar/Ativar Usuário

Para desativar um usuário temporariamente:
1. Edite o usuário
2. Desmarque a opção **"Usuário Ativo"**
3. Salve

O usuário não conseguirá mais fazer login, mas seus dados permanecem no sistema.

### 5.5 Dicas Importantes - Usuários

⚠️ **Nome de Usuário:** Deve ser único no sistema  
⚠️ **Email:** Deve ser válido, pois notificações são enviadas por e-mail  
⚠️ **Senha:** Recomende senhas fortes (mínimo 8 caracteres, letras, números e símbolos)  
💡 **Vinculação:** Usuários só veem clientes aos quais estão vinculados  
💡 **Perfil Cliente:** Ideal para funcionários que apenas emitem notas  
💡 **Perfil Admin:** Ideal para você e outros administradores

---

## 6. Gerenciamento de Produtos

### 6.1 Acessar Produtos de um Cliente

**Opção 1 - Via Lista de Clientes:**
1. Menu → **Clientes**
2. Clique em **"📦 Produtos"** do cliente desejado

**Opção 2 - Via Edição de Cliente:**
1. Menu → **Clientes** → **Editar Cliente**
2. Clique na aba **"Produtos"**

![Lista de Produtos](Documentacao/screenshots/Lista%20de%20produtos%20de%20um%20cliente.png)

### 6.2 Cadastrar Novo Produto

**Passo 1:** Na lista de produtos, clique em **"➕ Adicionar Novo Produto"**

**Passo 2:** Preencha o formulário:

![Formulário de Produto](Documentacao/screenshots/Formulário%20de%20cadastro:edição%20de%20produto.png)

#### Seção: Informações Básicas

- **Código Interno:** Código de identificação interno (obrigatório)
- **Descrição:** Nome/descrição do produto (obrigatório)
- **Unidade Comercial:** UN, KG, CX, etc. (obrigatório)
- **Preço Unitário Padrão:** Valor de venda padrão

#### Seção: Classificação Fiscal

- **NCM:** Nomenclatura Comum do Mercosul (8 dígitos) (obrigatório)
  - Use o campo de busca para encontrar o NCM correto
  - Exemplo: 84159090 (Aparelhos de ar condicionado)
- **CEST:** Código Especificador da Substituição Tributária (opcional)
  - Obrigatório apenas para produtos com ST
- **CFOP Padrão:** Código Fiscal de Operações (obrigatório)
  - Exemplo: 5102 (Venda de mercadoria adquirida ou recebida de terceiros)
- **Origem da Mercadoria:** (obrigatório)
  - 0 - Nacional
  - 1 - Estrangeira (importação direta)
  - 2 - Estrangeira (adquirida no mercado interno)
  - Etc.

#### Seção: Tributação ICMS

**Se o cliente for do Simples Nacional:**
- **CSOSN:** Código de Situação da Operação no Simples Nacional
  - Exemplo: 102 (Tributada pelo Simples Nacional sem permissão de crédito)

**Se o cliente for de outro regime:**
- **CST ICMS:** Código de Situação Tributária
  - Exemplo: 00 (Tributada integralmente)

#### Seção: Estoque (Opcional)

- **Controlar Estoque:** Marque se deseja controlar estoque
- **Quantidade em Estoque:** Quantidade disponível
- **Estoque Mínimo:** Quantidade mínima de alerta

#### Seção: Status

- ☑️ **Produto Ativo:** Marque para disponibilizar o produto

**Passo 3:** Clique em **"Salvar Produto"**

### 6.3 Editar Produto

**Passo 1:** Na lista de produtos, clique em **"✏️ Editar"**

**Passo 2:** Atualize os campos necessários

**Passo 3:** Clique em **"Salvar Produto"**

### 6.4 Buscar Produto

Use a barra de pesquisa na lista de produtos para filtrar por:
- Código Interno
- Descrição
- NCM

### 6.5 Dicas Importantes - Produtos

⚠️ **NCM:** Deve ser válido e ter 8 dígitos  
⚠️ **CFOP:** Escolha o CFOP correto de acordo com a operação  
⚠️ **CSOSN/CST:** Fundamental para cálculo correto de impostos  
💡 **Código Interno:** Use um código fácil de lembrar (exemplo: SKU)  
💡 **Descrição:** Seja claro, essa descrição aparece na NFe  
💡 **Preço Padrão:** Pode ser alterado na emissão da NFe  
💡 **Regras Tributárias:** Configure regras tributárias para automação

---

## 7. Gerenciamento de Destinatários/Tomadores NFe

### 7.1 Listar Destinatários/Tomadores

**Caminho:** Menu Lateral → **Destinatários/Tomadores** ou via aba do cliente

![Lista de Destinatários/Tomadores](Documentacao/screenshots/Lista%20de%20Destinatários/Tomadores.png)

Nesta tela você visualiza:
- **Nome/Razão Social:** Nome do destinatário
- **CPF/CNPJ:** Documento
- **Tipo:** Pessoa Física ou Jurídica
- **Email:** Email cadastrado
- **Cidade/UF:** Localização
- **Ações:** Editar, Excluir

### 7.2 Cadastrar Novo Destinatário

**Passo 1:** Clique em **"➕ Adicionar Novo Destinatário"**

**Passo 2:** Preencha o formulário:

![Formulário de Destinatário](Documentacao/screenshots/Formulário%20de%20cadastro:edição%20de%20destinatário.png)

#### Seção: Identificação

- **Tipo de Pessoa:** (obrigatório)
  - **F - Física:** CPF
  - **J - Jurídica:** CNPJ
- **Nome/Razão Social:** Nome completo ou razão social (obrigatório)
- **CPF/CNPJ:** Documento de identificação (obrigatório)
- **Inscrição Estadual:** IE do destinatário (para PJ)
- **Indicador IE:** (obrigatório)
  - **C - Contribuinte ICMS:** Possui IE válida
  - **I - Isento:** Isento de IE
  - **N - Não Contribuinte:** Não possui IE

#### Seção: Contato

- **Email:** Email para envio da NFe (recomendado)
- **Telefone:** Telefone de contato

#### Seção: Endereço

- **CEP:** Digite e clique em "Buscar" para preencher automaticamente
- **Logradouro:** Endereço completo
- **Número:** Número
- **Complemento:** Apto, Sala, etc. (opcional)
- **Bairro:** Bairro
- **Município:** Cidade (obrigatório)
- **UF:** Estado (obrigatório)
- **Código do Município:** Código IBGE (preenchido automaticamente)
- **País:** Brasil (padrão)
- **Código País:** 1058 (padrão)

**Passo 3:** Clique em **"Salvar Destinatário"**

### 7.3 Editar Destinatário

**Passo 1:** Na lista, clique em **"✏️ Editar"**

**Passo 2:** Atualize os campos necessários

**Passo 3:** Clique em **"Salvar Destinatário"**

### 7.4 Excluir Destinatário

**Passo 1:** Clique no botão **"🗑️ Excluir"**

**Passo 2:** Confirme a exclusão

⚠️ **Atenção:** Destinatários/Tomadores com NFes já emitidas não podem ser excluídos.

### 7.5 Dicas Importantes - Destinatários/Tomadores

⚠️ **CPF/CNPJ:** Deve ser válido  
⚠️ **Indicador IE:** Escolha corretamente para evitar rejeição da NFe  
💡 **Email:** Essencial para envio automático da DANFE  
💡 **Busca CEP:** Evita erros de digitação no endereço  
💡 **Cadastro Prévio:** Cadastre Destinatários/Tomadores frequentes para agilizar emissão  
💡 **Consumidor Final:** Para NFCe, não é necessário cadastrar destinatário

---

## 8. Gerenciamento de Regras Tributárias

### 8.1 O que são Regras Tributárias?

As **Regras Tributárias** automatizam o cálculo de impostos (ICMS, PIS, COFINS, IPI) durante a emissão da NFe. Você configura as alíquotas e CSTs uma vez, e o sistema aplica automaticamente.

### 8.2 Listar Regras Tributárias

**Caminho:** Menu Lateral → **Regras Tributárias** ou via aba do cliente

![Lista de Regras](Documentacao/screenshots/Lista%20de%20regras%20tributárias.png)

Nesta tela você visualiza:
- **Descrição:** Nome da regra
- **NCM:** Código NCM vinculado
- **CFOP:** Operação fiscal
- **Tipo:** Produto ou Serviço
- **Regime:** Simples Nacional, Lucro Real, etc.
- **Ações:** Editar, Excluir

### 8.3 Criar Nova Regra Tributária

**Passo 1:** Clique em **"➕ Adicionar Nova Regra"**

**Passo 2:** Preencha o formulário:

![Formulário de Regra](Documentacao/screenshots/Formulário%20de%20cadastro:edição%20de%20regra.png)

#### Seção: Identificação

- **Descrição da Regra:** Nome descritivo (obrigatório)
  - Exemplo: "Eletrônicos SP p/ SP - Simples Nacional"
- **Tipo de Item:** (obrigatório)
  - **PRODUTO:** Mercadorias físicas
  - **SERVICO:** Prestação de serviços

#### Seção: Abrangência

- **Regime Tributário:** (obrigatório)
  - Selecione o regime do cliente
- **NCM:** Código NCM (obrigatório para produtos)
- **CFOP:** Código da operação (obrigatório)
- **UF Origem:** Estado de origem (obrigatório)
- **UF Destino:** Estado de destino (obrigatório)
  - Use "**" para aplicar a todos os estados

#### Seção: ICMS

**Para Simples Nacional:**
- **CSOSN:** Código CSOSN (obrigatório)
- **Alíquota ICMS (%):** Percentual do ICMS

**Para Outros Regimes:**
- **CST ICMS:** Código CST (obrigatório)
- **Alíquota ICMS (%):** Percentual do ICMS
- **Modalidade BC ICMS:** Forma de cálculo da base
- **% Redução BC ICMS:** Percentual de redução (se aplicável)

#### Seção: PIS

- **CST PIS:** Código de situação tributária (obrigatório)
- **Alíquota PIS (%):** Percentual do PIS
  - Padrão: 1,65% (regime cumulativo) ou 0,65% (não cumulativo)

#### Seção: COFINS

- **CST COFINS:** Código de situação tributária (obrigatório)
- **Alíquota COFINS (%):** Percentual do COFINS
  - Padrão: 7,60% (regime cumulativo) ou 3,00% (não cumulativo)

#### Seção: IPI

- **CST IPI:** Código de situação tributária
- **Alíquota IPI (%):** Percentual do IPI
  - Geralmente 0% para a maioria dos produtos

#### Seção: Observações

- **Observações:** Notas internas sobre a regra (opcional)

**Passo 3:** Clique em **"Salvar Regra"**

### 8.4 Editar Regra Tributária

**Passo 1:** Na lista, clique em **"✏️ Editar"**

**Passo 2:** Atualize os campos necessários

**Passo 3:** Clique em **"Salvar Regra"**

### 8.5 Excluir Regra

**Passo 1:** Clique no botão **"🗑️ Excluir"**

**Passo 2:** Confirme a exclusão

### 8.6 Prioridade de Aplicação das Regras

O sistema aplica as regras na seguinte ordem de prioridade:

1. **Mais Específica:** NCM + CFOP + UF Origem + UF Destino exatos
2. **Intermediária:** NCM + CFOP + UF Origem + UF Destino "**" (todos)
3. **Genérica:** NCM + CFOP apenas

### 8.7 Exemplos de Regras Comuns

#### Exemplo 1: Venda de Eletrônicos - SP para SP
```
Descrição: Eletrônicos SP → SP - Simples Nacional
NCM: 85171231 (Telefones celulares)
CFOP: 5102 (Venda dentro do estado)
UF Origem: SP
UF Destino: SP
Regime: Simples Nacional
CSOSN: 102
ICMS: 0%
PIS: 0%
COFINS: 0%
```

#### Exemplo 2: Venda Interestadual - SP para Qualquer Estado
```
Descrição: Eletrônicos SP → Outros Estados
NCM: 85171231
CFOP: 6102 (Venda fora do estado)
UF Origem: SP
UF Destino: ** (Todos)
Regime: Simples Nacional
CSOSN: 102
ICMS: 0%
PIS: 0%
COFINS: 0%
```

#### Exemplo 3: Lucro Real - Operação Tributada
```
Descrição: Venda Normal - Lucro Real
NCM: 22030001 (Cerveja)
CFOP: 5102
UF Origem: SP
UF Destino: SP
Regime: Lucro Real
CST ICMS: 00 (Tributada integralmente)
ICMS: 18%
CST PIS: 01
PIS: 1,65%
CST COFINS: 01
COFINS: 7,60%
```

### 8.8 Dicas Importantes - Regras Tributárias

⚠️ **NCM e CFOP:** Devem estar corretos para aplicação automática  
⚠️ **UF Destino:** Use "**" para regra geral (aplica a todos os estados)  
⚠️ **Alíquotas:** Consulte um contador para valores corretos  
💡 **Teste em Homologação:** Valide as regras antes de usar em produção  
💡 **Nomenclatura:** Use descrições claras para facilitar manutenção  
💡 **Uma Regra por Cenário:** Crie regras específicas para cada situação  
💡 **Prioridade:** Regras mais específicas têm prioridade sobre genéricas

---

## 9. Gerenciamento de Certificados Digitais

### 9.1 O que é o Certificado Digital?

O **Certificado Digital** é obrigatório para emitir NFe. Ele garante a autenticidade e seguridade jurídica da nota fiscal eletrônica perante a SEFAZ.

**Tipos aceitos:** A1 (arquivo .pfx ou .p12)

### 9.2 Listar Certificados

**Caminho:** Via edição do cliente → Aba **"Certificados"**

![Lista de Certificados](Documentacao/screenshots/Lista%20de%20certificados%20de%20um%20cliente.png)

Nesta tela você visualiza:
- **Nome do Arquivo:** Nome do certificado enviado
- **Data de Upload:** Quando foi carregado
- **Data de Validade:** Quando expira
- **Status:** Ativo ou Inativo
- **Ações:** Baixar, Ativar, Desativar, Excluir

### 9.3 Fazer Upload de Certificado

**Passo 1:** Na lista de certificados, clique em **"➕ Adicionar Novo Certificado"**

**Passo 2:** Preencha o formulário:

#### Campos do Formulário

- **Arquivo do Certificado (.pfx):** Clique em "Escolher arquivo" e selecione o arquivo .pfx do cliente
- **Senha do Certificado:** Digite a senha do certificado (obrigatório)
- ☑️ **Certificado Ativo:** Marque se deseja ativar imediatamente

**Passo 3:** Clique em **"Salvar Certificado"**

**Observação:** O sistema valida o certificado automaticamente. Se a senha estiver incorreta ou o certificado inválido, você receberá uma mensagem de erro.

### 9.4 Ativar/Desativar Certificado

Apenas **um certificado pode estar ativo** por cliente por vez.

**Para Ativar:**
1. Clique no botão **"✅ Ativar"** do certificado desejado
2. O certificado anteriormente ativo será desativado automaticamente

**Para Desativar:**
1. Clique no botão **"❌ Desativar"**

⚠️ **Atenção:** Sem certificado ativo, não é possível emitir NFe.

### 9.5 Baixar Certificado

**Passo 1:** Clique no botão **"📥 Baixar"**

**Passo 2:** O arquivo .pfx será baixado

⚠️ **Segurança:** Mantenha o certificado em local seguro e não compartilhe a senha.

### 9.6 Excluir Certificado

**Passo 1:** Clique no botão **"🗑️ Excluir"**

**Passo 2:** Confirme a exclusão

⚠️ **Atenção:** Certificados ativos não podem ser excluídos. Desative antes de excluir.

### 9.7 Renovação de Certificado

Certificados digitais têm validade limitada (geralmente 1 ano).

**Quando Renovar:**
- O sistema exibe um alerta quando o certificado está próximo do vencimento (30 dias antes)
- Acesse a lista de certificados para verificar a data de validade

**Como Renovar:**
1. Adquira um novo certificado digital junto à Autoridade Certificadora
2. Faça upload do novo certificado (não precisa excluir o antigo)
3. Ative o novo certificado
4. O certificado antigo será desativado automaticamente

### 9.8 Dicas Importantes - Certificados

⚠️ **Senha Correta:** Certifique-se de ter a senha antes de fazer upload  
⚠️ **Validade:** Verifique a data de validade antes de usar  
⚠️ **Backup:** Mantenha cópia segura do certificado  
⚠️ **Renovação:** Não espere vencer, renove com antecedência  
💡 **Um por Vez:** Apenas um certificado ativo por cliente  
💡 **Homologação vs Produção:** Use certificado válido mesmo em homologação  
💡 **Arquivo .pfx:** Certifique-se de que o arquivo está no formato correto

---

## 10. Perguntas Frequentes (FAQ)

### 10.1 Acesso e Permissões

**P: Posso criar novos clientes?**  
R: Não. Apenas o Super Admin pode criar novos clientes. Você pode editar clientes existentes aos quais tem acesso.

**P: Como solicito acesso a um novo cliente?**  
R: Entre em contato com o Super Admin e solicite a vinculação do seu usuário ao cliente desejado.

**P: Esqueci minha senha, o que fazer?**  
R: Entre em contato com o Super Admin ou suporte técnico para redefinição de senha.

### 10.2 Certificados

**P: Posso usar o mesmo certificado para Homologação e Produção?**  
R: Sim. O mesmo certificado digital é válido para ambos os ambientes. O ambiente é definido no cadastro do cliente.

**P: Meu certificado está vencido, posso emitir NFe?**  
R: Não. A SEFAZ rejeita NFes assinadas com certificados vencidos. Renove o certificado urgentemente.

**P: Como sei quando meu certificado vai vencer?**  
R: O sistema exibe alertas 30 dias antes do vencimento. Você também pode verificar na lista de certificados.

### 10.3 Produtos

**P: Como busco o NCM correto?**  
R: No cadastro de produto, use o campo de busca NCM. Digite palavras-chave do produto ou o próprio código NCM.

**P: Posso cadastrar produtos sem NCM?**  
R: Não. O NCM é obrigatório para emissão de NFe. Se não souber, consulte a tabela NCM completa ou um contador.

**P: Como funciona o controle de estoque?**  
R: Ao marcar "Controlar Estoque", o sistema deduz a quantidade automaticamente a cada NFe emitida.

### 10.4 Regras Tributárias

**P: As regras são aplicadas automaticamente?**  
R: Sim. Ao selecionar um produto na emissão da NFe, o sistema busca a regra tributária correspondente e preenche automaticamente os impostos.

**P: E se não houver regra cadastrada?**  
R: Você precisará preencher manualmente os campos tributários na emissão da NFe.

**P: Como sei se a regra está correta?**  
R: Teste em ambiente de Homologação primeiro. Consulte um contador para validar alíquotas e CSTs.

### 10.5 Destinatários/Tomadores

**P: Preciso cadastrar todos os Destinatários/Tomadores?**  
R: Não é obrigatório. Você pode digitar os dados diretamente na emissão. Porém, cadastrar Destinatários/Tomadores frequentes agiliza o processo.

**P: Posso emitir NFCe sem destinatário?**  
R: Sim. NFCe (Nota Fiscal de Consumidor) permite venda sem identificação do destinatário (consumidor final não identificado).

### 10.6 Emissão de NFe

**P: Como sei se a NFe foi aceita pela SEFAZ?**  
R: Após emitir, o sistema exibe o status da NFe. Se aceita, você verá o número de protocolo e poderá baixar a DANFE.

**P: Posso cancelar uma NFe?**  
R: Sim, desde que dentro do prazo legal (geralmente 24 horas). Acesse a lista de NFes e clique em "Cancelar".

**P: A NFe é enviada automaticamente por email?**  
R: Sim, se o destinatário tiver email cadastrado. A DANFE e o XML são enviados automaticamente após autorização.

### 10.7 Ambiente (Homologação vs Produção)

**P: Qual a diferença entre Homologação e Produção?**  
R:
- **Homologação:** Para testes. NFe emitida não tem valor fiscal. Aparece como "SEM VALOR FISCAL" na DANFE.
- **Produção:** NFe válida fiscalmente, deve ser enviada ao destinatário e escriturada.

**P: Posso mudar um cliente de Homologação para Produção?**  
R: Sim. Edite o cliente e altere o campo "Ambiente de Emissão" de "1 - Homologação" para "2 - Produção".

**P: NFes de Homologação aparecem na lista de NFes?**  
R: Sim, mas são marcadas como "Homologação". Use os filtros para separar.

---

## 11. Suporte Técnico

### 11.1 Canais de Atendimento

**📧 Email:** suporte@sjtecnologia.com.br  
**📞 Telefone:** (00) 0000-0000  
**💬 Chat:** Disponível no sistema (canto inferior direito)  
**⏰ Horário:** Segunda a Sexta, 8h às 18h

### 11.2 Informações para Abertura de Chamado

Ao entrar em contato com o suporte, tenha em mãos:
- Seu **nome de usuário**
- **Cliente** relacionado ao problema
- **Descrição detalhada** do erro ou dúvida
- **Prints de tela** (se possível)
- **Mensagem de erro** (se houver)

### 11.3 Documentação Adicional

- **Manual da SEFAZ:** [Portal da Nota Fiscal Eletrônica](http://www.nfe.fazenda.gov.br/)
- **Tabela NCM:** Disponível no sistema ou em [www.gov.br](https://www.gov.br/receitafederal/pt-br/assuntos/aduana-e-comercio-exterior/manuais/nomenclatura-comum-do-mercosul-ncm)
- **Tabela CFOP:** Consulte seu contador ou [legislação estadual](https://www.confaz.fazenda.gov.br/)

---

## 📝 Glossário

**CFOP:** Código Fiscal de Operações e Prestações  
**CNPJ:** Cadastro Nacional de Pessoa Jurídica  
**CPF:** Cadastro de Pessoa Física  
**CST:** Código de Situação Tributária  
**CSOSN:** Código de Situação da Operação no Simples Nacional  
**DANFE:** Documento Auxiliar da Nota Fiscal Eletrônica  
**IE:** Inscrição Estadual  
**ICMS:** Imposto sobre Circulação de Mercadorias e Serviços  
**IPI:** Imposto sobre Produtos Industrializados  
**NCM:** Nomenclatura Comum do Mercosul  
**NFe:** Nota Fiscal Eletrônica (modelo 55)  
**NFCe:** Nota Fiscal de Consumidor Eletrônica (modelo 65)  
**PIS:** Programa de Integração Social  
**COFINS:** Contribuição para o Financiamento da Seguridade Social  
**SEFAZ:** Secretaria da Fazenda  
**UF:** Unidade Federativa (Estado)

---

## 📄 Histórico de Versões

| Versão | Data       | Descrição                          | Autor        |
|--------|------------|------------------------------------|--------------|
| 1.0    | Dez/2025   | Versão inicial do manual           | SJ Tecnologia|

---

## ✅ Checklist Rápido - Novo Cliente

Use este checklist ao configurar um novo cliente:

- [ ] **1. Verificar dados do cliente**
  - [ ] Razão Social correta
  - [ ] CNPJ válido
  - [ ] Endereço completo e correto
  - [ ] Regime tributário correto
  - [ ] Ambiente: Homologação (inicialmente)
  
- [ ] **2. Upload do Certificado Digital**
  - [ ] Arquivo .pfx obtido
  - [ ] Senha do certificado em mãos
  - [ ] Upload realizado com sucesso
  - [ ] Certificado ativado

- [ ] **3. Cadastrar Produtos**
  - [ ] Pelo menos 1 produto cadastrado
  - [ ] NCM correto
  - [ ] CFOP padrão definido
  - [ ] CSOSN/CST configurado
  - [ ] Preço unitário definido

- [ ] **4. Cadastrar Destinatários/Tomadores (Opcional)**
  - [ ] Destinatários/Tomadores frequentes cadastrados
  - [ ] CPF/CNPJ válidos
  - [ ] Endereços completos
  - [ ] Email para recebimento de DANFE

- [ ] **5. Configurar Regras Tributárias**
  - [ ] Regras para operações internas (dentro do estado)
  - [ ] Regras para operações interestaduais
  - [ ] Alíquotas validadas por contador

- [ ] **6. Criar Usuários (Se necessário)**
  - [ ] Usuário criado com login e senha
  - [ ] Perfil adequado atribuído (admin/cliente)
  - [ ] Vinculado ao cliente correto

- [ ] **7. Teste em Homologação**
  - [ ] Emitir NFe de teste
  - [ ] Verificar autorização da SEFAZ
  - [ ] Baixar DANFE e XML
  - [ ] Validar cálculos de impostos

- [ ] **8. Migração para Produção**
  - [ ] Todos os testes concluídos
  - [ ] Cliente aprovado para produção
  - [ ] Alterar ambiente para "2 - Produção"
  - [ ] Emitir primeira NFe real

---

**© 2025 SJ Tecnologia - Todos os direitos reservados**

---

**FIM DO MANUAL**
