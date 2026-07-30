# 📊 Análise: Atualização NFS-e RTC - NT007 v1.03.00

**Data da Análise:** 9 de fevereiro de 2026  
**Fonte:** https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc  
**Versão Atual do Sistema:** Baseada em GISS Online v2.04  
**Versão Alvo:** AnexoVI-LeiautesRN_RTC_IBSCBS-V1.03.00 - NT007

---

## 📑 Sumário Executivo

Este documento apresenta uma análise completa da compatibilidade do sistema atual de NFS-e com as atualizações mais recentes da documentação técnica da Receita Federal sobre a Reforma Tributária do Consumo (RTC), especificamente a **Nota Técnica SE/CGNFS-e nº 007**.

### 🎯 Objetivos da Análise

1. ✅ **Verificar compatibilidade** com layout v1.03.00 (NT007)
2. ✅ **Comparar implementação** atual vs. novas especificações
3. ✅ **Identificar adaptações** necessárias para conformidade

---

## 📋 PARTE 1: VERIFICAÇÃO DE COMPATIBILIDADE COM NT007 v1.03.00

### 🔍 Status Atual da Implementação

#### ✅ **Campos da Reforma Tributária Implementados no BD** (15 campos)

| Campo | Status | Versão Implementada | NT007 Requer | Compatível |
|-------|--------|-------------------|--------------|------------|
| `codigo_nbs` | ✅ Implementado | VARCHAR(9) | NBS (9 dígitos) | ✅ SIM |
| `finalidade_nfse` | ✅ Implementado | VARCHAR(1) | 0-3 | ✅ SIM |
| `indicador_consumidor_final` | ✅ Implementado | VARCHAR(1) | 0-1 | ✅ SIM |
| `indicador_destinatario` | ✅ Implementado | VARCHAR(1) | 0-2 | ✅ SIM |
| `codigo_indicador_operacao` | ✅ Implementado | VARCHAR(6) | cIndOp (6 dígitos) | ✅ SIM |
| `cst_ibs_cbs` | ✅ Implementado | VARCHAR(3) | CST (3 dígitos) | ✅ SIM |
| `codigo_classificacao_tributaria` | ✅ Implementado | VARCHAR(6) | cClassTrib (6 dígitos) | ✅ SIM |
| `codigo_localidade_incidencia` | ✅ Implementado | VARCHAR(7) | Código IBGE | ✅ SIM |
| `percentual_redutor` | ✅ Implementado | DECIMAL(5,2) | 0-100% | ✅ SIM |
| `percentual_total_tributos_federais` | ✅ Implementado | DECIMAL(5,2) | pTotTribFed | ✅ SIM |
| `percentual_total_tributos_estaduais` | ✅ Implementado | DECIMAL(5,2) | pTotTribEst | ✅ SIM |
| `percentual_total_tributos_municipais` | ✅ Implementado | DECIMAL(5,2) | pTotTribMun | ✅ SIM |
| `regime_especial_tributacao` | ✅ Implementado | VARCHAR(1) | 1-6 | ✅ SIM |
| `optante_simples_nacional` | ✅ Implementado | BOOLEAN | true/false | ✅ SIM |
| `incentivador_cultural` | ✅ Implementado | BOOLEAN | true/false | ✅ SIM |

**Resultado:** ✅ **15/15 campos compatíveis com estrutura NT007**

---

### 📝 Documentação Oficial NT007

#### **Nota Técnica SE/CGNFS-e nº 007**
- **Anexo VI:** LeiautesRN_RTC_IBSCBS-V1.03.00
- **Anexo VII:** IndOp_IBSCBS_V1.01.00
- **Status:** Versão mais recente (consulta: 09/02/2026)
- **Escopo:** Adequações do layout da NFS-e e esclarecimentos sobre a plataforma

#### **Nota Técnica SE/CGNFS-e nº 006**
- **Escopo:** NFS-e Via (contexto específico de concessão de vias)
- **Impacto no Sistema:** ⚠️ Não aplicável (sistema focado em serviços gerais)

#### **Nota Técnica SE/CGNFS-e nº 004**
- **Versão:** AnexoVI-LeiautesRN_RTC_IBSCBS-V1.01.03 - NT004
- **Status:** Disponível em produção desde 5 de janeiro de 2026
- **Anexo VII:** IndOp_IBSCBS_V1.00.00
- **XSD Schemas:** Disponíveis para validação

---

### 🔄 Comparação de Versões

| Item | NT004 (v1.01.03) | NT007 (v1.03.00) | Mudança |
|------|------------------|------------------|---------|
| **Anexo VI (Layout)** | v1.01.03 | v1.03.00 | ⚠️ **ATUALIZADO** |
| **Anexo VII (IndOp)** | v1.00.00 | v1.01.00 | ⚠️ **ATUALIZADO** |
| **XSD Schemas** | Disponíveis | Requer verificação | ⚠️ **VERIFICAR** |
| **Ambiente Produção** | ✅ Disponível desde 05/01/2026 | 🔮 Data não divulgada | ⚠️ **AGUARDANDO** |
| **Ambiente Piloto** | ✅ Disponível | ✅ Disponível | ✅ OK |

---

### ⚠️ AnexoVIII - Correlação entre Itens

**Status:** 🚧 EM DESENVOLVIMENTO (Receita Federal)

- **Objetivo:** Correlação entre Item de Serviço, NBS, cClassTrib e cIndOp (AnexoVII)
- **Regras de Negócio:** ❌ **NÃO HÁ** regras baseadas neste anexo no Piloto RTC
- **Produção:** ❌ **NÃO HAVERÁ** quando RTC estiver disponível em 01/01/2026
- **Sugestões:** Podem ser enviadas para atendimento.nfs-e@rfb.gov.br

**Impacto no Sistema:** ⚠️ **BAIXO** - Anexo VIII é apenas consultivo, sem impacto obrigatório

---

## 📊 PARTE 2: COMPARAÇÃO IMPLEMENTAÇÃO vs. NOVAS ESPECIFICAÇÕES

### ✅ Pontos Fortes da Implementação Atual

#### 1. **Estrutura de Dados Completa**
```python
# models/nfse_model.py - ServicoNFSe
✅ codigo_nbs: str = "101010000"
✅ percentual_total_tributos_federais: float = 0.0
✅ percentual_total_tributos_estaduais: float = 0.0
✅ percentual_total_tributos_municipais: float = 0.0
✅ finalidade_nfse: str = "0"
✅ indicador_consumidor_final: str = "0"
✅ codigo_indicador_operacao: str = "000001"
✅ indicador_destinatario: str = "0"
✅ cst_ibs_cbs: str = "001"
✅ codigo_classificacao_tributaria: str = "000001"
✅ codigo_localidade_incidencia: str = "3549805"
✅ percentual_redutor: float = 0.0
```

#### 2. **Persistência no Banco de Dados**
- ✅ Migração executada com sucesso (30/01/2026)
- ✅ 15 campos adicionados na tabela `nfse`
- ✅ Constraints de validação implementadas
- ✅ Índices criados para performance
- ✅ Valores padrão configurados

#### 3. **Camadas de Aplicação**
- ✅ **Models:** Estrutura completa em Python
- ✅ **Services:** Mapeamento de dados implementado
- ✅ **Routes:** Coleta de formulário configurada
- ✅ **Templates:** Formulário de emissão com todos os campos
- ✅ **Visualização:** Exibição de dados IBS/CBS implementada

#### 4. **Testes Realizados**
```python
# tests/test_nfse_reforma_tributaria.py
✅ Teste de criação com todos os campos
✅ Teste de validação de código NBS
✅ Teste de cálculo de valores
✅ Teste de valores padrão
✅ Todos os 4 testes passaram
```

---

### ⚠️ Gaps Identificados vs. NT007

#### 1. **Geração de XML - Tags IBS/CBS Ausentes**

**Status:** ❌ **CRÍTICO - NÃO IMPLEMENTADO**

A geração de XML atual (`services/nfse_service.py`) **NÃO inclui** as tags da Reforma Tributária:

```python
# 🔴 AUSENTE NO XML ATUAL
# Deveria estar em gerar_xml_rps() após <Valores>
```

**Tags Necessárias (NT007 - Anexo VI v1.03.00):**

```xml
<!-- ⚠️ TAGS NÃO GERADAS ATUALMENTE -->
<trib>
    <tribTot>
        <pTotTribFed>0.00</pTotTribFed>
        <pTotTribEst>0.00</pTotTribEst>
        <pTotTribMun>5.00</pTotTribMun>
    </tribTot>
</trib>

<IBSCBS>
    <tpOp>0</tpOp>
    <indIni>0</indIni>
    <indFin>0</indFin>
    <cIndOp>000001</cIndOp>
    <cst>001</cst>
    <cClassTrib>000001</cClassTrib>
    <cLocInc>3549805</cLocInc>
    <pRedBC>0.00</pRedBC>
</IBSCBS>
```

**Localização no Código:**
- **Arquivo:** `/services/nfse_service.py`
- **Função:** `gerar_xml_rps()`
- **Linha aproximada:** 220-250 (após `<Valores>`)

---

#### 2. **Validação de Códigos conforme AnexoVII v1.01.00**

**Status:** ⚠️ **PARCIAL**

| Item | Implementado | NT007 Requer | Ação Necessária |
|------|--------------|--------------|-----------------|
| Validação cIndOp | ❌ Não | ✅ AnexoVII v1.01.00 | 🔧 Implementar lookup |
| Validação cClassTrib | ❌ Não | ✅ tabela oficial | 🔧 Implementar tabela |
| Validação CST | ⚠️ Básica (001-008) | ✅ Lista expandida | 🔧 Atualizar lista |
| Validação NBS | ⚠️ Formato apenas | ✅ Tabela NBS oficial | 🔧 Implementar tabela |

**AnexoVII - Indicadores de Operação (v1.01.00):**
- 📋 Lista de códigos `cIndOp` válidos
- 🔗 Correlação com tipos de operação
- ⚠️ **Não há no sistema:** Tabela de validação

---

#### 3. **Schemas XSD da NT007**

**Status:** ⚠️ **NÃO DISPONÍVEL LOCALMENTE**

```bash
# 🔴 AUSENTE NO PROJETO
# Schemas XSD NT007 não estão no repositório

/schemas/
├── nfse_rtc_v1.03.00.xsd  # ❌ NÃO EXISTE
├── tipos_rtc_v1.03.00.xsd  # ❌ NÃO EXISTE
└── ibscbs_v1.03.00.xsd     # ❌ NÃO EXISTE
```

**Ação Necessária:**
1. 📥 Baixar XSD schemas da NT007 do portal gov.br
2. 🧪 Validar XML gerado contra schemas atualizados
3. 🔧 Corrigir estrutura se necessário

---

#### 4. **Endpoint GISS RTC**

**Status:** ⚠️ **URLs PODEM ESTAR DESATUALIZADAS**

Configuração atual:
```python
# services/nfse_service.py
URLS_SJRP = {
    "homologacao": {
        "base": "https://ws-homologacao-rtc.giss.com.br/",
        "wsdl": "https://ws-homologacao-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl",
    },
    "producao": {
        "base": "https://ws-rtc.giss.com.br/",
        "wsdl": "https://ws-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl",
    }
}
```

**Verificação Necessária:**
- ✅ URLs contêm sufixo `-rtc` (Reforma Tributária do Consumo)
- ⚠️ Confirmar se endpoints aceitam layout v1.03.00
- ⚠️ Testar conectividade e resposta

---

### 🔄 Compatibilidade com Versões Anteriores

| Aspecto | Status | Observação |
|---------|--------|-----------|
| **NT004 (v1.01.03)** | ✅ Compatível | Layout atual em produção desde 05/01/2026 |
| **NT007 (v1.03.00)** | ⚠️ Parcial | Campos OK, XML precisa atualização |
| **GISS v2.04** | ✅ Base implementada | Assinatura SHA1, namespaces GISS |
| **Backward Compatibility** | ✅ Mantida | Campos têm defaults, não quebra sistema |

---

## 🔧 PARTE 3: ADAPTAÇÕES NECESSÁRIAS

### 🎯 Prioridade ALTA (Crítico - Bloqueador)

#### 1. **Implementar Geração de Tags IBS/CBS no XML**

**Complexidade:** 🟡 Média  
**Esforço:** 4-6 horas  
**Impacto:** 🔴 CRÍTICO - Sem isso, XML é rejeitado

**Tarefas:**
```python
# ✅ IMPLEMENTAR em services/nfse_service.py

def gerar_xml_rps(self, nfse: NFSeNacional) -> str:
    """
    Atualizar para incluir tags IBS/CBS após <Valores>
    """
    
    # ... código existente até </Valores> ...
    
    # 🆕 ADICIONAR: Tributos Totais
    if (nfse.servico.percentual_total_tributos_federais > 0 or 
        nfse.servico.percentual_total_tributos_estaduais > 0 or 
        nfse.servico.percentual_total_tributos_municipais > 0):
        
        trib = etree.SubElement(valores, "{%s}trib" % self.NS_TIPOS)
        trib_tot = etree.SubElement(trib, "{%s}tribTot" % self.NS_TIPOS)
        
        etree.SubElement(trib_tot, "{%s}pTotTribFed" % self.NS_TIPOS).text = \
            f"{nfse.servico.percentual_total_tributos_federais:.2f}"
        etree.SubElement(trib_tot, "{%s}pTotTribEst" % self.NS_TIPOS).text = \
            f"{nfse.servico.percentual_total_tributos_estaduais:.2f}"
        etree.SubElement(trib_tot, "{%s}pTotTribMun" % self.NS_TIPOS).text = \
            f"{nfse.servico.percentual_total_tributos_municipais:.2f}"
    
    # 🆕 ADICIONAR: IBS/CBS
    ibscbs = etree.SubElement(servico_el, "{%s}IBSCBS" % self.NS_TIPOS)
    
    # Finalidade (tpOp)
    etree.SubElement(ibscbs, "{%s}tpOp" % self.NS_TIPOS).text = \
        nfse.servico.finalidade_nfse
    
    # Indicadores
    etree.SubElement(ibscbs, "{%s}indIni" % self.NS_TIPOS).text = \
        nfse.servico.indicador_consumidor_final
    etree.SubElement(ibscbs, "{%s}indFin" % self.NS_TIPOS).text = \
        nfse.servico.indicador_destinatario
    
    # Códigos operacionais
    etree.SubElement(ibscbs, "{%s}cIndOp" % self.NS_TIPOS).text = \
        nfse.servico.codigo_indicador_operacao
    etree.SubElement(ibscbs, "{%s}cst" % self.NS_TIPOS).text = \
        nfse.servico.cst_ibs_cbs
    etree.SubElement(ibscbs, "{%s}cClassTrib" % self.NS_TIPOS).text = \
        nfse.servico.codigo_classificacao_tributaria
    etree.SubElement(ibscbs, "{%s}cLocInc" % self.NS_TIPOS).text = \
        nfse.servico.codigo_localidade_incidencia
    
    # Percentual redutor (se aplicável)
    if nfse.servico.percentual_redutor > 0:
        etree.SubElement(ibscbs, "{%s}pRedBC" % self.NS_TIPOS).text = \
            f"{nfse.servico.percentual_redutor:.2f}"
    
    # ... continuar com resto do XML ...
```

**Validação:**
```bash
# Após implementação, validar XML gerado
python3 test_nfse_giss.py
```

---

#### 2. **Baixar e Validar XSD Schemas NT007**

**Complexidade:** 🟢 Baixa  
**Esforço:** 1-2 horas  
**Impacto:** 🟡 MÉDIO - Garante conformidade

**Tarefas:**

1. **Criar diretório para schemas:**
```bash
mkdir -p /Users/renato/Documents/Developement/api_nfe/schemas/nfse_rtc_nt007
cd /Users/renato/Documents/Developement/api_nfe/schemas/nfse_rtc_nt007
```

2. **Baixar schemas da NT007:**
```bash
# Acessar: https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc
# Baixar: "Esquemas XSD - AnexoVI-LeiautesRN_RTC_IBSCBS-V1.03.00 - NT007"
# Extrair para schemas/nfse_rtc_nt007/
```

3. **Implementar validação de XML:**
```python
# 🆕 CRIAR: services/nfse_xml_validator.py

from lxml import etree

def validar_xml_contra_xsd(xml_string: str, xsd_path: str) -> tuple[bool, str]:
    """
    Valida XML da NFS-e contra schema XSD da NT007
    
    Args:
        xml_string: XML a validar
        xsd_path: Caminho do arquivo XSD
        
    Returns:
        (sucesso, mensagem_erro)
    """
    try:
        # Carregar XSD
        with open(xsd_path, 'r', encoding='utf-8') as xsd_file:
            xsd_doc = etree.parse(xsd_file)
            schema = etree.XMLSchema(xsd_doc)
        
        # Parsear XML
        xml_doc = etree.fromstring(xml_string.encode('utf-8'))
        
        # Validar
        schema.assertValid(xml_doc)
        return True, "XML válido"
        
    except etree.DocumentInvalid as e:
        return False, f"XML inválido: {str(e)}"
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"
```

---

### 🎯 Prioridade MÉDIA (Importante)

#### 3. **Implementar Tabelas de Validação AnexoVII**

**Complexidade:** 🟡 Média  
**Esforço:** 6-8 horas  
**Impacto:** 🟡 MÉDIO - Melhora validação

**Tarefas:**

1. **Criar tabela de indicadores de operação:**
```sql
-- migrations/add_tabela_indicadores_operacao_nt007.sql

CREATE TABLE IF NOT EXISTS indicadores_operacao_ibscbs (
    codigo_indicador VARCHAR(6) PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    tipo_operacao VARCHAR(50) NOT NULL, -- 'Interna', 'Interestadual', 'Exterior'
    versao_anexo_vii VARCHAR(10) NOT NULL DEFAULT 'v1.01.00',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_indop_tipo ON indicadores_operacao_ibscbs(tipo_operacao);
CREATE INDEX idx_indop_ativo ON indicadores_operacao_ibscbs(ativo);

-- Popular com dados do AnexoVII v1.01.00
INSERT INTO indicadores_operacao_ibscbs (codigo_indicador, descricao, tipo_operacao) VALUES
('000001', 'Operação Interna', 'Interna'),
('000002', 'Operação Interestadual', 'Interestadual'),
('000003', 'Operação de Exportação', 'Exterior'),
-- ... adicionar demais códigos do AnexoVII v1.01.00
;
```

2. **Criar tabela de classificação tributária:**
```sql
-- migrations/add_tabela_classificacao_tributaria_nt007.sql

CREATE TABLE IF NOT EXISTS classificacao_tributaria_nfse (
    codigo_classificacao VARCHAR(6) PRIMARY KEY,
    descricao VARCHAR(200) NOT NULL,
    categoria VARCHAR(100),
    aliquota_sugerida_ibs DECIMAL(5,2),
    aliquota_sugerida_cbs DECIMAL(5,2),
    versao_anexo VARCHAR(10) NOT NULL DEFAULT 'v1.03.00',
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_classtrib_categoria ON classificacao_tributaria_nfse(categoria);
CREATE INDEX idx_classtrib_ativo ON classificacao_tributaria_nfse(ativo);
```

3. **Implementar validações no service:**
```python
# services/nfse_validation_service.py

def validar_codigo_indicador_operacao(codigo: str, db) -> tuple[bool, str]:
    """Valida se código de operação existe no AnexoVII"""
    from database.models import IndicadorOperacaoIBSCBS
    
    indicador = db.query(IndicadorOperacaoIBSCBS).filter_by(
        codigo_indicador=codigo,
        ativo=True
    ).first()
    
    if not indicador:
        return False, f"Código de operação '{codigo}' inválido (AnexoVII v1.01.00)"
    
    return True, indicador.descricao

def validar_classificacao_tributaria(codigo: str, db) -> tuple[bool, str]:
    """Valida se código de classificação tributária é válido"""
    from database.models import ClassificacaoTributariaNFSe
    
    classificacao = db.query(ClassificacaoTributariaNFSe).filter_by(
        codigo_classificacao=codigo,
        ativo=True
    ).first()
    
    if not classificacao:
        return False, f"Classificação tributária '{codigo}' inválida"
    
    return True, classificacao.descricao
```

---

#### 4. **Criar Tabela NBS (Nomenclatura Brasileira de Serviços)**

**Complexidade:** 🟡 Média  
**Esforço:** 4-6 horas  
**Impacto:** 🟡 MÉDIO - Facilita seleção

**Tarefas:**

```sql
-- migrations/add_tabela_nbs_oficial.sql

CREATE TABLE IF NOT EXISTS nomenclatura_brasileira_servicos (
    codigo_nbs VARCHAR(9) PRIMARY KEY,
    descricao TEXT NOT NULL,
    codigo_lc116 VARCHAR(5), -- Correlação com LC 116/2003
    categoria VARCHAR(100),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices
CREATE INDEX idx_nbs_codigo_lc116 ON nomenclatura_brasileira_servicos(codigo_lc116);
CREATE INDEX idx_nbs_categoria ON nomenclatura_brasileira_servicos(categoria);
CREATE INDEX idx_nbs_ativo ON nomenclatura_brasileira_servicos(ativo);

-- Exemplos (popular com lista oficial completa)
INSERT INTO nomenclatura_brasileira_servicos (codigo_nbs, descricao, codigo_lc116, categoria) VALUES
('101010000', 'Análise e desenvolvimento de sistemas', '01.01', 'Informática'),
('101020000', 'Programação', '01.02', 'Informática'),
('101030000', 'Processamento de dados', '01.03', 'Informática'),
-- ... adicionar todos os códigos NBS oficiais
;
```

---

### 🎯 Prioridade BAIXA (Desejável)

#### 5. **Implementar Seletor Dinâmico de NBS no Formulário**

**Complexidade:** 🟡 Média  
**Esforço:** 3-4 horas  
**Impacto:** 🟢 BAIXO - UX melhorada

```html
<!-- templates/admin/nfse/emitir.html -->

<!-- 🆕 Substituir input text por select2 com busca -->
<div class="form-group">
    <label for="codigo_nbs">Código NBS *</label>
    <select id="codigo_nbs" name="codigo_nbs" class="form-control select2" required>
        <option value="">Selecione o código NBS</option>
        <!-- Populado via AJAX -->
    </select>
    <small class="form-text text-muted">
        Nomenclatura Brasileira de Serviços (9 dígitos)
    </small>
</div>

<script>
// Configurar select2 com busca remota
$('#codigo_nbs').select2({
    ajax: {
        url: '/api/nbs/search',
        dataType: 'json',
        delay: 250,
        data: function (params) {
            return {
                q: params.term, // termo de busca
                page: params.page || 1
            };
        },
        processResults: function (data, params) {
            return {
                results: data.results.map(item => ({
                    id: item.codigo_nbs,
                    text: `${item.codigo_nbs} - ${item.descricao}`
                }))
            };
        }
    },
    minimumInputLength: 2,
    placeholder: 'Digite para buscar código NBS'
});
</script>
```

**Endpoint API:**
```python
# routes/nbs_api_routes.py

@app.route('/api/nbs/search', methods=['GET'])
def buscar_nbs():
    """Busca códigos NBS para autocomplete"""
    termo = request.args.get('q', '')
    page = int(request.args.get('page', 1))
    per_page = 20
    
    query = db.query(NomenclaturaBrasileiraServicos).filter(
        db.or_(
            NomenclaturaBrasileiraServicos.codigo_nbs.ilike(f'%{termo}%'),
            NomenclaturaBrasileiraServicos.descricao.ilike(f'%{termo}%')
        )
    ).filter_by(ativo=True)
    
    total = query.count()
    resultados = query.offset((page-1)*per_page).limit(per_page).all()
    
    return jsonify({
        'results': [
            {
                'codigo_nbs': r.codigo_nbs,
                'descricao': r.descricao,
                'codigo_lc116': r.codigo_lc116
            }
            for r in resultados
        ],
        'pagination': {
            'more': (page * per_page) < total
        }
    })
```

---

#### 6. **Atualizar Endpoint para Homologação RTC**

**Complexidade:** 🟢 Baixa  
**Esforço:** 1 hora  
**Impacto:** 🟢 BAIXO - Testes em ambiente atualizado

```python
# services/nfse_service.py

# ⚠️ VERIFICAR URLs atualizadas para NT007
URLS_SJRP = {
    "homologacao": {
        # ✅ URL já contém sufixo -rtc
        "base": "https://ws-homologacao-rtc.giss.com.br/",
        "wsdl": "https://ws-homologacao-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl",
        # 🔧 ADICIONAR: versão do layout suportada
        "versao_layout": "1.03.00",  # NT007
        "versao_anexo_vii": "1.01.00"
    },
    "producao": {
        "base": "https://ws-rtc.giss.com.br/",
        "wsdl": "https://ws-rtc.giss.com.br/service-ws/nf/nfse-ws?wsdl",
        "versao_layout": "1.03.00",  # NT007
        "versao_anexo_vii": "1.01.00"
    }
}
```

---

## 📊 Resumo de Ações por Prioridade

| Prioridade | Ação | Esforço | Impacto | Prazo Sugerido |
|------------|------|---------|---------|----------------|
| 🔴 **ALTA** | 1. Implementar tags IBS/CBS no XML | 4-6h | Crítico | Imediato |
| 🔴 **ALTA** | 2. Baixar e validar XSD NT007 | 1-2h | Médio | Imediato |
| 🟡 **MÉDIA** | 3. Tabelas validação AnexoVII | 6-8h | Médio | 1 semana |
| 🟡 **MÉDIA** | 4. Tabela NBS oficial | 4-6h | Médio | 2 semanas |
| 🟢 **BAIXA** | 5. Seletor dinâmico NBS | 3-4h | Baixo | 1 mês |
| 🟢 **BAIXA** | 6. Atualizar endpoints RTC | 1h | Baixo | 1 mês |

**Total Esforço Estimado:** 19-27 horas

---

## ✅ Checklist de Implementação NT007

### Fase 1: Crítico (Bloqueador)
- [ ] Implementar geração de tags `<trib>` no XML
- [ ] Implementar geração de tags `<IBSCBS>` no XML
- [ ] Baixar schemas XSD NT007 do portal gov.br
- [ ] Criar função de validação de XML contra XSD
- [ ] Testar XML gerado em homologação RTC

### Fase 2: Validações (Importante)
- [ ] Criar tabela `indicadores_operacao_ibscbs`
- [ ] Popular tabela com dados AnexoVII v1.01.00
- [ ] Criar tabela `classificacao_tributaria_nfse`
- [ ] Implementar validações em `nfse_validation_service.py`
- [ ] Adicionar validações na rota de emissão

### Fase 3: Dados Auxiliares (Desejável)
- [ ] Criar tabela `nomenclatura_brasileira_servicos`
- [ ] Popular com lista oficial NBS completa
- [ ] Criar endpoint API `/api/nbs/search`
- [ ] Implementar select2 no formulário de emissão
- [ ] Adicionar filtros por categoria LC 116

### Fase 4: Homologação (Final)
- [ ] Validar URLs webservice GISS RTC
- [ ] Testar envio com layout v1.03.00
- [ ] Verificar retorno do webservice
- [ ] Documentar erros/ajustes necessários
- [ ] Atualizar documentação do projeto

---

## 🔗 Referências

### Documentação Oficial
1. **Portal NFS-e Gov.br:**
   - https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc

2. **Notas Técnicas:**
   - NT007: AnexoVI-LeiautesRN_RTC_IBSCBS-V1.03.00
   - NT007: AnexoVII-IndOp_IBSCBS_V1.01.00
   - NT004: Layout em produção desde 05/01/2026

3. **GISS Online (São José do Rio Preto):**
   - Homologação: https://ws-homologacao-rtc.giss.com.br/
   - Produção: https://ws-rtc.giss.com.br/

4. **Contato Suporte RFB:**
   - E-mail: atendimento.nfs-e@rfb.gov.br
   - Assunto: "AnexoVIII" ou "Dúvidas NT007"

### Legislação
- Lei Complementar nº 214/2025 (Reforma Tributária do Consumo)
- Lei Complementar nº 116/2003 (Lista de Serviços)

---

## 📝 Notas Importantes

### ⚠️ Ambiente de Produção
- **NT004 (v1.01.03)** está em produção desde 05/01/2026
- **NT007 (v1.03.00)** ainda não tem data de disponibilização em produção
- Sistema deve manter compatibilidade com ambas as versões durante transição

### 🔮 AnexoVIII (Em Desenvolvimento)
- NÃO há obrigatoriedade de implementar correlações do AnexoVIII
- Anexo é apenas consultivo e está em revisão pela RFB
- Sugestões podem ser enviadas mas não há SLA de resposta

### 🧪 Testes Recomendados
1. Validar XML contra XSD NT007 localmente
2. Testar envio em ambiente de homologação RTC
3. Validar resposta do webservice GISS
4. Conferir se nota é processada e convertida
5. Verificar PDF/DANFSE gerado

---

## 📞 Suporte

**Dúvidas sobre esta análise:**
- Revisar código-fonte em `/Users/renato/Documents/Developement/api_nfe`
- Consultar documentação em `/docs/`
- Contatar equipe de desenvolvimento

**Dúvidas sobre NT007:**
- Portal: https://www.gov.br/nfse/pt-br
- E-mail: atendimento.nfs-e@rfb.gov.br

---

**Última Atualização:** 9 de fevereiro de 2026  
**Versão do Documento:** 1.0  
**Autor:** Análise Automática baseada em documentação oficial RFB
