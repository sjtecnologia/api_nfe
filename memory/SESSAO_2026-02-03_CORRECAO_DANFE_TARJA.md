# Sessão 03/02/2026 - Correção DANFE "SEM VALOR FISCAL"

**Timestamp**: 2026-02-03 13:50  
**Status**: ✅ CORREÇÃO IMPLEMENTADA E DEPLOYED

## 🎯 Problema Identificado

NFe 1155 emitida com sucesso na SEFAZ (protocolo 135260440923497), mas DANFE apresentava tarja "SEM VALOR FISCAL".

### Root Cause
O método `_gerar_xml_protocolo()` em `services/nfe_service.py` estava gerando protocolo com valores simulados/hardcoded:
- ❌ `<tpAmb>2</tpAmb>` hardcoded (homologação) - independente do ambiente real
- ❌ `<digVal>SIMULADO</digVal>` hardcoded
- ❌ `<cStat>AUTORIZADA</cStat>` string ao invés de código numérico

**Impacto**: DANFE library detectava `tpAmb=2` no protocolo e marcava como "SEM VALOR FISCAL", mesmo com NFe autorizada em produção.

## ✅ Solução Implementada

### Arquivo: `services/nfe_service.py` - Método `_gerar_xml_protocolo()`

**Mudanças aplicadas:**

1. **Extração dinâmica do tpAmb** (linhas 1236-1246):
```python
# Extrair tpAmb do XML da NFe para usar no protocolo
tp_amb = '2'  # Padrão: homologação
try:
    tp_amb_element = root.find('.//{http://www.portalfiscal.inf.br/nfe}tpAmb')
    if tp_amb_element is not None and tp_amb_element.text:
        tp_amb = tp_amb_element.text
        print(f"[PROTOCOLO] tpAmb extraído da NFe: {tp_amb} ({'Produção' if tp_amb == '1' else 'Homologação'})")
except:
    print(f"[PROTOCOLO] Não foi possível extrair tpAmb, usando padrão: 2")
```

2. **Valores condicionais baseados em ambiente_real** (linhas 1248-1256):
```python
# Determinar cStat e digVal baseado no ambiente
if resultado.get('ambiente_real'):
    # SEFAZ real retorna cStat como número (100, 150, etc)
    cstat = resultado.get('status', '100') if resultado.get('status', '').isdigit() else '100'
    dig_val = resultado.get('digVal', resultado.get('digest_value', ''))
else:
    # Simulação
    cstat = 'AUTORIZADA'
    dig_val = 'SIMULADO'
```

3. **XML protocolo com valores dinâmicos**:
```python
xml_protocolo = f'''<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
{nfe_xml}
  <protNFe versao="4.00">
    <infProt>
      <tpAmb>{tp_amb}</tpAmb>  <!-- ✅ EXTRAÍDO DA NFE -->
      <verAplic>SP_NFE_PL_008i2</verAplic>
      <chNFe>{resultado.get('chave_acesso', '')}</chNFe>
      <dhRecbto>{resultado.get('data_autorizacao', datetime.now().isoformat())}</dhRecbto>
      <nProt>{resultado.get('protocolo', '')}</nProt>
      <digVal>{dig_val}</digVal>  <!-- ✅ REAL OU SIMULADO CONFORME CONTEXTO -->
      <cStat>{cstat}</cStat>  <!-- ✅ NUMÉRICO PARA PROD -->
      <xMotivo>{resultado.get('mensagem', 'Autorizado o uso da NF-e')}</xMotivo>
    </infProt>
  </protNFe>
</nfeProc>'''
```

## 📋 Deployment

**Comando executado**:
```bash
scp services/nfe_service.py ubuntu@3.87.73.106:/home/ubuntu/api_nfe/services/
ssh ubuntu@3.87.73.106 'sudo systemctl restart api-nfe-principal.service'
```

**Status**: ✅ Serviço reiniciado com sucesso (13:39:28)

## 🧪 Validação

**Próximos testes**:
- Emitir nova NFe e verificar DANFE sem tarja "SEM VALOR FISCAL"
- Protocolo deve ter:
  - `tpAmb=1` (produção)
  - `digVal` com valor real (não "SIMULADO")
  - `cStat=100` (numérico)

## 📝 NFe de Referência

**NFe 1155** (teste com problema):
- Chave: 35260234482371000179550010000011551353320624
- Protocolo: 135260440923497
- Status SEFAZ: ✅ AUTORIZADA
- DANFE: ❌ Tinha tarja (antes da correção)

## 🔄 Histórico da Sessão

1. **13:20** - Identificado tarja no DANFE apesar de autorização válida
2. **13:25** - Corrigido chave de acesso ao XML (xml_nfe_proc → xml_protocolo)
3. **13:30** - Descoberto tpAmb mismatch no protocolo gerado
4. **13:35** - Implementada extração dinâmica de tpAmb e valores condicionais
5. **13:39** - Deploy e restart do serviço
6. **13:50** - Documentação da sessão

## 🎓 Lições Aprendidas

1. **Protocolo nfeProc crítico para DANFE**: tpAmb no protNFe deve sempre coincidir com NFe
2. **ambiente_real flag**: Usar para diferenciar autorizações reais de simuladas
3. **digVal e cStat**: Devem refletir dados reais quando `ambiente_real=True`

## 🔗 Arquivos Relacionados

- `services/nfe_service.py` - Método `_gerar_xml_protocolo()` (linhas 1228-1270)
- `routes/nfe_routes.py` - Geração de DANFE (linha 812)
- `services/nfe_nfelib_service.py` - Geração do XML NFe

## ⚠️ Notas Importantes

- ✅ Correção aplica-se a NOVAS emissões
- ℹ️ NFes antigas (1155) mantêm DANFE com tarja
- 🔄 Regeneração de DANFE de NFes antigas requer consulta SEFAZ + re-processamento

---
**Última atualização**: 2026-02-03 13:50  
**Próxima verificação**: Testar emissão de nova NFe
