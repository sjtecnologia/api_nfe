# 🏗️ IMPLEMENTAÇÃO COMPLETA - LUCRO REAL/PRESUMIDO (CRT=3)

## 📋 RESUMO DA IMPLEMENTAÇÃO

Sistema EmiteMax agora suporta **dois regimes tributários** baseado no cadastro do cliente:

- **CRT=1**: Simples Nacional → Sistema funciona **exatamente como está** (sem mudanças)
- **CRT=3**: Lucro Real / Lucro Presumido → Campos IBS/CBS aparecem **dinamicamente**

---

## ✅ O QUE FOI IMPLEMENTADO (Backend)

### 1. **Banco de Dados** ✅

```sql
-- Campo CRT adicionado em regimes_tributarios
ALTER TABLE regimes_tributarios ADD COLUMN crt INTEGER DEFAULT 1;
UPDATE regimes_tributarios SET crt = 1 WHERE regime_tributario_id = 1; -- Simples
UPDATE regimes_tributarios SET crt = 3 WHERE regime_tributario_id IN (2, 3); -- Lucro Real/Presumido

-- Nova tabela: classificacoes_ibs_cbs
CREATE TABLE classificacoes_ibs_cbs (
    classificacao_id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,
    descricao TEXT NOT NULL,
    aliquota_ibs_uf NUMERIC(5,2) DEFAULT 0.10,
    aliquota_ibs_mun NUMERIC(5,2) DEFAULT 0.00,
    aliquota_cbs NUMERIC(5,2) DEFAULT 0.90,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dados iniciais
INSERT INTO classificacoes_ibs_cbs (codigo, descricao) VALUES
    ('000001', 'Medicamentos e produtos de higiene pessoal'),
    ('000002', 'Produtos alimentícios básicos'),
    ('000003', 'Outros produtos');

-- Nova tabela: autorizacoes_xml_nfe
CREATE TABLE autorizacoes_xml_nfe (
    autorizacao_id SERIAL PRIMARY KEY,
    nfe_emitida_id BIGINT NOT NULL,
    cliente_id BIGINT NOT NULL,
    cpf_cnpj VARCHAR(14) NOT NULL,
    tipo VARCHAR(3) CHECK (tipo IN ('CPF', 'CNPJ')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nfe_emitida_id, cliente_id) 
        REFERENCES nfe_emitidas(nfe_emitida_id, cliente_id) ON DELETE CASCADE
);

-- Novas colunas em nfe_emitidas
ALTER TABLE nfe_emitidas ADD COLUMN total_ibs NUMERIC(15,2) DEFAULT 0;
ALTER TABLE nfe_emitidas ADD COLUMN total_cbs NUMERIC(15,2) DEFAULT 0;
ALTER TABLE nfe_emitidas ADD COLUMN total_ibs_bc NUMERIC(15,2) DEFAULT 0;
ALTER TABLE nfe_emitidas ADD COLUMN valor_icms_st_retido NUMERIC(15,2) DEFAULT 0;

-- Nova coluna em produtos (opcional para pré-seleção)
ALTER TABLE produtos ADD COLUMN classificacao_ibs_cbs_id INTEGER 
    REFERENCES classificacoes_ibs_cbs(classificacao_id);
```

### 2. **Modelos (database/models.py)** ✅

```python
class RegimeTributario(Base):
    # ... campos existentes ...
    crt = Column(Integer, default=1, nullable=False)  # NOVO

class ClassificacaoIBSCBS(Base):
    """NOVO: Classificações IBS/CBS Reforma Tributária"""
    __tablename__ = 'classificacoes_ibs_cbs'
    classificacao_id = Column(Integer, primary_key=True)
    codigo = Column(String(10), unique=True, nullable=False)
    descricao = Column(Text, nullable=False)
    aliquota_ibs_uf = Column(Numeric(5, 2), default=0.10)
    aliquota_ibs_mun = Column(Numeric(5, 2), default=0.00)
    aliquota_cbs = Column(Numeric(5, 2), default=0.90)
    ativo = Column(Boolean, default=True)
    produtos = relationship('Produto', back_populates='classificacao_ibs_cbs')

class AutorizacaoXMLNFe(Base):
    """NOVO: CPFs/CNPJs autorizados a baixar XML"""
    __tablename__ = 'autorizacoes_xml_nfe'
    autorizacao_id = Column(Integer, primary_key=True)
    nfe_emitida_id = Column(BigInteger, nullable=False)
    cliente_id = Column(BigInteger, nullable=False)
    cpf_cnpj = Column(String(14), nullable=False)
    tipo = Column(String(3), nullable=False)

class NFeEmitidas(Base):
    # ... campos existentes ...
    # NOVOS campos IBS/CBS:
    total_ibs = Column(Numeric(15, 2), default=0)
    total_cbs = Column(Numeric(15, 2), default=0)
    total_ibs_bc = Column(Numeric(15, 2), default=0)
    valor_icms_st_retido = Column(Numeric(15, 2), default=0)

class Produto(Base):
    # ... campos existentes ...
    classificacao_ibs_cbs_id = Column(Integer, ForeignKey('classificacoes_ibs_cbs.classificacao_id'))
    classificacao_ibs_cbs = relationship('ClassificacaoIBSCBS', back_populates='produtos')
```

### 3. **Serviço IBS/CBS (services/ibs_cbs_service.py)** ✅

```python
# Funções disponíveis:
calcular_ibs_cbs(valor_produto, classificacao, db)  # Calcula IBS/CBS
gerar_xml_ibscbs(ibs_cbs_data)  # Gera XML <IBSCBS>
gerar_xml_icms60(produto_data)  # Gera XML <ICMS60>
gerar_xml_totais_ibscbs(totais_ibs, totais_cbs)  # Gera <IBSCBSTot>
gerar_xml_autorizacoes(autorizacoes)  # Gera <autXML>
gerar_xml_pisnt_cst04()  # Gera <PISNT> CST 04
gerar_xml_cofinsnt_cst04()  # Gera <COFINSNT> CST 04
totalizar_ibs_cbs(itens_ibs_cbs)  # Totaliza todos os itens
validar_dados_crt3(dados_nfe)  # Valida dados obrigatórios CRT=3
```

### 4. **Rotas API (routes/admin_routes.py)** ✅

```python
# Nova rota: Listar classificações IBS/CBS
GET /admin/api/classificacoes-ibs-cbs
Response: {
    "success": true,
    "data": [
        {
            "id": 1,
            "codigo": "000001",
            "descricao": "Medicamentos e produtos de higiene pessoal",
            "aliquota_ibs_uf": 0.10,
            "aliquota_ibs_mun": 0.00,
            "aliquota_cbs": 0.90
        }
    ]
}

# Nova rota: Verificar regime tributário do cliente
GET /admin/api/regime-tributario/<cliente_id>
Response: {
    "success": true,
    "crt": 3,
    "regime_nome": "Lucro Real",
    "requer_ibs_cbs": true
}
```

---

## 🎨 O QUE PRECISA SER IMPLEMENTADO (Frontend)

### 1. **Formulário de Emissão NFe** 🔴 PENDENTE

**Arquivo**: `templates/admin/nfes/emitir.html`

**Lógica**:
1. Ao carregar a página, fazer requisição: `GET /admin/api/regime-tributario/<cliente_id>`
2. Se `requer_ibs_cbs == true`, mostrar campos IBS/CBS
3. Se `requer_ibs_cbs == false`, **não mostrar** (cliente Simples Nacional)

**JavaScript a adicionar**:

```javascript
// Ao carregar a página ou trocar de cliente
async function verificarRegimeCliente(clienteId) {
    const response = await fetch(`/admin/api/regime-tributario/${clienteId}`);
    const data = await response.json();
    
    const requerIBS = data.requer_ibs_cbs;
    
    // Mostrar/ocultar seções
    document.getElementById('secao-ibs-cbs').style.display = requerIBS ? 'block' : 'none';
    document.getElementById('secao-icms60').style.display = requerIBS ? 'block' : 'none';
    document.getElementById('secao-autorizacoes').style.display = requerIBS ? 'block' : 'none';
    
    // Se mostrar, carregar classificações
    if (requerIBS) {
        carregarClassificacoesIBS();
    }
}

async function carregarClassificacoesIBS() {
    const response = await fetch('/admin/api/classificacoes-ibs-cbs');
    const data = await response.json();
    
    const select = document.getElementById('select-classificacao-ibs');
    select.innerHTML = '<option value="">Selecione...</option>';
    
    data.data.forEach(c => {
        const option = document.createElement('option');
        option.value = c.id;
        option.textContent = `${c.codigo} - ${c.descricao}`;
        option.dataset.aliquotaIbsUf = c.aliquota_ibs_uf;
        option.dataset.aliquotaIbsMun = c.aliquota_ibs_mun;
        option.dataset.aliquotaCbs = c.aliquota_cbs;
        select.appendChild(option);
    });
}
```

**HTML a adicionar** (após seção de produtos):

```html
<!-- SEÇÃO IBS/CBS - Visível apenas para CRT=3 -->
<div id="secao-ibs-cbs" style="display: none;">
    <div class="card mt-3">
        <div class="card-header bg-info text-white">
            <h5><i class="fas fa-balance-scale"></i> IBS/CBS - Reforma Tributária</h5>
        </div>
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <label>Classificação Tributária IBS/CBS</label>
                    <select id="select-classificacao-ibs" name="classificacao_ibs_cbs_id" class="form-control" required>
                        <option value="">Carregando...</option>
                    </select>
                    <small class="text-muted">Obrigatório para Lucro Real/Presumido</small>
                </div>
                <div class="col-md-2">
                    <label>% IBS UF</label>
                    <input type="number" name="aliquota_ibs_uf" step="0.01" value="0.10" class="form-control" readonly>
                </div>
                <div class="col-md-2">
                    <label>% IBS Municipal</label>
                    <input type="number" name="aliquota_ibs_mun" step="0.01" value="0.00" class="form-control" readonly>
                </div>
                <div class="col-md-2">
                    <label>% CBS</label>
                    <input type="number" name="aliquota_cbs" step="0.01" value="0.90" class="form-control" readonly>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- SEÇÃO ICMS60 - Visível apenas para CRT=3 -->
<div id="secao-icms60" style="display: none;">
    <div class="card mt-3">
        <div class="card-header bg-warning text-dark">
            <h5><i class="fas fa-file-invoice-dollar"></i> ICMS Substituição Tributária</h5>
        </div>
        <div class="card-body">
            <div class="alert alert-info">
                <i class="fas fa-info-circle"></i> 
                Preencha apenas se houver ICMS ST retido anteriormente
            </div>
            <div class="row">
                <div class="col-md-3">
                    <label>BC ICMS ST Retido</label>
                    <input type="number" name="vBCSTRet" step="0.01" class="form-control" placeholder="0,00">
                </div>
                <div class="col-md-3">
                    <label>% Substituição</label>
                    <input type="number" name="pST" step="0.01" class="form-control" placeholder="0,00">
                </div>
                <div class="col-md-3">
                    <label>ICMS Substituto</label>
                    <input type="number" name="vICMSSubstituto" step="0.01" class="form-control" placeholder="0,00">
                </div>
                <div class="col-md-3">
                    <label>ICMS ST Retido</label>
                    <input type="number" name="vICMSSTRet" step="0.01" class="form-control" placeholder="0,00">
                </div>
            </div>
        </div>
    </div>
</div>

<!-- SEÇÃO AUTORIZAÇÕES XML - Visível apenas para CRT=3 -->
<div id="secao-autorizacoes" style="display: none;">
    <div class="card mt-3">
        <div class="card-header bg-secondary text-white">
            <h5><i class="fas fa-users"></i> Autorizações para Download do XML</h5>
        </div>
        <div class="card-body">
            <p class="text-muted">CPFs/CNPJs autorizados a baixar o XML da NFe (opcional)</p>
            <div id="autorizacoes-container">
                <div class="input-group mb-2">
                    <input type="text" name="autXML[]" class="form-control" placeholder="CPF ou CNPJ (apenas números)">
                    <button type="button" class="btn btn-sm btn-danger" onclick="this.parentElement.remove()">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <button type="button" class="btn btn-sm btn-secondary" onclick="adicionarAutorizacao()">
                <i class="fas fa-plus"></i> Adicionar Autorização
            </button>
        </div>
    </div>
</div>

<script>
function adicionarAutorizacao() {
    const container = document.getElementById('autorizacoes-container');
    const div = document.createElement('div');
    div.className = 'input-group mb-2';
    div.innerHTML = `
        <input type="text" name="autXML[]" class="form-control" placeholder="CPF ou CNPJ (apenas números)">
        <button type="button" class="btn btn-sm btn-danger" onclick="this.parentElement.remove()">
            <i class="fas fa-trash"></i>
        </button>
    `;
    container.appendChild(div);
}

// Auto-preencher alíquotas ao selecionar classificação
document.getElementById('select-classificacao-ibs').addEventListener('change', function() {
    const option = this.options[this.selectedIndex];
    if (option.value) {
        document.querySelector('input[name="aliquota_ibs_uf"]').value = option.dataset.aliquotaIbsUf;
        document.querySelector('input[name="aliquota_ibs_mun"]').value = option.dataset.aliquotaIbsMun;
        document.querySelector('input[name="aliquota_cbs"]').value = option.dataset.aliquotaCbs;
    }
});
</script>
```

### 2. **Cadastro de Produtos** 🔴 PENDENTE

**Arquivo**: `templates/admin/produtos/form.html` (ou similar)

**Campo a adicionar**:

```html
<!-- Adicionar após campos de tributação existentes -->
<div class="form-group" id="campo-classificacao-ibs" style="display: none;">
    <label>Classificação IBS/CBS (Reforma Tributária)</label>
    <select name="classificacao_ibs_cbs_id" class="form-control">
        <option value="">Selecione...</option>
        <!-- Carregar via JS de /admin/api/classificacoes-ibs-cbs -->
    </select>
    <small class="text-muted">
        Pré-selecionado para clientes com Lucro Real/Presumido
    </small>
</div>

<script>
// Carregar classificações ao carregar página
async function carregarClassificacoesProduto() {
    const response = await fetch('/admin/api/classificacoes-ibs-cbs');
    const data = await response.json();
    
    const select = document.querySelector('select[name="classificacao_ibs_cbs_id"]');
    data.data.forEach(c => {
        const option = document.createElement('option');
        option.value = c.id;
        option.textContent = `${c.codigo} - ${c.descricao}`;
        select.appendChild(option);
    });
}

carregarClassificacoesProduto();
</script>
```

### 3. **Dashboard Analytics** 🔴 PENDENTE

**Arquivo**: `templates/admin/dashboard.html`

**Adicionar KPIs IBS/CBS**:

```html
<!-- Adicionar após KPIs existentes -->
<div class="col-md-3" id="kpi-ibs" style="display: none;">
    <div class="card bg-gradient-info text-white">
        <div class="card-body">
            <h6 class="text-uppercase">Total IBS Arrecadado</h6>
            <h3 id="valor-total-ibs">R$ 0,00</h3>
            <small>Imposto sobre Bens e Serviços (UF + Municipal)</small>
        </div>
    </div>
</div>

<div class="col-md-3" id="kpi-cbs" style="display: none;">
    <div class="card bg-gradient-warning text-white">
        <div class="card-body">
            <h6 class="text-uppercase">Total CBS Arrecadado</h6>
            <h3 id="valor-total-cbs">R$ 0,00</h3>
            <small>Contribuição sobre Bens e Serviços</small>
        </div>
    </div>
</div>
```

**Backend (routes/admin_routes.py)** - adicionar em `dashboard_analytics()`:

```python
# Após cálculo de KPIs existentes, adicionar:
if periodo_inicio and periodo_fim:
    where_and = "AND data_emissao BETWEEN :inicio AND :fim"
    params = {'inicio': periodo_inicio, 'fim': periodo_fim}
else:
    where_and = ""
    params = {}

# Total IBS arrecadado
kpis['total_ibs'] = db.execute(text(f"""
    SELECT COALESCE(SUM(total_ibs), 0) 
    FROM nfe_emitidas 
    WHERE status ILIKE '%autoriza%' {where_and}
"""), params).scalar() or 0

# Total CBS arrecadado
kpis['total_cbs'] = db.execute(text(f"""
    SELECT COALESCE(SUM(total_cbs), 0) 
    FROM nfe_emitidas 
    WHERE status ILIKE '%autoriza%' {where_and}
"""), params).scalar() or 0
```

### 4. **Visualização de NFe Emitida** 🔴 PENDENTE

**Arquivo**: `templates/admin/nfes/detalhes.html`

**Adicionar seção IBS/CBS** (após totais existentes):

```html
<!-- Mostrar apenas se nfe.total_ibs > 0 ou nfe.total_cbs > 0 -->
{% if nfe.total_ibs or nfe.total_cbs %}
<div class="card mt-3">
    <div class="card-header bg-info text-white">
        <h5><i class="fas fa-balance-scale"></i> IBS/CBS - Reforma Tributária</h5>
    </div>
    <div class="card-body">
        <table class="table table-bordered">
            <thead>
                <tr>
                    <th>Tributo</th>
                    <th>Base de Cálculo</th>
                    <th>Alíquota</th>
                    <th>Valor</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><strong>IBS (UF + Municipal)</strong></td>
                    <td>R$ {{ nfe.total_ibs_bc|format_currency }}</td>
                    <td>0,10%</td>
                    <td><strong>R$ {{ nfe.total_ibs|format_currency }}</strong></td>
                </tr>
                <tr>
                    <td><strong>CBS (Federal)</strong></td>
                    <td>R$ {{ nfe.total_ibs_bc|format_currency }}</td>
                    <td>0,90%</td>
                    <td><strong>R$ {{ nfe.total_cbs|format_currency }}</strong></td>
                </tr>
                <tr class="table-success">
                    <td colspan="3"><strong>Total IBS/CBS</strong></td>
                    <td><strong>R$ {{ (nfe.total_ibs + nfe.total_cbs)|format_currency }}</strong></td>
                </tr>
            </tbody>
        </table>
        
        {% if nfe.valor_icms_st_retido > 0 %}
        <div class="alert alert-warning mt-3">
            <strong>ICMS ST Retido:</strong> R$ {{ nfe.valor_icms_st_retido|format_currency }}
        </div>
        {% endif %}
    </div>
</div>
{% endif %}
```

---

## 🔄 FLUXO COMPLETO DE EMISSÃO

### Para Cliente **Simples Nacional (CRT=1)**:

1. Usuário seleciona cliente
2. Sistema verifica: `GET /admin/api/regime-tributario/<id>` → `requer_ibs_cbs: false`
3. Formulário **NÃO mostra** campos IBS/CBS
4. Emissão funciona **exatamente como antes**
5. XML gerado usa `<ICMSSN>` (CSOSN)

### Para Cliente **Lucro Real/Presumido (CRT=3)**:

1. Usuário seleciona cliente
2. Sistema verifica: `GET /admin/api/regime-tributario/<id>` → `requer_ibs_cbs: true`
3. Formulário **MOSTRA** seções:
   - Classificação IBS/CBS (obrigatória)
   - ICMS60 (opcional)
   - Autorizações XML (opcional)
4. Ao submeter:
   - Backend calcula IBS/CBS usando `services/ibs_cbs_service.py`
   - Gera XML com `<ICMS60>`, `<IBSCBS>`, `<IBSCBSTot>`
   - Salva `total_ibs`, `total_cbs` em `nfe_emitidas`
5. XML enviado para SEFAZ

---

## 🧪 TESTES

### 1. **Testar API**

```bash
# Verificar regime tributário
curl http://localhost:8080/admin/api/regime-tributario/1

# Listar classificações IBS/CBS
curl http://localhost:8080/admin/api/classificacoes-ibs-cbs
```

### 2. **Testar Cálculo IBS/CBS**

```python
from services.ibs_cbs_service import calcular_ibs_cbs
from decimal import Decimal

# Simular cálculo
valor_produto = Decimal('100.00')
classificacao_id = 1

# Deve retornar:
# vIBSUF = 0.10 (0.10% de 100)
# vCBS = 0.90 (0.90% de 100)
# vIBS = 0.10
```

### 3. **Testar Emissão**

1. Cadastrar cliente com **Lucro Presumido**
2. Verificar se campos IBS/CBS aparecem no formulário
3. Emitir NFe de teste
4. Verificar XML gerado contém:
   - `<IBSCBS>` com cálculos corretos
   - `<IBSCBSTot>` nos totais
   - Valores salvos em `nfe_emitidas`

---

## 📚 REFERÊNCIAS

- **XML Modelo**: `/Documentacao/modeloxmlcompleto/MODELO bsj.xml`
- **Serviço IBS/CBS**: `/services/ibs_cbs_service.py`
- **Modelos**: `/database/models.py` (classes ClassificacaoIBSCBS, AutorizacaoXMLNFe)
- **Rotas API**: `/routes/admin_routes.py` (linhas finais)

---

## ⚠️ IMPORTANTE

1. **NÃO ALTERAR** lógica existente do Simples Nacional
2. **SEMPRE** verificar `regime_tributario.crt` antes de mostrar campos IBS/CBS
3. **VALIDAR** classificação IBS/CBS obrigatória quando CRT=3
4. **TESTAR** em homologação antes de produção

---

## 🚀 PRÓXIMOS PASSOS

1. ✅ Backend completo (100%)
2. 🔴 Implementar frontend (formulários dinâmicos)
3. 🔴 Integrar com geração XML em `services/nfe_service.py`
4. 🔴 Testar emissão completa em homologação
5. 🔴 Deploy em produção

---

**Data da implementação**: 11/12/2025  
**Sistema**: EmiteMax v2.0  
**Desenvolvedor**: Renato / AI Assistant
