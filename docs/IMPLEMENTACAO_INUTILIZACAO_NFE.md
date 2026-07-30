# Funcionalidade: Inutilização de Numeração de NFe/NFCe

## 📋 Visão Geral

Implementação completa da funcionalidade de inutilização de numeração fiscal conforme requisitos da SEFAZ. Permite cancelar faixas de números não utilizados, mantendo conformidade com a legislação.

## 🎯 Objetivo

Quando há quebras na sequência numérica de NFes/NFCes (erros de emissão, problemas técnicos, etc.), é necessário inutilizar os números não utilizados para manter a continuidade da numeração fiscal.

## 📊 Status da Implementação

### ✅ CONCLUÍDO

#### 1. Banco de Dados
- **Tabela**: `nfe_inutilizacoes` criada com 18 campos
- **Índices**: 6 índices para otimização de consultas
- **Constraints**: Validações de modelo, série, números e justificativa
- **Auditoria**: Campos de data_criacao, data_inutilizacao e created_by_user_id

**Estrutura:**
```sql
- inutilizacao_id (BIGSERIAL PRIMARY KEY)
- cliente_id (FK → clientes)
- modelo (VARCHAR: '55' ou '65')
- serie (INTEGER 0-999)
- numero_inicial, numero_final (INTEGER)
- ano (VARCHAR 2 dígitos)
- justificativa (TEXT min 15 chars)
- status (VARCHAR DEFAULT 'PROCESSANDO')
- protocolo, chave_inutilizacao (VARCHAR)
- codigo_status (VARCHAR)
- mensagem_sefaz (TEXT)
- xml_pedido, xml_resposta (TEXT)
- data_criacao (TIMESTAMP with BRT timezone)
- data_inutilizacao (TIMESTAMP)
- created_by_user_id (FK → users)
```

**Migration**: `migrations/005_create_nfe_inutilizacoes_table.sql`
- Executada com sucesso em 12/02/2026 15:30 BRT
- Verificação pós-migração: OK

#### 2. Modelo SQLAlchemy
**Arquivo**: `database/models.py`

```python
class NFeInutilizacao(Base):
    __tablename__ = 'nfe_inutilizacoes'
    
    # Campos principais + relacionamentos
    cliente = relationship("Cliente")
    created_by_user = relationship("UserModel")
```

#### 3. SEFAZ Service
**Arquivo**: `services/sefaz_service.py`

**Método**: `inutilizar_numeracao()`
- Gera XML conforme leiaute SEFAZ
- Estrutura: `<inutNFe><infInut Id="IDxxxxxxxxx">...</infInut></inutNFe>`
- Assina digitalmente com certificado A3
- Envia via SOAP para endpoints:
  - Homologação: `https://homologacao.nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx`
  - Produção: `https://nfe.fazenda.sp.gov.br/ws/nfeinutilizacao4.asmx`
- Processa resposta: código 102 = autorização bem sucedida

**Campos do XML:**
```xml
<infInut Id="ID35260257308098000166550010000000041000000009">
    <tpAmb>1</tpAmb>        <!-- Ambiente -->
    <xServ>INUTILIZAR</xServ>
    <cUF>35</cUF>           <!-- SP -->
    <ano>26</ano>
    <CNPJ>57308098000166</CNPJ>
    <mod>55</mod>           <!-- NFe ou NFCe -->
    <serie>1</serie>
    <nNFIni>4</nNFIni>      <!-- Número inicial -->
    <nNFFin>5</nNFFin>      <!-- Número final -->
    <xJust>Erro no sistema...</xJust>
</infInut>
```

#### 4. Routes (Backend)
**Arquivo**: `routes/nfe_routes.py`

| Rota | Método | Decorator | Descrição |
|------|--------|-----------|-----------|
| `/nfe/inutilizar/form` | GET | `viewer_or_higher_required` | Exibe formulário com sugestões de séries |
| `/nfe/inutilizar` | POST | `editor_or_higher_required` | Processa inutilização no SEFAZ |
| `/nfe/inutilizacoes` | GET | `viewer_or_higher_required` | Lista histórico com filtros e stats |
| `/nfe/inutilizacao/<id>/detalhes` | GET | `viewer_or_higher_required` | Retorna JSON com detalhes completos |
| `/nfe/inutilizacao/<id>/xml/<tipo>` | GET | `viewer_or_higher_required` | Download XML (pedido/resposta) |

**Validações no POST:**
- Todos campos obrigatórios presentes
- Justificativa mínimo 15 caracteres
- numero_final >= numero_inicial
- Modelo válido (55 ou 65)
- Série entre 0-999
- Ano com 2 dígitos

**Fluxo de Processamento:**
1. Validar dados recebidos
2. Extrair certificado para arquivos temporários
3. Chamar `sefaz.inutilizar_numeracao()`
4. Salvar registro no banco (PROCESSANDO → AUTORIZADA/REJEITADA)
5. Armazenar XMLs de pedido e resposta
6. Retornar JSON com resultado

#### 5. Templates (Frontend)

##### A) Formulário de Inutilização
**Arquivo**: `templates/admin/nfes/inutilizar.html`

**Recursos:**
- Seleção de modelo (NFe 55 / NFCe 65)
- Campos: série, números inicial/final, ano, justificativa
- **Sugestão inteligente**: Exibe últimas numerações por série
- Validação client-side:
  - Justificativa mínimo 15 caracteres (contador em tempo real)
  - Número final >= número inicial
  - Sincronização automática de número final com inicial
  - Ano preenchido automaticamente
- Checkbox de confirmação (ação irreversível)
- AJAX submit para não recarregar página
- Modais:
  - **Processando**: Spinner enquanto aguarda SEFAZ
  - **Resultado**: Sucesso (verde) ou Erro (vermelho)
- Auto-reload após 3 segundos em caso de sucesso

**Layout:**
```
┌─────────────────────────────────────────┐
│  Alert: Ação Irreversível               │
├─────────────────────────────────────────┤
│  Últimas Numerações por Série (tabela)  │
├─────────────────────────────────────────┤
│  [Modelo] [Série] [Nº Ini] [Nº Fim]    │
│  [Ano]    [Justificativa (textarea)]    │
│  [✓] Confirmo que desejo inutilizar     │
│  [Cancelar] [Inutilizar Numeração]      │
└─────────────────────────────────────────┘
```

##### B) Lista de Inutilizações
**Arquivo**: `templates/admin/nfes/listar_inutilizacoes.html`

**Recursos:**
- **Filtros**: Modelo, Série, Status, Ano
- **Cards de Estatísticas**:
  - ✅ Autorizadas (verde)
  - ❌ Rejeitadas (vermelho)
  - ⏳ Processando (amarelo)
  - 📊 Total
- **Tabela Completa**:
  - Colunas: ID, Data/Hora, Modelo, Série, Números, Ano, Justificativa, Status, Protocolo, Usuário, Ações
  - Ordenação: data_criacao DESC
  - Tooltip na justificativa (truncada com "...")
  - Badge colorido para status
- **Ações por Item**:
  - 👁️ Ver Detalhes (modal com dados completos)
  - 📥 Baixar XML (pedido e resposta)
- **Modal de Detalhes**:
  - Dados da Inutilização (ID, modelo, série, números, ano, data)
  - Resposta SEFAZ (status, código, protocolo, chave, mensagem)
  - Justificativa completa
  - Auditoria (usuário criador)

**Filtros Client-Side:**
- JavaScript filtra tabela sem recarregar
- Atualiza contador total dinamicamente
- Botão "Limpar" reseta todos filtros

##### C) Integração com Lista de NFes
**Arquivo**: `templates/admin/nfes/list.html`

**Botões Adicionados**:
```html
<a href="/nfe/inutilizar/form?cliente_id=X" class="btn btn-warning">
    <i class="fas fa-ban"></i> Inutilizar Numeração
</a>
<a href="/nfe/inutilizacoes?cliente_id=X" class="btn btn-outline-warning">
    <i class="fas fa-list-alt"></i> Ver Inutilizações
</a>
```

**Localização**: Toolbar superior, entre "Nova NFe" e "Voltar"
**Visibilidade**: Apenas quando `cliente_id` está presente

## 🔐 Segurança e Permissões

| Ação | Permissão Necessária | Decorator |
|------|----------------------|-----------|
| Ver formulário | Viewer ou superior | `viewer_or_higher_required` |
| Processar inutilização | Editor ou superior | `editor_or_higher_required` |
| Ver lista/detalhes | Viewer ou superior | `viewer_or_higher_required` |
| Baixar XML | Viewer ou superior | `viewer_or_higher_required` |

**Verificações Adicionais:**
- Super admins: acesso total
- Usuários comuns: apenas clientes associados via `user_clients`

## 📡 Integração SEFAZ

### Requisitos da SEFAZ
1. ✅ Justificativa mínima de 15 caracteres
2. ✅ Assinatura digital do XML com certificado A3
3. ✅ Envelope SOAP com header `nfeCabecMsg`
4. ✅ Identificador único: `Id="ID" + cUF + ano + CNPJ + mod + serie + nNFIni + nNFFin`
5. ✅ Código de retorno 102 = autorizado

### Códigos de Status
- **102**: Inutilização de número homologado
- **256**: Rejeição (já consumido, já inutilizado, etc.)
- Outros: Erros diversos (certificado, schema, etc.)

### Ambientes
- **Homologação**: `tpAmb=2`
- **Produção**: `tpAmb=1`

## 🧪 Testes Necessários

### Teste 1: Inutilizar Número Único
1. Acessar `/nfe/inutilizar/form?cliente_id=29`
2. Selecionar: Modelo 55, Série 1, Números 4-4, Ano 26
3. Justificativa: "Teste de inutilização número único"
4. Confirmar e enviar
5. ✅ Esperar: Código 102, Status AUTORIZADA, Protocolo preenchido

### Teste 2: Inutilizar Faixa
1. Números 10-15 (6 números)
2. Justificativa: "Erro no sistema causou quebra na sequência numérica da emissão"
3. ✅ Esperar: Inutilização em lote autorizada

### Teste 3: Validações
- ❌ Justificativa com 14 caracteres → Erro
- ❌ Número final < número inicial → Erro
- ❌ Série 1000 → Erro (máximo 999)
- ❌ Modelo 77 → Erro (apenas 55 ou 65)

### Teste 4: Listagem
1. Filtrar por Status: AUTORIZADA
2. Filtrar por Série: 1
3. Ver detalhes de uma inutilização
4. Baixar XML de resposta
5. ✅ Verificar: Filtros funcionam, modal abre, XML baixa

### Teste 5: Permissões
- Usuário viewer: pode ver mas não processar
- Usuário editor: pode processar
- Usuário sem associação ao cliente: acesso negado

## 📁 Arquivos Criados/Modificados

### Criados ✨
```
migrations/
  005_create_nfe_inutilizacoes_table.sql    (88 linhas)
  run_migration_inutilizacao.py             (119 linhas)

templates/admin/nfes/
  inutilizar.html                           (350 linhas)
  listar_inutilizacoes.html                 (380 linhas)
```

### Modificados ✏️
```
database/
  models.py                                 (+45 linhas)

services/
  sefaz_service.py                          (+220 linhas)

routes/
  nfe_routes.py                             (+317 linhas backend + 152 linhas rotas extras)

templates/admin/nfes/
  list.html                                 (+10 linhas)
```

## 📊 Estatísticas da Implementação

| Métrica | Valor |
|---------|-------|
| **Linhas de Código Total** | ~1.130 |
| **Arquivos Criados** | 4 |
| **Arquivos Modificados** | 5 |
| **Rotas Adicionadas** | 5 |
| **Templates HTML** | 2 completos |
| **Tempo de Dev** | ~2 horas |
| **Commits** | 3 |

## 🚀 Deploy

### 1. Migração do Banco (✅ EXECUTADA)
```bash
python3 migrations/run_migration_inutilizacao.py
```

### 2. Deploy de Código (⏳ PENDENTE)
```bash
# Copiar arquivos para servidor
scp database/models.py ubuntu@100.26.12.107:/home/ubuntu/api_nfe/database/
scp services/sefaz_service.py ubuntu@100.26.12.107:/home/ubuntu/api_nfe/services/
scp routes/nfe_routes.py ubuntu@100.26.12.107:/home/ubuntu/api_nfe/routes/
scp -r templates/admin/nfes/ ubuntu@100.26.12.107:/home/ubuntu/api_nfe/templates/admin/nfes/

# Reiniciar serviço
ssh ubuntu@100.26.12.107 "sudo systemctl restart api-nfe-principal"
```

### 3. Verificação Pós-Deploy
```bash
# Verificar logs
ssh ubuntu@100.26.12.107 "sudo journalctl -u api-nfe-principal -f"

# Testar endpoints
curl http://100.26.12.107:8090/nfe/inutilizar/form?cliente_id=29
```

## 📝 Próximos Passos

1. ⏳ Deploy em produção (AWS EC2)
2. ⏳ Testes end-to-end com SEFAZ homologação
3. ⏳ Testes com certificado real do cliente 29
4. ⏳ Documentação no manual do usuário
5. ⏳ Treinamento para usuários sobre quando usar inutilização

## 🐛 Troubleshooting

### Erro: "Justificativa muito curta"
- Mínimo 15 caracteres conforme SEFAZ
- Validação client-side previne envio

### Erro: "Número já utilizado"
- SEFAZ retorna código 256
- Verificar se número não foi emitido
- Consultar lista de NFes para confirmar

### Erro: "Certificado inválido"
- Verificar validade do certificado A3
- Confirmar senha correta no banco
- Testar extração de certificado

### XML não retornado
- Verificar se `xml_resposta` está preenchido no banco
- Inutilizações rejeitadas podem não ter XML completo

## 📚 Referências

- [Manual de Integração SEFAZ SP](https://www.fazenda.sp.gov.br/nfe/)
- [Leiaute NFe 4.0](http://www.nfe.fazenda.gov.br/portal/listaConteudo.aspx?tipoConteudo=/fhKKVy+Y5I=)
- [Códigos de Status SEFAZ](http://www.nfe.fazenda.gov.br/portal/exibirArquivo.aspx?conteudo=mz/pWL4hnE8=)

## ✅ Checklist Final

- [x] Tabela criada no banco
- [x] Modelo SQLAlchemy implementado
- [x] Método SEFAZ implementado
- [x] 5 rotas backend criadas
- [x] Formulário HTML com validações
- [x] Lista HTML com filtros e stats
- [x] Botões integrados na lista de NFes
- [x] Migração executada com sucesso
- [x] Código commitado no git (3 commits)
- [ ] Deploy em produção
- [ ] Testes com SEFAZ homologação
- [ ] Testes com certificado real
- [ ] Documentação do usuário

---

**Data de Conclusão**: 12 de Fevereiro de 2026  
**Commits**:
- `5617825`: Correção de bugs (status NFe)
- `1243939`: Inutilização parte 1 (backend)
- `b635024`: Inutilização parte 2 (frontend)

**Desenvolvido por**: GitHub Copilot (Claude Sonnet 4.5)  
**Cliente**: SIRIUS MATERIAIS PARA CONSTRUCAO LTDA (Cliente ID 29)
