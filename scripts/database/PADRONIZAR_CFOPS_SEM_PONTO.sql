-- =====================================================
-- MIGRAÇÃO: Remover pontos dos CFOPs
-- =====================================================
-- Padroniza todos os CFOPs para o formato oficial da Receita Federal (sem ponto)
-- Exemplo: "5.101" → "5101", "6.102" → "6102"
-- =====================================================

-- =====================================================
-- PASSO 1: BACKUP - Ver todos os CFOPs atuais
-- =====================================================

SELECT 
    cfop_id,
    cfop as cfop_antigo,
    REPLACE(cfop, '.', '') as cfop_novo,
    descricao,
    tipo
FROM cfops
ORDER BY cfop;

-- Guarde este resultado como backup antes de prosseguir!


-- =====================================================
-- PASSO 2: Verificar quantos CFOPs serão alterados
-- =====================================================

SELECT 
    COUNT(*) as total_cfops,
    COUNT(CASE WHEN cfop LIKE '%.%' THEN 1 END) as cfops_com_ponto,
    COUNT(CASE WHEN cfop NOT LIKE '%.%' THEN 1 END) as cfops_sem_ponto
FROM cfops;


-- =====================================================
-- PASSO 3: Verificar impacto nas regras de tributação
-- =====================================================

SELECT 
    'Regras afetadas' as info,
    COUNT(DISTINCT rt.regra_tributacao_id) as total_regras,
    COUNT(DISTINCT rt.cfop_id) as cfops_usados
FROM regras_tributacao rt
WHERE rt.cfop_id IS NOT NULL;


-- =====================================================
-- PASSO 4: Verificar impacto nos produtos
-- =====================================================

SELECT 
    'Produtos afetados' as info,
    COUNT(DISTINCT p.produto_id) as total_produtos,
    COUNT(DISTINCT p.cfop_id) as cfops_usados
FROM produtos p
WHERE p.cfop_id IS NOT NULL;


-- =====================================================
-- PASSO 5: Verificar impacto nos itens de NFe
-- =====================================================

SELECT 
    'Itens NFe afetados' as info,
    COUNT(DISTINCT i.item_id) as total_itens,
    COUNT(DISTINCT i.cfop_id) as cfops_usados
FROM itens_nfe i
WHERE i.cfop_id IS NOT NULL;


-- =====================================================
-- PASSO 6: EXECUTAR A MIGRAÇÃO
-- =====================================================

-- ⚠️ ATENÇÃO: Esta operação vai alterar TODOS os CFOPs!
-- ⚠️ Execute os passos anteriores primeiro para verificar o impacto!

BEGIN;

-- Atualizar todos os CFOPs removendo o ponto
UPDATE cfops
SET cfop = REPLACE(cfop, '.', '')
WHERE cfop LIKE '%.%';

-- Verificar resultado
SELECT 
    'Resultado da migração' as info,
    COUNT(*) as total_cfops,
    COUNT(CASE WHEN cfop LIKE '%.%' THEN 1 END) as ainda_com_ponto,
    COUNT(CASE WHEN cfop NOT LIKE '%.%' THEN 1 END) as sem_ponto
FROM cfops;

-- Se estiver tudo OK, execute:
COMMIT;

-- Se algo deu errado, execute:
-- ROLLBACK;


-- =====================================================
-- PASSO 7: VERIFICAR SE FUNCIONOU
-- =====================================================

-- Buscar o CFOP 5101 (agora sem ponto)
SELECT 
    cfop_id,
    cfop,
    descricao,
    tipo
FROM cfops
WHERE cfop = '5101';

-- Deve retornar 1 registro ✅


-- =====================================================
-- PASSO 8: TESTAR A BUSCA DA API (simulação)
-- =====================================================

SELECT 
    '✅ TESTE FINAL' as status,
    (SELECT ncm_id FROM ncms WHERE codigo = '85285900') as ncm_id_encontrado,
    (SELECT cfop_id FROM cfops WHERE cfop = '5101') as cfop_id_encontrado;

-- Ambos devem retornar IDs válidos agora!


-- =====================================================
-- PASSO 9: Buscar regra com os novos dados
-- =====================================================

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
    rt.aliquota_ipi,
    c.cfop,
    n.codigo as ncm
FROM regras_tributacao rt
    LEFT JOIN cfops c ON rt.cfop_id = c.cfop_id
    LEFT JOIN ncms n ON rt.ncm_id = n.ncm_id
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

-- Se não retornar nada, precisa criar uma regra (veja PASSO 10)


-- =====================================================
-- PASSO 10: Criar regra CORINGA se não existir
-- =====================================================

-- Esta regra funciona para QUALQUER NCM/CFOP/UF
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
    'Regra CORINGA - Simples Nacional - Qualquer Produto',
    1,        -- Simples Nacional
    NULL,     -- Qualquer cliente
    NULL,     -- ⭐ Qualquer NCM
    NULL,     -- ⭐ Qualquer CFOP
    NULL,     -- Qualquer UF origem
    NULL,     -- Qualquer UF destino
    NULL,     -- Qualquer tipo
    true,     -- Ativa
    1,        -- Prioridade baixa
    
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
)
ON CONFLICT DO NOTHING;


-- =====================================================
-- PASSO 11: VERIFICAÇÃO FINAL
-- =====================================================

SELECT 
    '✅ MIGRAÇÃO COMPLETA' as status,
    (SELECT COUNT(*) FROM cfops WHERE cfop LIKE '%.%') as cfops_ainda_com_ponto,
    (SELECT COUNT(*) FROM cfops WHERE cfop NOT LIKE '%.%') as cfops_padronizados,
    (SELECT COUNT(*) FROM regras_tributacao WHERE regime_tributario_id = 1 AND ativo = true) as regras_simples_nacional
FROM cfops
LIMIT 1;

-- Se "cfops_ainda_com_ponto" = 0, está tudo OK! ✅
