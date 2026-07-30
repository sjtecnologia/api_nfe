# Implementação Funcionalidade Inutilização de Numeração - 12/02/2026

## Resumo da Sessão
**Período:** 12 de fevereiro de 2026  
**Objetivo Principal:** Implementar funcionalidade completa de inutilização de numeração de NFe/NFCe  
**Branch:** lc214-migration  
**Ambiente:** AWS EC2 (100.26.12.107) + RDS PostgreSQL  

## Funcionalidade Implementada

### Descrição
Sistema de inutilização de numeração conforme legislação brasileira para NFe/NFCe, permitindo que usuários inutilizem faixas de números não utilizados junto à SEFAZ.

### Componentes Desenvolvidos

#### 1. Backend - Modelo de Dados
**Arquivo:** `database/models.py` (linha 586)  
**Modelo:** `NFeInutilizacao`  
**Campos:** 18 campos incluindo cliente_id, modelo, serie, numero_inicial, numero_final, ano, justificativa, status, protocolo, xml_pedido, xml_resposta, etc.

#### 2. Migração SQL
**Arquivo:** `migrations/005_create_nfe_inutilizacoes_table.sql`  
**Status:** ✅ Executado no RDS  
**Estrutura:** Tabela com 18 colunas, 7 índices, constraint de status

#### 3. Serviço SEFAZ
**Arquivo:** `services/sefaz_service.py` (601 linhas)  
**Método Principal:** `inutilizar_numeracao()`  
**Funcionalidades:**
- Geração de XML de inutilização
- Assinatura digital com certificado A3
- Envio para SEFAZ via SOAP
- Processamento de respostas
- Tratamento de erros

#### 4. Serviço de Assinatura XML
**Arquivo:** `services/xml_signature_service.py` (184 linhas)  
**Método:** `assinar_xml()`  
**Tecnologia:** PyNFe (AssinaturaA1)

#### 5. Rotas da Aplicação
**Arquivo:** `routes/nfe_routes.py` (5 rotas implementadas)  
- `/inutilizar/form` (GET) - Formulário de inutilização
- `/inutilizar` (POST) - Processar inutilização
- `/inutilizacoes` (GET) - Listar inutilizações
- `/inutilizacao/<id>/detalhes` (GET) - Detalhes JSON
- `/inutilizacao/<id>/xml/<tipo>` (GET) - Download XML

#### 6. Templates Frontend
**Arquivo:** `templates/admin/nfes/inutilizar.html` (376 linhas)  
**Funcionalidades:** Formulário com validação, AJAX, modal de confirmação

**Arquivo:** `templates/admin/nfes/listar_inutilizacoes.html` (21KB)  
**Funcionalidades:** Listagem, filtros, estatísticas, modal de detalhes, download de XML

## Problemas Encontrados e Soluções

### Deploy e Correções em Sequência

#### 1. **Import Error** (Commit: fix imports)
- **Problema:** `from models.user import UserModel` failed
- **Solução:** Changed to `from database.models import UserModel, UserClient`

#### 2. **Decorator Error** (Commit: fix decorators)
- **Problema:** `editor_or_higher_required` doesn't exist
- **Solução:** Changed to `@editor_or_admin_required()`

#### 3. **Database Session Error** (Commit: fix session handling)
- **Problema:** `get_db_session()` function doesn't exist
- **Solução:** Changed to `next(get_db())` (5 locations)

#### 4. **Column Mapping Error** (Commit: fix column mapping)
- **Problema:** `_is_active` column mapping incorrect
- **Solução:** Removed mapping, used `_is_active = Column(Boolean)`

#### 5. **Access Control Error** (Commit: fix access control)
- **Problema:** Direct access to `current_user.user_clients`
- **Solução:** Refactored to use `get_accessible_client_ids(db)`

#### 6. **Field Name Errors** (Commit: fix field names)
- **Problema:** `cliente.cnpj_cpf` and `cliente.ambiente_sefaz` don't exist
- **Solução:** Changed to `cliente.cnpj` and `cliente.ambiente`

#### 7. **User ID Missing** (Commit: fix user id)
- **Problema:** `user_id` variable not defined
- **Solução:** Added `user_id = current_user.id`

#### 8. **Status Constraint Error** (Commit: fix status constraint)
- **Problema:** Status 'ERRO_HTTP' violates check constraint
- **Solução:** Added status normalization before DB save

#### 9. **XML Signature Missing** (Commit: implement xml signature)
- **Problema:** XML not signed, HTTP 400 from SEFAZ
- **Solução:** Added `_assinar_xml()` method using PyNFe

#### 10. **Certificate Format Error** (Commit: fix certificate format)
- **Problema:** Certificate format incompatible with PyNFe
- **Solução:** Changed to pass original cert_pfx_data instead of PEM conversion

#### 11. **SEFAZ Error 588** (Commit: fix XML formatting)
- **Problema:** "Não é permitida a presença de caracteres de edição"
- **Solução:** 
  - Generated XML as single-line format (no whitespace)
  - Added justificativa sanitization
  - Added XML cleanup after signing: `re.sub(r'>\s+<', '><', xml.strip())`

### Frontend Issues e Correções

#### 12. **Lazy Loading Error** (Commit: fix lazy loading listagem)
- **Problema:** Parent instance not bound to Session
- **Solução:** Added `joinedload(NFeInutilizacao.created_by_user)` 

#### 13. **URL Incorretas** (Commit: fix URLs)
- **Problema:** JavaScript using `/nfe/` instead of `/admin/nfe/`
- **Solução:** Updated fetch URLs and download URLs

#### 14. **Import Missing** (Commit: fix import NFeInutilizacao)
- **Problema:** `name 'NFeInutilizacao' is not defined`
- **Solução:** Added to global imports, removed local duplicates

#### 15. **User Clients Access** (Commit: fix user clients access)
- **Problema:** `'User' object has no attribute 'user_clients'`
- **Solução:** Replaced direct access with `get_accessible_client_ids()`

#### 16. **Modal Close Buttons** (Commit: fix modal buttons)
- **Problema:** Modal close buttons not working
- **Solução:** Added `onclick="fecharModal()"` and custom close function

#### 17. **Badge Colors** (Commit: fix badge colors)
- **Problema:** Status "Autorizada" with poor contrast
- **Solução:** Applied inline styles: `style="background-color: #28a745; color: white;"`

## Status Final

### Infrastructure
- **Servidor:** AWS EC2 (100.26.12.107) - Elastic IP permanente
- **Banco:** RDS PostgreSQL (nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com)
- **Serviço:** api-nfe-principal (systemd, 4 workers, ~256MB memória)
- **SEFAZ:** Homologação SP integrado via SOAP

### Funcionalidades Validadas
✅ Formulário de inutilização com validações  
✅ Processamento SEFAZ com certificado A3  
✅ Assinatura digital XML (PyNFe)  
✅ Listagem com filtros e estatísticas  
✅ Modal de detalhes funcionando  
✅ Download de XMLs (pedido/resposta)  
✅ Controle de acesso por cliente  
✅ Status visuais com cores adequadas  

### Últimos Commits
```
271ef8f - fix: aplicar estilos inline nos badges de status para garantir fundo verde visível
037b9e7 - fix: aplicar cores customizadas com fundo verde forte nos badges de status
0b3e30b - fix: corrigir fechamento do modal de detalhes da inutilização
661469b - fix: adicionar eager loading na rota de detalhes da inutilização
c4e707b - fix: corrigir URLs das requisições AJAX no template de listagem de inutilizações
bee64d7 - fix: substituir acesso a user_clients por get_accessible_client_ids nas rotas de inutilização
37988a3 - fix: adicionar NFeInutilizacao aos imports globais e remover imports locais duplicados
50f7404 - fix: adicionar eager loading para created_by_user na listagem de inutilizações
be85d65 - fix: remover espaços e caracteres inválidos do XML de inutilização (erro 588)
```

## Links de Acesso
- **Formulário:** http://100.26.12.107:8080/admin/nfe/inutilizar/form?cliente_id=29
- **Listagem:** http://100.26.12.107:8080/admin/nfe/inutilizacoes?cliente_id=29

## Próximos Passos
1. Testes em produção com certificados reais
2. Documentação para usuários finais  
3. Monitoramento de logs: `/home/ubuntu/api_nfe/logs/error.log`
4. Possível expansão para outros estados (atualmente SP)

## Lições Aprendidas
- SEFAZ requer XML perfeitamente formatado (sem espaços extras)
- PyNFe AssinaturaA1 precisa do arquivo .pfx original, não PEM
- Flask Blueprint url_prefix deve ser incluído em todas as URLs do frontend
- Constraints de banco devem ser rigorosamente seguidas
- Eager loading é essencial para relacionamentos acessados após fechamento da sessão
- Estilos inline garantem funcionamento quando CSS externo falha