# 🔧 CORREÇÃO DO ERRO RNTC - Campo não reconhecido pelo nfelib

## 📋 Problema Identificado

O campo `<RNTC>` (Registro Nacional de Transportador de Carga / ANTT) está presente nos XMLs das NFes 62, 63 e 64, mas o **nfelib 2.2.0** não reconhece esse campo, causando o erro:

```
Unknown property {http://www.portalfiscal.inf.br/nfe}Transp:{http://www.portalfiscal.inf.br/nfe}RNTC
```

Esse erro impede a geração do DANFE oficial, fazendo o sistema cair para o DANFE simplificado.

## ✅ Solução Aplicada

1. **Código corrigido**: O campo `<RNTC>` foi comentado no código (já não é mais gerado nos novos XMLs)
2. **Workaround**: O valor do ANTT agora vai para o campo `<infAdic><infCpl>` (Informações Adicionais)
3. **NFes antigas**: Precisam ter seus XMLs corrigidos no banco de dados

## 🚀 Como Executar a Correção

### No Servidor Windows:

```powershell
# 1. Ativar o ambiente virtual
cd C:\nfe_app
.\venv\Scripts\Activate.ps1

# 2. Executar o script de correção
python fix_rntc_xml.py
```

### O que o script faz:

1. ✅ Busca todas as NFes com campo `<RNTC>` no banco
2. ✅ Remove o campo `<RNTC>` do XML
3. ✅ Move o valor do ANTT para `<infAdic><infCpl>`
4. ✅ Atualiza os XMLs no banco de dados
5. ✅ Faz commit das alterações

### Exemplo de saída esperada:

```
================================================================================
🔧 CORREÇÃO DE XMLs - Remover campo <RNTC>
================================================================================

📋 Encontradas 3 NFe(s) com campo <RNTC> para corrigir:

🔍 NFe ID 62 - Chave: 35251246840224000102...
  ✅ xml_enviado corrigido (RNTC removido)
  ✅ xml_autorizado corrigido (RNTC removido)
  💾 NFe 62 atualizada no banco

🔍 NFe ID 63 - Chave: 35251246840224000102...
  ✅ xml_enviado corrigido (RNTC removido)
  ✅ xml_autorizado corrigido (RNTC removido)
  💾 NFe 63 atualizada no banco

🔍 NFe ID 64 - Chave: 35251246840224000102...
  ✅ xml_enviado corrigido (RNTC removido)
  ✅ xml_autorizado corrigido (RNTC removido)
  💾 NFe 64 atualizada no banco

================================================================================
✅ CONCLUÍDO! 3 NFe(s) processadas com sucesso.
================================================================================
```

## 📊 Verificação

Após executar o script, você pode verificar se as NFes foram corrigidas:

```powershell
# Verificar no banco de dados
psql -U nfe_user -d nfe_db -c "SELECT nfe_emitida_id, chave_acesso FROM nfe_emitidas WHERE xml_enviado LIKE '%<RNTC>%';"

# Resultado esperado: 0 registros
```

## 🎯 Teste Final

Após a correção, teste a geração do DANFE:

1. Acesse: http://192.168.0.52:8080/admin/nfes?cliente_id=11
2. Clique em "Visualizar DANFE" nas NFes 62, 63 ou 64
3. **Resultado esperado**: DANFE oficial gerado com sucesso
4. **Campo ANTT**: Deve aparecer em "Informações Adicionais do Documento Fiscal"

## 📝 Observações

- ✅ **Novas NFes (65, 66)**: Já estão corretas (ANTT em `<infAdic>`)
- ✅ **Código atual**: Não gera mais o campo `<RNTC>`
- ✅ **Compatibilidade**: XML compatível com nfelib 2.2.0
- ⚠️ **SEFAZ**: O campo `<infCpl>` é aceito pela SEFAZ para informações adicionais

## 🔄 Próximos Passos

Caso o nfelib seja atualizado no futuro para suportar `<RNTC>`:

1. Descomentar as linhas 1265-1271 de `services/nfe_service.py`
2. Remover as linhas 1330-1337 (adição ao infAdic)
3. Testar com uma NFe de homologação
4. Atualizar a biblioteca: `pip install --upgrade nfelib`

---

**Última atualização**: 2 de dezembro de 2025  
**Autor**: GitHub Copilot  
**Status**: ✅ Pronto para produção
