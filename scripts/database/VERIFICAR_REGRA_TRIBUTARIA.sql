-- =====================================================
-- VERIFICAR SE REGRA TRIBUTÁRIA EXISTE NO BANCO
-- =====================================================
-- Use esta query para verificar se sua regra está cadastrada
-- e se os parâmetros estão corretos
-- =====================================================

-- 1️⃣ PASSO 1: Substitua os valores abaixo pelos dados do seu produto
-- =====================================================

-- Dados do emitente/cliente
SET @cliente_id = 1;                    -- ID do cliente (ou NULL para regras genéricas)
SET @regime_tributario_id = 1;          -- 1=Simples Nacional, 2=Lucro Presumido, 3=Lucro Real

-- Dados do produto
SET @ncm_codigo = '84159090';           -- NCM do produto
SET @cfop_codigo = '5102';              -- CFOP da operação

-- Dados de localização
SET @uf_origem = 'SP';                  -- UF do emitente
SET @uf_destino = 'SP';                 -- UF do destinatário

-- Tipo de item
SET @tipo_item = 'PRODUTO';             -- PRODUTO ou SERVICO


-- 2️⃣ PASSO 2: Execute esta query para buscar regras correspondentes
-- =====================================================

SELECT 
    rt.regra_tributacao_id,
    rt.descricao_regra,
    rt.ativo,
    rt.prioridade,
    
    -- Critérios de busca
    rt.cliente_id,
    rt.regime_tributario_id,
    reg.nome as regime_tributario_nome,
    
    -- NCM e CFOP
    n.codigo as ncm_codigo,
    n.descricao as ncm_descricao,
    c.cfop as cfop_codigo,
    c.descricao as cfop_descricao,
    
    -- UFs
    rt.uf_origem,
    rt.uf_destino,
    rt.tipo_item,
    
    -- Tributos ICMS
    rt.csosn_icms,
    rt.cst_icms,
    rt.aliquota_icms,
    rt.reducao_base_icms,
    rt.modalidade_bc_icms,
    
    -- Tributos PIS
    rt.cst_pis,
    rt.aliquota_pis,
    
    -- Tributos COFINS
    rt.cst_cofins,
    rt.aliquota_cofins,
    
    -- Tributos IPI
    rt.cst_ipi,
    rt.aliquota_ipi,
    
    -- Datas
    rt.data_inicio_vigencia,
    rt.data_fim_vigencia

FROM regras_tributacao rt
    LEFT JOIN regimes_tributarios reg ON rt.regime_tributario_id = reg.regime_tributario_id
    LEFT JOIN ncms n ON rt.ncm_id = n.ncm_id
    LEFT JOIN cfops c ON rt.cfop_id = c.cfop_id

WHERE rt.ativo = true
    -- Cliente: específico do cliente OU regra genérica (NULL)
    AND (rt.cliente_id = @cliente_id OR rt.cliente_id IS NULL)
    
    -- Regime tributário (obrigatório)
    AND rt.regime_tributario_id = @regime_tributario_id
    
    -- NCM (obrigatório se informado)
    AND (n.codigo = @ncm_codigo OR rt.ncm_id IS NULL)
    
    -- CFOP (obrigatório se informado)
    AND (c.cfop = @cfop_codigo OR rt.cfop_id IS NULL)
    
    -- UF Origem (opcional)
    AND (rt.uf_origem = @uf_origem OR rt.uf_origem IS NULL)
    
    -- UF Destino (opcional)
    AND (rt.uf_destino = @uf_destino OR rt.uf_destino IS NULL)
    
    -- Tipo de item (opcional)
    AND (rt.tipo_item = @tipo_item OR rt.tipo_item IS NULL)

-- Ordenar por prioridade (mesma lógica do backend)
ORDER BY 
    rt.cliente_id DESC,  -- Regras específicas do cliente primeiro
    rt.prioridade DESC;  -- Maior prioridade primeiro


-- 3️⃣ PASSO 3: Verificar se há regras cadastradas (mesmo que não batam todos os critérios)
-- =====================================================

SELECT 
    rt.regra_tributacao_id,
    rt.descricao_regra,
    rt.ativo,
    rt.prioridade,
    
    -- Mostrar o que está cadastrado
    rt.cliente_id,
    rt.regime_tributario_id,
    reg.nome as regime_tributario_nome,
    n.codigo as ncm_codigo,
    c.cfop as cfop_codigo,
    rt.uf_origem,
    rt.uf_destino,
    rt.tipo_item,
    
    -- Verificar por que não está batendo
    CASE 
        WHEN rt.ativo = false THEN '❌ Regra INATIVA'
        WHEN rt.cliente_id IS NOT NULL AND rt.cliente_id != @cliente_id THEN '❌ Cliente diferente'
        WHEN rt.regime_tributario_id != @regime_tributario_id THEN '❌ Regime tributário diferente'
        WHEN n.codigo IS NOT NULL AND n.codigo != @ncm_codigo THEN '❌ NCM diferente'
        WHEN c.cfop IS NOT NULL AND c.cfop != @cfop_codigo THEN '❌ CFOP diferente'
        WHEN rt.uf_origem IS NOT NULL AND rt.uf_origem != @uf_origem THEN '❌ UF Origem diferente'
        WHEN rt.uf_destino IS NOT NULL AND rt.uf_destino != @uf_destino THEN '❌ UF Destino diferente'
        WHEN rt.tipo_item IS NOT NULL AND rt.tipo_item != @tipo_item THEN '❌ Tipo Item diferente'
        ELSE '✅ Deveria funcionar!'
    END as motivo

FROM regras_tributacao rt
    LEFT JOIN regimes_tributarios reg ON rt.regime_tributario_id = reg.regime_tributario_id
    LEFT JOIN ncms n ON rt.ncm_id = n.ncm_id
    LEFT JOIN cfops c ON rt.cfop_id = c.cfop_id

WHERE rt.regime_tributario_id = @regime_tributario_id

ORDER BY rt.regra_tributacao_id DESC
LIMIT 20;


-- 4️⃣ PASSO 4: Verificar regimes tributários disponíveis
-- =====================================================

SELECT 
    regime_tributario_id,
    nome,
    codigo
FROM regimes_tributarios
ORDER BY regime_tributario_id;


-- 5️⃣ PASSO 5: Verificar se NCM e CFOP existem
-- =====================================================

-- Verificar NCM
SELECT 
    ncm_id,
    codigo,
    descricao
FROM ncms
WHERE codigo = @ncm_codigo;

-- Verificar CFOP
SELECT 
    cfop_id,
    cfop,
    descricao
FROM cfops
WHERE cfop = @cfop_codigo;


-- 6️⃣ EXEMPLO DE REGRA CORINGA (funciona para qualquer produto)
-- =====================================================

/*
INSERT INTO regras_tributacao (
    descricao_regra,
    regime_tributario_id,
    ativo,
    prioridade,
    
    -- Deixar NULL para ser "coringa" (funciona para qualquer NCM/CFOP)
    ncm_id,
    cfop_id,
    cliente_id,
    uf_origem,
    uf_destino,
    tipo_item,
    
    -- Tributos Simples Nacional
    csosn_icms,
    aliquota_icms,
    
    cst_pis,
    aliquota_pis,
    
    cst_cofins,
    aliquota_cofins,
    
    cst_ipi,
    aliquota_ipi
)
VALUES (
    'Regra Padrão - Simples Nacional (CORINGA)',
    1,  -- Simples Nacional
    true,
    1,  -- Prioridade baixa (regras específicas terão prioridade maior)
    
    -- Tudo NULL = funciona para qualquer produto
    NULL,  -- ncm_id
    NULL,  -- cfop_id
    NULL,  -- cliente_id
    NULL,  -- uf_origem
    NULL,  -- uf_destino
    NULL,  -- tipo_item
    
    -- Tributação padrão Simples Nacional
    '101',  -- CSOSN 101 - Tributada pelo Simples Nacional com permissão de crédito
    7.00,   -- ICMS 7%
    
    '01',   -- CST PIS 01 - Operação Tributável com Alíquota Básica
    1.65,   -- PIS 1.65%
    
    '01',   -- CST COFINS 01 - Operação Tributável com Alíquota Básica
    7.60,   -- COFINS 7.60%
    
    '99',   -- CST IPI 99 - Outras saídas
    0.00    -- IPI 0%
);
*/


-- 7️⃣ DIAGNÓSTICO RÁPIDO
-- =====================================================

-- Contar regras ativas por regime
SELECT 
    rt.regime_tributario_id,
    reg.nome as regime_nome,
    COUNT(*) as total_regras,
    SUM(CASE WHEN rt.cliente_id IS NULL THEN 1 ELSE 0 END) as regras_genericas,
    SUM(CASE WHEN rt.cliente_id IS NOT NULL THEN 1 ELSE 0 END) as regras_especificas
FROM regras_tributacao rt
    LEFT JOIN regimes_tributarios reg ON rt.regime_tributario_id = reg.regime_tributario_id
WHERE rt.ativo = true
GROUP BY rt.regime_tributario_id, reg.nome
ORDER BY rt.regime_tributario_id;
