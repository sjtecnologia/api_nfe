# Análise: Regras Tributárias vs NFS-e

**Data:** 30/01/2026  
**Objetivo:** Verificar se a tabela `regras_tributacao` atende os requisitos para emissão de NFS-e

---

## 📋 Resumo Executivo

A tabela **`regras_tributacao`** atual é focada em **NFe (Nota Fiscal de Produtos)** e contém campos específicos para:
- ICMS (CST, CSOSN, alíquotas, modalidade BC)
- PIS/COFINS (CST, alíquotas)
- IPI (CST, alíquota)
- CFOP e NCM

Para **NFS-e (Nota Fiscal de Serviços)**, são necessários campos completamente diferentes relacionados a:
- ISS (Imposto Sobre Serviços)
- Códigos de Serviço (LC 116/2003)
- NBS (Nomenclatura Brasileira de Serviços)
- Reforma Tributária (IBS/CBS)

## 🔍 Análise Detalhada

### ✅ Campos Existentes em `regras_tributacao`

```sql
-- Campos da tabela atual
regra_tributacao_id          BIGINT (PK)
cliente_id                   BIGINT (FK)
regime_tributario_id         BIGINT (FK)
cfop_id                      BIGINT (FK)      -- NFe
ncm_id                       BIGINT (FK)      -- NFe (produtos)
uf_origem                    VARCHAR(2)
uf_destino                   VARCHAR(2)
tipo_item                    VARCHAR(10)
prioridade                   INTEGER
cst_icms                     VARCHAR(2)       -- NFe
csosn_icms                   VARCHAR(3)       -- NFe
aliquota_icms                NUMERIC(5,2)     -- NFe
reducao_base_icms            NUMERIC(5,2)     -- NFe
modalidade_bc_icms           INTEGER          -- NFe
motivo_desoneracao_icms      INTEGER          -- NFe
cst_pis                      VARCHAR(3)       -- NFe
aliquota_pis                 NUMERIC(5,2)     -- NFe
cst_cofins                   VARCHAR(3)       -- NFe
aliquota_cofins              NUMERIC(5,2)     -- NFe
cst_ipi                      VARCHAR(3)       -- NFe
aliquota_ipi                 NUMERIC(5,2)     -- NFe
descricao_regra              TEXT
data_criacao                 TIMESTAMP
ativo                        BOOLEAN
created_by_user_id           BIGINT
```

**Conclusão:** Todos os campos são específicos para NFe (produtos).

---

### ❌ Campos Necessários para NFS-e (Ausentes)

#### 1. ISS (Obrigatório)
```sql
aliquota_iss                 NUMERIC(5,2)     -- FALTANDO
iss_retido                   BOOLEAN          -- FALTANDO
responsavel_retencao         VARCHAR(1)       -- FALTANDO (1=Tomadores, 2=Intermediário)
```

#### 2. Código de Serviço (Obrigatório)
```sql
codigo_servico_lc116         VARCHAR(5)       -- FALTANDO
-- Ex: "01.01" = Análise e desenvolvimento de sistemas
-- Ex: "17.05" = Serviços de medicina
```

#### 3. NBS - Nomenclatura Brasileira de Serviços (Obrigatório)
```sql
codigo_nbs                   VARCHAR(9)       -- FALTANDO
-- Ex: "101010000" = Serviços de tecnologia
```

#### 4. Reforma Tributária LC 214/2025 (Obrigatório a partir de 2026)
```sql
cst_ibs_cbs                  VARCHAR(3)       -- FALTANDO
-- 001=Tributado, 002=Redução, 003=Diferido, 004=Isento, etc.

percentual_total_tributos_federais    NUMERIC(5,2)  -- FALTANDO
percentual_total_tributos_estaduais   NUMERIC(5,2)  -- FALTANDO
percentual_total_tributos_municipais  NUMERIC(5,2)  -- FALTANDO

codigo_indicador_operacao    VARCHAR(6)       -- FALTANDO
-- 000001=Interna, 000002=Interestadual, 000003=Exterior

codigo_classificacao_tributaria VARCHAR(6)   -- FALTANDO
codigo_localidade_incidencia VARCHAR(7)      -- FALTANDO (código IBGE município)
percentual_redutor           NUMERIC(5,2)     -- FALTANDO
```

#### 5. Regime Especial (Opcional mas importante)
```sql
regime_especial_tributacao   VARCHAR(1)       -- FALTANDO
-- 1=ME Municipal, 2=Estimativa, 3=Soc. Profissionais, 4=Cooperativa, 5=MEI, 6=Simples
optante_simples_nacional     BOOLEAN          -- FALTANDO
incentivador_cultural        BOOLEAN          -- FALTANDO
```

#### 6. Campos de Classificação
```sql
finalidade_nfse              VARCHAR(1)       -- FALTANDO
-- 0=Normal, 1=Complementar, 2=Ajuste, 3=Substituição

indicador_consumidor_final   VARCHAR(1)       -- FALTANDO
-- 0=Não, 1=Sim

indicador_destinatario       VARCHAR(1)       -- FALTANDO
-- 0=Interno (mesmo município), 1=Interestadual, 2=Exterior
```

---

## 🎯 Estado Atual da Emissão de NFS-e

### Como Funciona Hoje?

Atualmente, a emissão de NFS-e **NÃO USA** a tabela `regras_tributacao`. Os valores são:

1. **Preenchidos manualmente no formulário** pelo usuário
2. **Salvos diretamente na tabela `nfse`**
3. **Valores padrão hardcoded** no service:

```python
# services/nfse_service.py - linha ~600
servico = ServicoNFSe(
    codigo_servico=dados.get('codigo_servico', '01.01'),  # Hardcoded
    codigo_nbs='101010000',                                 # Hardcoded
    aliquota_iss=dados.get('aliquota_iss', Decimal('5.00')), # Form
    percentual_total_tributos_federais=dados.get('percentual_total_tributos_federais', 0),  # Form
    # ... etc
)
```

### Problemas:
- ❌ Usuário precisa preencher TUDO manualmente a cada NFS-e
- ❌ Não há "memória" das alíquotas usadas anteriormente
- ❌ Mais sujeito a erros de digitação
- ❌ Não aproveita automação de regras

---

## 💡 Soluções Propostas

### **Opção 1: Tabela Separada** (Recomendado ✅)

Criar `regras_tributacao_servicos` específica para NFS-e:

```sql
CREATE TABLE regras_tributacao_servicos (
    regra_id                          BIGSERIAL PRIMARY KEY,
    cliente_id                        BIGINT NOT NULL REFERENCES clientes(cliente_id),
    regime_tributario_id              BIGINT NOT NULL REFERENCES regimes_tributarios(regime_tributario_id),
    
    -- Identificação do serviço
    codigo_servico_lc116              VARCHAR(5) NOT NULL,     -- "01.01", "17.05", etc
    codigo_nbs                        VARCHAR(9) NOT NULL,     -- "101010000"
    descricao_servico                 TEXT,
    
    -- ISS
    aliquota_iss                      NUMERIC(5,2) NOT NULL,   -- 2.00 a 5.00
    iss_retido                        BOOLEAN DEFAULT FALSE,
    responsavel_retencao              VARCHAR(1),              -- 1=Tomadores, 2=Intermediário
    
    -- Reforma Tributária
    cst_ibs_cbs                       VARCHAR(3) DEFAULT '001',
    codigo_indicador_operacao         VARCHAR(6) DEFAULT '000001',
    codigo_classificacao_tributaria   VARCHAR(6) DEFAULT '000001',
    codigo_localidade_incidencia      VARCHAR(7) DEFAULT '3549805',
    percentual_redutor                NUMERIC(5,2) DEFAULT 0.00,
    percentual_total_tributos_federais   NUMERIC(5,2) DEFAULT 0.00,
    percentual_total_tributos_estaduais  NUMERIC(5,2) DEFAULT 0.00,
    percentual_total_tributos_municipais NUMERIC(5,2) DEFAULT 5.00,
    
    -- Regime Especial
    regime_especial_tributacao        VARCHAR(1),
    optante_simples_nacional          BOOLEAN DEFAULT TRUE,
    incentivador_cultural             BOOLEAN DEFAULT FALSE,
    
    -- Condições de aplicação
    uf_origem                         VARCHAR(2),
    uf_destino                        VARCHAR(2),
    indicador_destinatario            VARCHAR(1) DEFAULT '0',
    indicador_consumidor_final        VARCHAR(1) DEFAULT '0',
    finalidade_nfse                   VARCHAR(1) DEFAULT '0',
    
    -- Controle
    prioridade                        INTEGER DEFAULT 100,
    descricao_regra                   TEXT,
    ativo                             BOOLEAN DEFAULT TRUE,
    data_criacao                      TIMESTAMP DEFAULT NOW(),
    created_by_user_id                BIGINT REFERENCES users(id)
);

CREATE INDEX idx_regras_servicos_cliente ON regras_tributacao_servicos(cliente_id);
CREATE INDEX idx_regras_servicos_codigo ON regras_tributacao_servicos(codigo_servico_lc116);
CREATE INDEX idx_regras_servicos_nbs ON regras_tributacao_servicos(codigo_nbs);
```

**Vantagens:**
- ✅ Campos específicos para serviços
- ✅ Não interfere com regras de NFe existentes
- ✅ Fácil de expandir no futuro
- ✅ Queries mais eficientes
- ✅ Manutenção separada

**Desvantagens:**
- ⚠️ Mais uma tabela no sistema
- ⚠️ Necessário código adicional para buscar regras

---

### **Opção 2: Adicionar Campos à Tabela Existente**

Adicionar colunas nullable em `regras_tributacao`:

```sql
ALTER TABLE regras_tributacao ADD COLUMN tipo_regra VARCHAR(10) DEFAULT 'NFE';
-- 'NFE' ou 'NFSE'

-- Campos para NFS-e
ALTER TABLE regras_tributacao ADD COLUMN codigo_servico_lc116 VARCHAR(5);
ALTER TABLE regras_tributacao ADD COLUMN codigo_nbs VARCHAR(9);
ALTER TABLE regras_tributacao ADD COLUMN aliquota_iss NUMERIC(5,2);
-- ... adicionar todos os campos da Opção 1
```

**Vantagens:**
- ✅ Apenas uma tabela
- ✅ Uso do mesmo CRUD existente

**Desvantagens:**
- ❌ Tabela muito grande e confusa
- ❌ Muitos campos NULL (NFe não usa ISS, NFS-e não usa ICMS)
- ❌ Difícil manutenção
- ❌ Validações complexas (tipo_regra='NFE' requer cfop_id, etc)

---

### **Opção 3: Status Quo** (Atual)

Manter como está: formulário manual sem automação.

**Desvantagens:**
- ❌ Usuário digita tudo manualmente
- ❌ Sem reuso de configurações
- ❌ Mais erros humanos

---

## 🎯 Recomendação Final

### ✅ Implementar Opção 1: Tabela Separada

**Por quê?**
1. **Separação de responsabilidades**: NFe tem ICMS/IPI, NFS-e tem ISS - são mundos diferentes
2. **Facilita expansão futura**: Novos campos da Reforma podem ser adicionados sem afetar NFe
3. **Melhor performance**: Queries mais simples e rápidas
4. **Manutenção clara**: Desenvolvedores sabem onde mexer em cada tipo de nota

**Impacto:**
- ⏱️ 4-6 horas de desenvolvimento
- 📝 Migration SQL + Model Python + CRUD básico
- 🔧 Ajuste no formulário NFS-e para buscar regras

---

## 📝 Próximos Passos

Se aprovar a Opção 1:

1. ✅ Criar migration SQL (`create_table_regras_tributacao_servicos.sql`)
2. ✅ Criar model Python (`RegraTributacaoServico`)
3. ✅ Criar CRUD no admin (listar, criar, editar, deletar)
4. ✅ Ajustar formulário NFS-e para buscar regras automaticamente
5. ✅ Migrar dados existentes (se houver)
6. ✅ Documentar novos campos

---

## 📊 Comparação Visual

```
┌─────────────────────────────────┬──────────────────────────────────┐
│   REGRAS TRIBUTAÇÃO (NFe)       │  REGRAS SERVIÇOS (NFS-e)         │
├─────────────────────────────────┼──────────────────────────────────┤
│ ✓ CFOP                          │ ✗ CFOP não aplicável              │
│ ✓ NCM (produtos)                │ ✓ NBS (serviços)                  │
│ ✓ CST ICMS                      │ ✗ ICMS não aplicável              │
│ ✓ CSOSN                         │ ✗ CSOSN não aplicável             │
│ ✓ Alíquota ICMS                 │ ✓ Alíquota ISS                    │
│ ✓ CST PIS/COFINS                │ ✗ PIS/COFINS diferentes           │
│ ✓ CST/Alíquota IPI              │ ✗ IPI não aplicável               │
│ ✗ Código Serviço LC116          │ ✓ Código Serviço LC116            │
│ ✗ ISS Retido                    │ ✓ ISS Retido                      │
│ ✗ CST IBS/CBS                   │ ✓ CST IBS/CBS                     │
│ ✗ % Tributos (Fed/Est/Mun)      │ ✓ % Tributos (Fed/Est/Mun)        │
│ ✗ Regime Especial               │ ✓ Regime Especial                 │
└─────────────────────────────────┴──────────────────────────────────┘
```

---

## 🚨 Conclusão

**Status Atual:** ❌ Tabela `regras_tributacao` **NÃO atende** requisitos de NFS-e

**Motivo:** Campos são específicos para NFe (produtos) com ICMS, enquanto NFS-e precisa de ISS, códigos de serviço, NBS e campos da Reforma Tributária.

**Solução Recomendada:** Criar tabela separada `regras_tributacao_servicos`

**Benefício:** Automação na emissão de NFS-e, menos erros, melhor experiência do usuário.
