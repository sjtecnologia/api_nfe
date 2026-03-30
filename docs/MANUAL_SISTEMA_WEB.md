# 📘 Manual do Sistema EmiteMax - Interface Web

**Versão:** 2.0  
**Data:** Fevereiro de 2026  
**Suporte:** contato@emitemax.com.br  
**WhatsApp:** (17) 98810-5545

---

## 📋 Índice

1. [Introdução](#introdução)
2. [Acesso ao Sistema](#acesso-ao-sistema)
3. [Dashboard](#dashboard)
4. [Emissão de Notas Fiscais](#emissão-de-notas-fiscais)
   - [NFe - Nota Fiscal Eletrônica](#nfe---nota-fiscal-eletrônica)
   - [NFC-e - Nota Fiscal do Consumidor](#nfc-e---nota-fiscal-do-consumidor)
   - [NFS-e - Nota Fiscal de Serviço](#nfs-e---nota-fiscal-de-serviço)
5. [Gerenciamento](#gerenciamento)
   - [Produtos](#produtos)
   - [Serviços](#serviços)
   - [Clientes e Destinatários](#clientes-e-destinatários)
   - [Certificado Digital](#certificado-digital)
6. [Regras Tributárias](#regras-tributárias)
7. [Configurações](#configurações)
8. [Relatórios e Consultas](#relatórios-e-consultas)
9. [Suporte e Ajuda](#suporte-e-ajuda)

---

## 🎯 Introdução

O **EmiteMax** é um sistema completo de emissão de notas fiscais eletrônicas que oferece:

- ✅ **Emissão Simplificada**: Interface intuitiva para emitir NFe, NFC-e e NFS-e
- 🤖 **Tributação Automática**: Sistema inteligente que calcula impostos automaticamente
- 📧 **Envio Automático**: Emails com XML e DANFE enviados automaticamente ao cliente
- 📊 **Dashboard Completo**: Acompanhe suas emissões em tempo real
- 🔒 **Segurança**: Certificado digital armazenado com criptografia
- 💸 **Planos Flexíveis**: Escolha o plano ideal para seu negócio

**URL do Sistema:** https://api.emitemax.com.br

---

## 🔐 Acesso ao Sistema

### Primeiro Acesso

1. Acesse: https://api.emitemax.com.br
2. Clique em **"Criar Conta"**
3. Preencha seus dados:
   - Nome completo
   - Email
   - Senha (mínimo 8 caracteres)
   - CNPJ da empresa
4. Confirme seu email
5. Faça login no sistema

### Login

1. Acesse: https://api.emitemax.com.br
2. Informe seu **email** e **senha**
3. Clique em **"Entrar"**

### Recuperação de Senha

1. Na tela de login, clique em **"Esqueci minha senha"**
2. Informe seu email cadastrado
3. Você receberá um link para redefinir sua senha
4. Acesse o link e cadastre uma nova senha

---

## 📊 Dashboard

O Dashboard é a tela inicial do sistema e mostra informações importantes:

### Indicadores Principais

- **📈 Notas Emitidas (Mês)**: Total de notas emitidas no mês atual
- **💰 Faturamento (Mês)**: Valor total das notas do mês
- **📋 Notas Pendentes**: Rascunhos e notas aguardando autorização
- **⚠️ Limite do Plano**: Quantas notas você ainda pode emitir neste mês

### Gráficos e Relatórios

- **Evolução Mensal**: Gráfico de emissões por mês
- **Notas por Status**: Distribuição entre autorizadas, canceladas, denegadas
- **Últimas Notas**: Lista das 10 últimas notas emitidas

### Ações Rápidas

- 🚀 **Emitir NFe**: Acesso rápido para nova emissão
- 📦 **Emitir NFC-e**: Emissão de cupom fiscal
- 🔍 **Consultar Notas**: Buscar notas emitidas
- ⚙️ **Configurações**: Acesso às configurações do sistema

---

## 📝 Emissão de Notas Fiscais

### NFe - Nota Fiscal Eletrônica

A NFe (modelo 55) é utilizada para operações de venda de produtos.

#### Como Emitir uma NFe

1. **Acesse**: Menu **"NFe"** → **"Emitir NFe"**

2. **Dados do Destinatário**:
   - CPF/CNPJ
   - Nome/Razão Social
   - Endereço completo
   - Email (para envio automático)
   - Telefone

3. **Produtos**:
   - Clique em **"Adicionar Produto"**
   - Busque o produto cadastrado ou cadastre um novo
   - Informe:
     - Código do produto
     - Descrição
     - NCM (classificação fiscal)
     - Quantidade
     - Valor unitário
     - CFOP (natureza da operação)
   
   **💡 Dica**: O sistema calcula automaticamente os impostos com base no NCM e CFOP!

4. **Dados da Nota**:
   - Natureza da Operação (ex: "Venda de Mercadoria")
   - Informações Adicionais (opcional)
   - Forma de Pagamento

5. **Tributação Automática**:
   - O sistema busca automaticamente as regras tributárias
   - Validação inteligente com IA antes da emissão
   - Cálculos de ICMS, IPI, PIS, COFINS automáticos

6. **Emitir**:
   - Clique em **"Salvar como Rascunho"** para revisar depois
   - Ou clique em **"Emitir NFe"** para enviar à SEFAZ

7. **Após Autorização**:
   - ✅ NFe é autorizada pela SEFAZ
   - 📧 Email automático enviado ao destinatário (XML + DANFE)
   - 📄 DANFE (PDF) disponível para impressão
   - 💾 XML disponível para download

#### Recursos Especiais da NFe

- **🤖 Tributação Automática**: Sistema calcula impostos automaticamente
- **✅ Validação IA**: Inteligência artificial valida regras antes da emissão
- **📧 Email Automático**: Cliente recebe XML e DANFE automaticamente
- **🔄 Numeração Automática**: Sistema controla numeração sequencial
- **📊 IBS/CBS (Reforma Tributária)**: Suporte para novos impostos

---

### NFC-e - Nota Fiscal do Consumidor

A NFC-e (modelo 65) é utilizada para vendas ao consumidor final (varejo).

#### Como Emitir uma NFC-e

1. **Acesse**: Menu **"NFC-e"** → **"Emitir NFC-e"**

2. **Identificação do Cliente** (opcional):
   - CPF/CNPJ (opcional para consumidor final)
   - Nome (opcional)
   - Email (para envio do DANFE)

3. **Produtos**:
   - Adicione os produtos vendidos
   - Informe quantidade e valor
   - Tributação aplicada automaticamente

4. **Pagamento**:
   - Forma de pagamento:
     - Dinheiro
     - Cartão de Crédito
     - Cartão de Débito
     - PIX
     - Outros

5. **Emitir**:
   - Clique em **"Emitir NFC-e"**
   - Aguarde autorização da SEFAZ
   - DANFE é gerado automaticamente

6. **Após Autorização**:
   - 🖨️ Imprima o cupom (DANFE NFC-e)
   - 📱 Mostre o QR Code para o cliente
   - 📧 Envie por email (se informado)

#### Diferenças NFe vs NFC-e

| Característica | NFe | NFC-e |
|----------------|-----|-------|
| **Modelo** | 55 | 65 |
| **Uso** | Venda entre empresas | Venda ao consumidor |
| **Destinatário** | Obrigatório | Opcional |
| **DANFE** | A4 (completo) | Cupom (simplificado) |
| **QR Code** | Não | Sim |
| **Contingência** | FS-DA, EPEC | Offline (SAT) |

---

### NFS-e - Nota Fiscal de Serviço

A NFS-e é utilizada para prestação de serviços.

#### Como Emitir uma NFS-e

1. **Acesse**: Menu **"NFS-e"** → **"Emitir NFS-e"**

2. **Dados do Tomador de Serviço**:
   - CPF/CNPJ
   - Nome/Razão Social
   - Endereço
   - Email

3. **Serviços Prestados**:
   - Clique em **"Adicionar Serviço"**
   - Informe:
     - Código do serviço (NBS)
     - Descrição do serviço
     - Quantidade de horas ou unidades
     - Valor unitário
     - Alíquota de ISS

4. **Dados da Nota**:
   - Discriminação do serviço (descrição detalhada)
   - Informações adicionais
   - Local da prestação do serviço

5. **Impostos**:
   - ISS (calculado automaticamente)
   - Retenções (se aplicável):
     - IR
     - PIS
     - COFINS
     - CSLL
     - INSS

6. **Emitir**:
   - Clique em **"Emitir NFS-e"**
   - Aguarde processamento pela Prefeitura
   - PDF disponível após autorização

**⚠️ Importante**: Cada prefeitura tem seu próprio sistema de NFS-e. Verifique se seu município está integrado.

---

## 🗂️ Gerenciamento

### Produtos

Cadastre e gerencie seus produtos para emissão rápida de notas.

#### Como Cadastrar um Produto

1. **Acesse**: Menu **"Produtos"** → **"Novo Produto"**

2. **Dados Básicos**:
   - Código interno (SKU)
   - Descrição do produto
   - Unidade (UN, KG, CX, etc.)
   - Valor unitário

3. **Classificação Fiscal**:
   - **NCM**: Busque pelo nome do produto
     - Sistema tem IA integrada para sugerir NCM correto
     - Ex: "Cadeira de escritório" → NCM sugerido automaticamente
   - **CEST**: Código especial para substituição tributária (se aplicável)
   - **Origem da mercadoria**: Nacional, importada, etc.

4. **Tributação Padrão**:
   - CFOP padrão
   - CST/CSOSN de ICMS
   - CST PIS/COFINS
   - Sistema busca regras automaticamente na emissão

5. **IBS/CBS** (Reforma Tributária):
   - Alíquota IBS (se CRT = 3)
   - Alíquota CBS (se CRT = 3)

6. **Salvar**: Clique em **"Salvar Produto"**

#### Buscar Produtos

- Use a busca por código, descrição ou NCM
- Filtre por categoria ou status (ativo/inativo)
- Visualize histórico de vendas do produto

---

### Serviços

Cadastre serviços para emissão de NFS-e.

#### Como Cadastrar um Serviço

1. **Acesse**: Menu **"Serviços"** → **"Novo Serviço"**

2. **Dados do Serviço**:
   - Código interno
   - Descrição do serviço
   - Unidade (hora, dia, mês, etc.)
   - Valor unitário

3. **Classificação**:
   - **NBS**: Nomenclatura Brasileira de Serviços
   - Sistema sugere NBS baseado na descrição
   - **Item da Lista**: Código municipal do serviço

4. **Tributação**:
   - Alíquota de ISS
   - Exigibilidade do ISS
   - Retenções (IR, PIS, COFINS, etc.)
   - **IBS/CBS** (Reforma Tributária)

5. **Salvar**: Clique em **"Salvar Serviço"**

---

### Clientes e Destinatários

Gerencie sua carteira de clientes.

#### Como Cadastrar um Cliente

1. **Acesse**: Menu **"Clientes"** → **"Novo Cliente"**

2. **Dados Básicos**:
   - CPF ou CNPJ
   - Nome ou Razão Social
   - Nome Fantasia
   - Telefone
   - **Email** (importante para envio automático de notas)

3. **Endereço**:
   - CEP (sistema busca endereço automaticamente)
   - Logradouro
   - Número
   - Complemento
   - Bairro
   - Cidade/UF

4. **Dados Fiscais**:
   - Inscrição Estadual (se tiver)
   - Indicador IE:
     - Contribuinte ICMS
     - Contribuinte isento
     - Não contribuinte

5. **Salvar**: Clique em **"Salvar Cliente"**

#### Importar Clientes

- Acesse **"Clientes"** → **"Importar"**
- Baixe o modelo de planilha Excel
- Preencha os dados
- Faça upload do arquivo
- Sistema valida e importa automaticamente

---

### Certificado Digital

O certificado digital é obrigatório para emissão de notas fiscais.

#### Como Instalar o Certificado

1. **Acesse**: Menu **"Configurações"** → **"Certificado Digital"**

2. **Upload do Certificado**:
   - Clique em **"Enviar Certificado"**
   - Selecione o arquivo **.pfx** ou **.p12**
   - Informe a **senha do certificado**
   - Clique em **"Enviar"**

3. **Validação**:
   - Sistema valida o certificado
   - Verifica a validade (não pode estar vencido)
   - Confirma que pertence ao CNPJ da empresa

4. **Armazenamento Seguro**:
   - Certificado é criptografado no servidor
   - Senha não é armazenada em texto puro
   - Renovação automática de sessão

#### Status do Certificado

- ✅ **Válido**: Certificado instalado e funcionando
- ⚠️ **Vencendo**: Faltam menos de 30 dias para vencer
- ❌ **Vencido**: Certificado expirou, renove urgente
- 🔒 **Não instalado**: Nenhum certificado configurado

#### Renovação

Quando seu certificado for vencer:
1. Adquira um novo certificado na Autoridade Certificadora
2. Instale o novo certificado seguindo o processo acima
3. O sistema substituirá automaticamente o antigo

---

## 📋 Regras Tributárias

O sistema possui **tributação automática** com inteligência artificial.

### Como Funciona

1. **Cadastro Automático**: Ao emitir uma nota, o sistema:
   - Identifica o NCM/NBS
   - Identifica o CFOP
   - Busca regras tributárias aplicáveis
   - Calcula impostos automaticamente

2. **Validação IA**: Antes de enviar à SEFAZ:
   - Inteligência artificial valida as regras
   - Verifica inconsistências
   - Alerta sobre possíveis erros
   - Sugere correções

3. **Regras por Regime**:
   - **Simples Nacional**: CSOSN, sem cálculo de ICMS
   - **Lucro Presumido/Real**: CST, cálculos completos de ICMS, IPI, PIS, COFINS
   - **MEI**: Isento de ICMS

### Consultar Regras Tributárias

1. **Acesse**: Menu **"Tributação"** → **"Regras Cadastradas"**

2. **Filtros Disponíveis**:
   - Por NCM
   - Por CFOP
   - Por estado (UF)
   - Por regime tributário

3. **Visualizar Detalhes**:
   - Clique na regra para ver:
     - CST/CSOSN aplicável
     - Alíquotas de impostos
     - Reduções de base de cálculo
     - Benefícios fiscais

### Criar Regra Personalizada

Para criar uma regra específica para sua empresa:

1. **Acesse**: Menu **"Tributação"** → **"Nova Regra"**

2. **Parâmetros**:
   - NCM do produto
   - CFOP da operação
   - UF de origem e destino
   - Regime tributário (CRT)

3. **Impostos**:
   - Configure CST/CSOSN
   - Defina alíquotas
   - Configure reduções
   - Adicione benefícios fiscais

4. **Validar**: Sistema valida a regra com IA

5. **Salvar**: Regra fica disponível para uso

---

## ⚙️ Configurações

### Dados da Empresa

Configure os dados do emitente.

1. **Acesse**: Menu **"Configurações"** → **"Dados da Empresa"**

2. **Informações**:
   - Razão Social
   - Nome Fantasia
   - CNPJ
   - Inscrição Estadual
   - Inscrição Municipal
   - Endereço completo
   - Logo da empresa (para DANFE)

3. **Regime Tributário (CRT)**:
   - **1**: Simples Nacional
   - **2**: Simples Nacional - Excesso
   - **3**: Regime Normal (Lucro Presumido/Real)

4. **Numeração das Notas**:
   - Série da NFe (padrão: 1)
   - Próximo número disponível
   - Série da NFC-e
   - Série da NFS-e

### Ambiente SEFAZ

Configure o ambiente de emissão.

1. **Homologação**:
   - Para testes
   - Notas sem valor fiscal
   - Ideal para aprender o sistema

2. **Produção**:
   - Emissão oficial
   - Notas com valor fiscal
   - Necessário certificado válido

**⚠️ Atenção**: Em homologação, use CNPJ de teste da SEFAZ nos destinatários.

### Emails

O sistema envia automaticamente o XML e DANFE da NFe por email para o destinatário.

**✅ Configuração Atual**: Sistema já está configurado para envio automático!

---

## 📊 Relatórios e Consultas

### Consultar Notas Emitidas

1. **Acesse**: Menu **"Consultas"** → **"Notas Emitidas"**

2. **Filtros**:
   - Período (data início/fim)
   - Tipo de nota (NFe, NFC-e, NFS-e)
   - Status (autorizada, cancelada, denegada)
   - Cliente/Destinatário
   - Número da nota

3. **Ações Disponíveis**:
   - 👁️ **Visualizar**: Ver detalhes da nota
   - 📄 **Download XML**: Baixar arquivo XML
   - 🖨️ **Download DANFE/PDF**: Baixar impressão
   - 📧 **Reenviar Email**: Enviar novamente para cliente
   - ❌ **Cancelar**: Cancelar nota (em até 24h)
   - 📋 **Carta de Correção**: Corrigir informações (NFe)

---

## ❓ Suporte e Ajuda

### Email

**contato@emitemax.com.br**

- Envie suas dúvidas, sugestões ou problemas
- Anexe prints de tela se necessário
- Resposta em até 24 horas úteis

### WhatsApp

**(17) 98810-5545**

- Atendimento por mensagem
- Segunda a sexta, 9h às 18h
- Apenas para clientes dos planos Pro e Enterprise: atendimento por ligação

### Abrir Chamado

Para problemas técnicos mais complexos:

1. **Acesse**: Menu **"Ajuda"** → **"Abrir Chamado"**
2. Preencha:
   - Categoria do problema
   - Descrição detalhada
   - Anexos (prints, XMLs, logs)
   - Prioridade
3. Acompanhe o status do chamado
4. Receba notificações por email

---

## 🎓 Dicas e Boas Práticas

### 1. Mantenha seus Dados Atualizados

- Revise os dados da empresa periodicamente
- Mantenha o cadastro de produtos atualizado
- Atualize preços e NCMs quando necessário

### 2. Backup Regular

- Faça download dos XMLs mensalmente
- Mantenha backup local dos arquivos fiscais
- Exporte relatórios importantes

### 3. Certificado Digital

- Renove o certificado com pelo menos 30 dias de antecedência
- Guarde a senha do certificado em local seguro
- Use certificado A1 para maior praticidade

### 4. Tributação

- Revise as regras tributárias trimestralmente
- Fique atento a mudanças na legislação
- Consulte seu contador em caso de dúvida

### 5. Email Automático

- Certifique-se que o email do cliente está correto
- O sistema envia XML + DANFE automaticamente
- Cliente não recebeu? Verifique spam/lixeira

### 6. Contingência Automática (SVC)

Quando a SEFAZ autorizadora está fora do ar, o sistema entra em contingência **automaticamente**:

1. O sistema tenta emitir normalmente na SEFAZ do estado
2. Se detectar que a SEFAZ está indisponível (timeout, erro de conexão, código 108/109), ativa a contingência
3. A nota é **reemitida automaticamente** via SEFAZ Virtual de Contingência (SVC-AN ou SVC-RS, conforme a UF)
4. O XML é ajustado com `tpEmis=6` (SVC-AN) ou `tpEmis=7` (SVC-RS), chave de acesso recalculada e reassinada
5. A nota é autorizada em tempo real pelo servidor de contingência
6. Quando a SEFAZ normal voltar, o sistema detecta e sai da contingência automaticamente

**Importante**: A nota emitida em contingência tem **validade jurídica plena** — é autorizada online por um servidor alternativo da Receita Federal.

| UF do Emitente | Servidor de Contingência |
|---|---|
| SP, MG, RJ, ES, SC, BA e outras 9 UFs | **SVC-RS** (tpEmis=7) |
| AM, CE, GO, PR, RS e outras 7 UFs | **SVC-AN** (tpEmis=6) |

Você pode consultar se alguma UF está em contingência acessando **Notas Fiscais > Status Contingência**.

### 7. Validação IA

- Preste atenção aos alertas da IA
- Se houver sugestão de correção, avalie com cuidado
- Validação IA previne rejeições e multas

---

## 📱 App Mobile (Em Breve)

Estamos desenvolvendo o app mobile do EmiteMax!

**Recursos**:
- Emissão de NFC-e direto do celular
- Consulta de notas
- Dashboard mobile
- Notificações push
- Leitura de QR Code

**Disponibilidade**: iOS e Android

**Previsão**: 2º trimestre de 2026

---

## 🆕 Novidades e Atualizações

### Fevereiro 2026

- ✅ **Email Automático**: XML + DANFE enviados automaticamente
- ✅ **Template Profissional**: Email com logo EmiteMax
- ✅ **Validação IA Melhorada**: Precisão aumentada em 30%
- ✅ **IBS/CBS**: Suporte completo para Reforma Tributária

### Janeiro 2026

- ✅ **NFS-e São José do Rio Preto**: Integração com GISS
- ✅ **Assistente IA**: Sugestão automática de NCM/NBS
- ✅ **Dashboard Renovado**: Novo visual e gráficos

---

## 📞 Contato

Para dúvidas, sugestões ou suporte técnico:

- **Email**: contato@emitemax.com.br
- **WhatsApp**: (17) 98810-5545
- **Site**: https://api.emitemax.com.br
- **Documentação API**: https://api.emitemax.com.br/docs

**Horário de Atendimento**:
- Segunda a Sexta: 9h às 18h
- Sábado: 9h às 12h

---

## 📄 Termos e Condições

Este sistema está sujeito aos **Termos de Uso** e **Política de Privacidade** disponíveis em:

- https://api.emitemax.com.br/termos
- https://api.emitemax.com.br/privacidade

**EmiteMax** - Sistema de Emissão de Notas Fiscais Eletrônicas  
**Versão do Manual**: 2.0 - Fevereiro de 2026

---

**🎉 Obrigado por escolher o EmiteMax!**

Estamos aqui para facilitar sua emissão de notas fiscais e fazer seu negócio crescer! 🚀
