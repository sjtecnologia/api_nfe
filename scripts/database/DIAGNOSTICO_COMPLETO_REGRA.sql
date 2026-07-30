-- =====================================================
-- DIAGNÓSTICO COMPLETO - Por que a regra não foi encontrada?
-- =====================================================
-- Use com os parâmetros exatos do log do browser
-- =====================================================

-- 📋 PARÂMETROS DO SEU LOG:
-- cliente_id: 11
-- regime_tributario_id: 1
-- ncm_codigo: "85285900"
-- cfop_codigo: "5101"
-- uf_origem: "SP"
-- uf_destino: "SP"

-- =====================================================
-- PASSO 1: Verificar se NCM existe
-- =====================================================

SELECT 
    'NCM' as tipo,
    ncm_id,
    codigo,
    descricao,
    CASE 
        WHEN ncm_id IS NOT NULL THEN '✅ NCM EXISTE'
        ELSE '❌ NCM NÃO EXISTE - CADASTRE PRIMEIRO!'
    END as status
FROM ncms
WHERE codigo = '85285900';

-- Se não retornar nada, o NCM não existe!
-- Solução: Cadastrar o NCM primeiro


-- =====================================================
-- PASSO 2: Verificar se CFOP existe
-- =====================================================

SELECT 
    'CFOP' as tipo,
    cfop_id,
    cfop,
    descricao,
    CASE 
        WHEN cfop_id IS NOT NULL THEN '✅ CFOP EXISTE'
        ELSE '❌ CFOP NÃO EXISTE - CADASTRE PRIMEIRO!'
    END as status
FROM cfops
WHERE cfop = '5101';

-- Se não retornar nada, o CFOP não existe!
-- Solução: Cadastrar o CFOP primeiro


-- =====================================================
-- PASSO 3: Verificar IDs encontrados
-- =====================================================

SELECT 
    '📊 IDs Encontrados' as info,
    (SELECT ncm_id FROM ncms WHERE codigo = '85285900') as ncm_id_encontrado,
    (SELECT cfop_id FROM cfops WHERE cfop = '5101') as cfop_id_encontrado;


-- =====================================================
-- PASSO 4: Buscar regras com esses IDs
-- =====================================================

SELECT 
    rt.regra_tributacao_id,
    rt.descricao_regra,
    rt.ativo,
    rt.prioridade,
    
    -- Critérios
    rt.cliente_id,
    rt.regime_tributario_id,
    rt.ncm_id,
    rt.cfop_id,
    rt.uf_origem,
    rt.uf_destino,
    rt.tipo_item,
    
    -- Tributos
    rt.csosn_icms,
    rt.aliquota_icms,
    rt.cst_pis,
    rt.aliquota_pis,
    rt.cst_cofins,
    rt.aliquota_cofins,
    
    -- Diagnóstico
    CASE 
        WHEN rt.ativo = false THEN '❌ INATIVA'
        WHEN rt.cliente_id IS NOT NULL AND rt.cliente_id != 11 THEN '❌ Cliente diferente'
        WHEN rt.regime_tributario_id != 1 THEN '❌ Regime diferente'
        WHEN rt.ncm_id != (SELECT ncm_id FROM ncms WHERE codigo = '85285900') THEN '❌ NCM diferente'
        WHEN rt.cfop_id != (SELECT cfop_id FROM cfops WHERE cfop = '5101') THEN '❌ CFOP diferente'
        WHEN rt.uf_origem IS NOT NULL AND rt.uf_origem != 'SP' THEN '❌ UF Origem diferente'
        WHEN rt.uf_destino IS NOT NULL AND rt.uf_destino != 'SP' THEN '❌ UF Destino diferente'
        WHEN rt.tipo_item IS NOT NULL AND rt.tipo_item != 'PRODUTO' THEN '❌ Tipo Item diferente'
        ELSE '✅ DEVERIA FUNCIONAR!'
    END as diagnostico

FROM regras_tributacao rt
WHERE rt.ativo = true
    AND rt.regime_tributario_id = 1
    AND (rt.cliente_id = 11 OR rt.cliente_id IS NULL)
    AND (rt.ncm_id = (SELECT ncm_id FROM ncms WHERE codigo = '85285900') OR rt.ncm_id IS NULL)
    AND (rt.cfop_id = (SELECT cfop_id FROM cfops WHERE cfop = '5101') OR rt.cfop_id IS NULL)
ORDER BY 
    rt.cliente_id DESC,
    rt.prioridade DESC
LIMIT 10;


-- =====================================================
-- PASSO 5: Ver TODAS as regras do Simples Nacional
-- =====================================================

SELECT 
    rt.regra_tributacao_id,
    rt.descricao_regra,
    rt.ativo,
    rt.cliente_id,
    rt.regime_tributario_id,
    n.codigo as ncm,
    c.cfop as cfop,
    rt.uf_origem,
    rt.uf_destino,
    rt.tipo_item,
    rt.prioridade
FROM regras_tributacao rt
    LEFT JOIN ncms n ON rt.ncm_id = n.ncm_id
    LEFT JOIN cfops c ON rt.cfop_id = c.cfop_id
WHERE rt.regime_tributario_id = 1
    AND rt.ativo = true
ORDER BY rt.prioridade DESC
LIMIT 20;


-- =====================================================
-- PASSO 6: SOLUÇÃO - Criar regra CORINGA se não existir nenhuma
-- =====================================================

-- Esta regra funciona para QUALQUER produto (NCM/CFOP = NULL)
-- Use se não houver nenhuma regra no sistema

/*
INSERT INTO regras_tributacao (
    descricao_regra,
    regime_tributario_id,
    cliente_id,
    ncm_id,
    cfop_id,
    uf_origem,
    uf_destino,
    tipo_item,
    ativo,
    prioridade,
    
    -- Simples Nacional - CSOSN 101
    csosn_icms,
    aliquota_icms,
    reducao_base_icms,
    modalidade_bc_icms,
    
    -- PIS padrão
    cst_pis,
    aliquota_pis,
    
    -- COFINS padrão
    cst_cofins,
    aliquota_cofins,
    
    -- IPI
    cst_ipi,
    aliquota_ipi,
    
    data_inicio_vigencia,
    data_fim_vigencia
)
VALUES (
    'Regra CORINGA - Simples Nacional - Funciona para qualquer produto',
    1,        -- Simples Nacional
    NULL,     -- Qualquer cliente
    NULL,     -- ⭐ Qualquer NCM
    NULL,     -- ⭐ Qualquer CFOP
    NULL,     -- Qualquer UF origem
    NULL,     -- Qualquer UF destino
    NULL,     -- Qualquer tipo (PRODUTO/SERVICO)
    true,     -- Ativa
    1,        -- Prioridade baixa (regras específicas terão prioridade maior)
    
    -- Tributação padrão Simples Nacional
    '101',    -- CSOSN 101 - Tributada com permissão de crédito
    7.00,     -- ICMS 7%
    0.00,     -- Sem redução
    0,        -- Modalidade 0
    
    '01',     -- PIS 01 - Operação Tributável
    1.65,     -- PIS 1.65%
    
    '01',     -- COFINS 01 - Operação Tributável
    7.60,     -- COFINS 7.60%
    
    '99',     -- IPI 99 - Outras saídas
    0.00,     -- IPI 0%
    
    NOW(),    -- Vigência inicia agora
    NULL      -- Sem data fim (sempre válida)
);
*/


-- =====================================================
-- PASSO 7: SOLUÇÃO - Criar regra ESPECÍFICA para este NCM/CFOP
-- =====================================================

-- Primeiro, cadastre o NCM se não existir
/*
INSERT INTO ncms (codigo, descricao, data_inicio_vigencia, data_fim_vigencia)
VALUES ('85285900', 'Outros aparelhos monitores', NOW(), NULL)
ON CONFLICT (codigo) DO NOTHING;
*/

-- Depois, cadastre o CFOP se não existir
/*
INSERT INTO cfops (cfop, descricao, tipo)
VALUES ('5101', 'Venda de produção do estabelecimento', 'SAIDA')
ON CONFLICT (cfop) DO NOTHING;
*/

-- Por fim, crie a regra específica
/*
INSERT INTO regras_tributacao (
    descricao_regra,
    regime_tributario_id,
    cliente_id,
    ncm_id,
    cfop_id,
    uf_origem,
    uf_destino,
    tipo_item,
    ativo,
    prioridade,
    csosn_icms,
    aliquota_icms,
    cst_pis,
    aliquota_pis,
    cst_cofins,
    aliquota_cofins,
    cst_ipi,
    aliquota_ipi,
    data_inicio_vigencia
)
SELECT 
    'Venda Nacional - Simples Nacional - NCM 85285900',
    1,                                          -- Simples Nacional
    NULL,                                       -- Qualquer cliente
    (SELECT ncm_id FROM ncms WHERE codigo = '85285900'),   -- NCM específico
    (SELECT cfop_id FROM cfops WHERE cfop = '5101'),       -- CFOP específico
    NULL,                                       -- Qualquer UF origem
    NULL,                                       -- Qualquer UF destino
    'PRODUTO',                                  -- Apenas produtos
    true,
    10,                                         -- Prioridade alta
    '101',
    7.00,
    '01',
    1.65,
    '01',
    7.60,
    '99',
    0.00,
    NOW();
*/


-- =====================================================
-- PASSO 8: VERIFICAR O RESULTADO
-- =====================================================

-- Simular a busca exata da API
SELECT 
    rt.regra_tributacao_id,
    rt.descricao_regra,
    rt.csosn_icms,
    rt.aliquota_icms,
    rt.cst_pis,
    rt.aliquota_pis,
    rt.cst_cofins,
    rt.aliquota_cofins,
    rt.cst_ipi,
    rt.aliquota_ipi
FROM regras_tributacao rt
WHERE rt.ativo = true
    AND rt.regime_tributario_id = 1
    AND (rt.cliente_id = 11 OR rt.cliente_id IS NULL)
    AND (rt.ncm_id = (SELECT ncm_id FROM ncms WHERE codigo = '85285900') OR rt.ncm_id IS NULL)
    AND (rt.cfop_id = (SELECT cfop_id FROM cfops WHERE cfop = '5101') OR rt.cfop_id IS NULL)
    AND (rt.uf_origem = 'SP' OR rt.uf_origem IS NULL)
    AND (rt.uf_destino = 'SP' OR rt.uf_destino IS NULL)
    AND (rt.tipo_item = 'PRODUTO' OR rt.tipo_item IS NULL)
ORDER BY 
    rt.cliente_id DESC,
    rt.prioridade DESC
LIMIT 1;

-- Se retornar algo aqui, a API vai funcionar! ✅
