-- Adicionar campo modelo na tabela nfe_emitidas
ALTER TABLE nfe_emitidas ADD COLUMN IF NOT EXISTS modelo VARCHAR(2);

-- Atualizar registros existentes baseado no tipo_nfe
-- NFe normal = modelo 55
UPDATE nfe_emitidas 
SET modelo = '55' 
WHERE tipo_nfe = '1' OR tipo_nfe = '55';

-- NFCe = modelo 65
UPDATE nfe_emitidas 
SET modelo = '65' 
WHERE tipo_nfe = 'NFCE' OR tipo_nfe = '65';

-- Padronizar tipo_nfe: 0=entrada, 1=saída
-- NFCe é sempre saída (venda ao consumidor)
UPDATE nfe_emitidas 
SET tipo_nfe = '1' 
WHERE tipo_nfe = 'NFCE';

-- Atualizar Destinatários/Tomadores vazios de NFCe para "Consumidor Final"
UPDATE nfe_emitidas 
SET destinatario_razao_social = 'Consumidor Final'
WHERE modelo = '65' 
AND (destinatario_razao_social IS NULL OR destinatario_razao_social = '');

-- Comentário: 
-- tipo_nfe agora representa: 0=Entrada, 1=Saída
-- modelo representa: 55=NFe, 65=NFCe
