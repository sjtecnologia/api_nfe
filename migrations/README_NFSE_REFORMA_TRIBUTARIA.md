# Migração - Campos Reforma Tributária NFS-e

## 📋 Descrição

Esta migração adiciona os campos obrigatórios da **Reforma Tributária (LC 214/2025)** na tabela `nfse` do banco de dados. Estes campos são necessários para a emissão de NFS-e no sistema GISS Online de São José do Rio Preto conforme as novas exigências fiscais de IBS/CBS.

## 📅 Data

30 de janeiro de 2026

## 🎯 Objetivo

Adicionar 15 novos campos relacionados a:
- **IBS/CBS** (Imposto sobre Bens e Serviços / Contribuição sobre Bens e Serviços)
- **Tributos Totais** (Federal, Estadual e Municipal)
- **Classificações Tributárias** da Reforma

## 📝 Campos Adicionados

### 1. Identificação do Serviço
| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `codigo_nbs` | VARCHAR(9) | '101010000' | Código NBS - Nomenclatura Brasileira de Serviços (9 dígitos) |

### 2. Finalidade e Indicadores
| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `finalidade_nfse` | VARCHAR(1) | '0' | 0=Normal, 1=Complementar, 2=Ajuste, 3=Substituição |
| `indicador_consumidor_final` | VARCHAR(1) | '0' | 0=Não, 1=Sim |
| `indicador_destinatario` | VARCHAR(1) | '0' | 0=Interno, 1=Interestadual, 2=Exterior |

### 3. IBS/CBS - Reforma Tributária
| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `codigo_indicador_operacao` | VARCHAR(6) | '000001' | Código da operação (000001=Interna, 000002=Interestadual, 000003=Exterior) |
| `cst_ibs_cbs` | VARCHAR(3) | '001' | CST IBS/CBS (001=Tributado cheia, 002=Redução, 003=Diferido, etc.) |
| `codigo_classificacao_tributaria` | VARCHAR(6) | '000001' | Código de classificação tributária (6 dígitos) |
| `codigo_localidade_incidencia` | VARCHAR(7) | '3549805' | Código IBGE do município de incidência (SJRP padrão) |
| `percentual_redutor` | DECIMAL(5,2) | 0.00 | Percentual de redução da base de cálculo (0 a 100) |

### 4. Tributos Totais
| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `percentual_total_tributos_federais` | DECIMAL(5,2) | 0.00 | % tributos federais sobre valor do serviço |
| `percentual_total_tributos_estaduais` | DECIMAL(5,2) | 0.00 | % tributos estaduais sobre valor do serviço |
| `percentual_total_tributos_municipais` | DECIMAL(5,2) | 5.00 | % tributos municipais (geralmente ISS) |

### 5. Regime Tributário
| Campo | Tipo | Default | Descrição |
|-------|------|---------|-----------|
| `regime_especial_tributacao` | VARCHAR(1) | NULL | 1=ME, 2=Estimativa, 3=Sociedade Prof., 4=Cooperativa, 5=MEI, 6=Simples |
| `optante_simples_nacional` | BOOLEAN | TRUE | Indica se é optante do Simples Nacional |
| `incentivador_cultural` | BOOLEAN | FALSE | Indica se é incentivador cultural |

## 🔧 Como Executar

### Opção 1: Via Script Python (Recomendado)

```bash
cd /Users/renato/Documents/Developement/api_nfe
python3 migrations/run_migration_nfse_reforma.py
```

O script irá:
1. ✅ Conectar ao banco de dados
2. ✅ Executar a migration
3. ✅ Verificar os campos adicionados
4. ✅ Mostrar estatísticas

### Opção 2: Via psql Direto

```bash
cd /Users/renato/Documents/Developement/api_nfe
psql -U seu_usuario -d sjtnfe -f migrations/add_nfse_reforma_tributaria_campos.sql
```

## ⚠️ Importante

### Pré-requisitos
- A tabela `nfse` deve existir (execute `create_table_nfse.sql` primeiro se necessário)
- Conexão ativa com o banco de dados PostgreSQL
- Permissões para ALTER TABLE

### Segurança
- ✅ A migration usa `IF NOT EXISTS` para evitar erros se já executada
- ✅ Usa transações (BEGIN/COMMIT) para garantir atomicidade
- ✅ Adiciona constraints para validar valores
- ✅ Cria índices para melhorar performance

### Impacto
- ✅ **Zero downtime** - campos são adicionados com defaults
- ✅ Registros existentes recebem valores padrão automaticamente
- ✅ Não afeta funcionamento atual do sistema

## 📊 Índices Criados

Para melhorar a performance das consultas:

```sql
idx_nfse_codigo_nbs
idx_nfse_finalidade
idx_nfse_localidade_incidencia
idx_nfse_cst_ibs_cbs
```

## ✅ Constraints Adicionadas

Validações automáticas:

```sql
chk_finalidade_nfse           -- Valores: '0', '1', '2', '3'
chk_indicador_consumidor_final -- Valores: '0', '1'
chk_indicador_destinatario    -- Valores: '0', '1', '2'
chk_percentual_redutor        -- Range: 0 a 100
chk_percentual_tributos_*     -- Range: 0 a 100 (3 constraints)
```

## 🔄 Próximos Passos

Após executar a migração:

1. ✅ **Banco de Dados** - Campos adicionados
2. 🔄 **Modelo Python** - Atualizar `models/nfse_model.py` (já contém os campos)
3. 🔄 **Service Layer** - Atualizar `services/nfse_service.py` para processar novos campos
4. 🔄 **Routes** - Atualizar `routes/nfse_routes.py` para receber dados do formulário
5. 🔄 **XML Generator** - Atualizar geração de XML para incluir campos IBS/CBS
6. ✅ **Formulário** - Já contém os campos (`templates/admin/nfse/emitir.html`)

## 🧪 Teste

Após a migração, verificar:

```sql
-- Listar todos os campos da tabela nfse
SELECT column_name, data_type, column_default
FROM information_schema.columns 
WHERE table_name = 'nfse' 
ORDER BY ordinal_position;

-- Verificar constraints
SELECT constraint_name, constraint_type
FROM information_schema.table_constraints
WHERE table_name = 'nfse';

-- Verificar índices
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'nfse';
```

## 📚 Referências

- **Lei Complementar 214/2025** - Reforma Tributária
- **GISS Online** - Sistema de NFS-e São José do Rio Preto
- **NBS** - Nomenclatura Brasileira de Serviços
- **ABRASF 2.04** - Padrão Nacional de NFS-e

## 🐛 Troubleshooting

### Erro: "relation nfse does not exist"
**Solução:** Execute primeiro o script `create_table_nfse.sql`

### Erro: "column already exists"
**Solução:** A migração já foi executada. Use `IF NOT EXISTS` no ALTER TABLE

### Erro: "permission denied"
**Solução:** Verifique as permissões do usuário no banco de dados

## 📞 Suporte

Para dúvidas ou problemas:
- Verifique os logs do PostgreSQL
- Execute o script com modo verbose
- Consulte a documentação do GISS Online

---

**Versão:** 1.0  
**Autor:** Sistema API NFe  
**Data:** 30/01/2026
