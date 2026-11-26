# Implementação de Cancelamento de NFe via SEFAZ

## 📋 Resumo
Sistema de cancelamento real de NFe enviando evento para SEFAZ conforme layout 4.00.

## ✅ Status: IMPLEMENTADO

Data: 03/02/2026 10:37

## 🔧 Alterações Realizadas

### 1. services/sefaz_service.py
**Novo método `cancelar_nfe()`**

Funcionalidades:
- Cria XML do evento de cancelamento (tpEvento 110111)
- Assina digitalmente o evento com certificado A1
- Envia para SEFAZ via SOAP (serviço NFeRecepcaoEvento4)
- Processa resposta e retorna dados do cancelamento

**Estrutura do XML de Evento:**
```xml
<evento versao="1.00">
  <infEvento Id="ID110111{chave}{nSeq}">
    <cOrgao>35</cOrgao>
    <tpAmb>1</tpAmb>
    <CNPJ>{cnpj_emitente}</CNPJ>
    <chNFe>{chave}</chNFe>
    <dhEvento>{data/hora}</dhEvento>
    <tpEvento>110111</tpEvento>
    <nSeqEvento>1</nSeqEvento>
    <verEvento>1.00</verEvento>
    <detEvento versao="1.00">
      <descEvento>Cancelamento</descEvento>
      <nProt>{protocolo_autorizacao}</nProt>
      <xJust>{justificativa}</xJust>
    </detEvento>
  </infEvento>
</evento>
```

**Códigos de Retorno SEFAZ:**
- `135`: Evento registrado e vinculado (sucesso)
- `136`: Evento já registrado (duplicado)
- `218`: NFe já está cancelada
- `573`: Rejeição por inconsistências

### 2. routes/nfe_routes.py
**Rota `POST /nfe/cancelar/<nfe_id>` atualizada**

Validações implementadas:
- ✅ NFe deve estar com status `AUTORIZADA`
- ✅ Chave de acesso e protocolo devem existir
- ✅ Prazo máximo de 24h após emissão
- ✅ Justificativa mínima de 15 caracteres

Fluxo:
1. Busca NFe no banco com dados do emitente
2. Valida status e prazo
3. Chama `SefazService.cancelar_nfe()`
4. Atualiza banco com dados do cancelamento
5. Retorna resultado para frontend

### 3. database/nfe_emitidas
**Novas colunas adicionadas:**

```sql
ALTER TABLE nfe_emitidas 
  ADD COLUMN protocolo_cancelamento VARCHAR(20),
  ADD COLUMN data_cancelamento TIMESTAMP,
  ADD COLUMN justificativa_cancelamento TEXT,
  ADD COLUMN xml_cancelamento TEXT;
```

## 📊 Campos no Banco de Dados

| Campo | Tipo | Descrição |
|-------|------|-----------|
| protocolo_cancelamento | VARCHAR(20) | Protocolo retornado pela SEFAZ |
| data_cancelamento | TIMESTAMP | Data/hora do registro na SEFAZ |
| justificativa_cancelamento | TEXT | Motivo do cancelamento (mín 15 chars) |
| xml_cancelamento | TEXT | XML completo do procEvento |

## 🔐 Segurança e Assinatura Digital

- Utiliza certificado A1 (PEM) configurado no SefazService
- Assina apenas o elemento `<infEvento>` com Id
- Validação de hash SHA-1 e canonicalização C14N
- Comunicação HTTPS com certificado do cliente

## 🌐 Endpoints SEFAZ

### Produção (tpAmb=1)
```
https://nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx
```

### Homologação (tpAmb=2)
```
https://homologacao.nfe.fazenda.sp.gov.br/ws/nferecepcaoevento4.asmx
```

## 📝 Regras de Negócio

### Prazo de Cancelamento
- **Máximo:** 24 horas após a autorização
- **Verificação:** Compara `data_emissao` com `datetime.now()`
- **Rejeição:** Código 573 se prazo expirado

### Justificativa
- **Mínimo:** 15 caracteres
- **Máximo:** Sem limite (recomendado até 255)
- **Exemplos válidos:**
  - ✅ "Erro no valor do produto, necessário reemitir"
  - ✅ "Cliente solicitou alteração de dados cadastrais"
  - ❌ "Erro" (muito curto)

### Status da NFe
- **Antes:** `AUTORIZADA`
- **Depois:** `CANCELADA`
- **Irreversível:** Não é possível descancelar

## 🧪 Teste de Cancelamento

### Requisição HTTP
```http
POST /nfe/cancelar/257
Content-Type: application/json

{
  "justificativa": "Erro nos dados da transportadora, necessário reemitir com informações corretas"
}
```

### Resposta de Sucesso
```json
{
  "success": true,
  "message": "NFe cancelada com sucesso na SEFAZ",
  "protocolo": "135260437859234",
  "data_cancelamento": "2026-02-03T10:45:12-03:00"
}
```

### Resposta de Erro
```json
{
  "success": false,
  "message": "Erro ao cancelar na SEFAZ: Prazo de cancelamento expirado",
  "codigo": "573"
}
```

## 📂 Arquivos Modificados

```
services/
  └── sefaz_service.py          (+193 linhas - método cancelar_nfe)

routes/
  └── nfe_routes.py              (~150 linhas modificadas)

scripts/
  └── add_cancelamento_columns.py  (novo - migração DB)
```

## 🔄 Fluxo Completo

```
[Frontend] → POST /nfe/cancelar/257
                ↓
[Backend] → Validar status e prazo
                ↓
[SefazService] → Criar XML evento
                ↓
[CertificateService] → Assinar XML
                ↓
[SEFAZ-SP] → Validar e registrar evento
                ↓
[Backend] → Atualizar status no banco
                ↓
[Frontend] ← Retornar resultado
```

## 🚀 Deploy Realizado

1. ✅ Atualizado `services/sefaz_service.py` no servidor
2. ✅ Atualizado `routes/nfe_routes.py` no servidor
3. ✅ Adicionadas colunas na tabela `nfe_emitidas`
4. ✅ Reiniciado serviço `api-nfe-principal.service`
5. ✅ Serviço online em http://3.87.73.106:8080

## ⚠️ Observações Importantes

1. **Prazo de 24h é rigoroso** - SEFAZ rejeita após esse período
2. **Cancelamento é definitivo** - Não há como reverter
3. **Justificativa é obrigatória** - Será armazenada pela SEFAZ
4. **XML de cancelamento deve ser guardado** - Para consultas futuras
5. **Após cancelar, pode emitir nova NFe** - Com mesmo número ou próximo

## 📖 Referências

- Manual de Orientação do Contribuinte NFe v7.0
- Layout 4.00 dos Eventos da NFe
- Nota Técnica 2020.006 - Cancelamento de NFe
- SEFAZ-SP: http://www.nfe.fazenda.sp.gov.br/

## 🎯 Próximos Passos

- [ ] Implementar botão de cancelamento no frontend
- [ ] Adicionar visualização do XML de cancelamento
- [ ] Criar relatório de NFes canceladas
- [ ] Implementar carta de correção (evento 110110)
- [ ] Log de auditoria de cancelamentos
