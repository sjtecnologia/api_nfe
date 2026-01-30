# Sessão 28/01/2026 - Implementação IA Validação NFe

## Resumo Executivo
Após resolver o Erro 297 (assinatura) com NFe 121 autorizada, implementamos validação de NFe por IA antes da emissão.

---

## Conquistas da Sessão

### 1. NFe 121 AUTORIZADA ✅
- Erro 297 (Assinatura difere do calculado) finalmente resolvido
- Solução: PyNFe com `AssinaturaA1` (não a classe base `Assinatura`)
- IE real usado em homologação
- Nome padrão destinatário em homologação

### 2. Validação IA Implementada ✅
- Botão "Validar com IA" na tela de emissão
- Modal Bootstrap 5 para exibir resultados
- Endpoint FastAPI `/valida/nfe-pre-emissao`
- Rota Flask `/api/llm/validar-nfe`

---

## Arquivos Modificados

### ia_service/main.py
- Novo endpoint: `POST /valida/nfe-pre-emissao`
- Modelo: `ValidacaoNFeRequest` com todos campos da NFe
- Usa GitHub Models GPT-4o-mini
- Retorna: `validacao_ok`, `erros_criticos`, `alertas`, `sugestoes_melhoria`, `score_confianca`

### routes/llm_api_routes.py
- Nova rota: `/api/llm/validar-nfe`
- Proxy para o serviço de IA em `localhost:8081`

### templates/admin/nfes/emitir.html
- Botão "Validar com IA" (linha ~590)
- Modal `#modalValidacaoIA` com Bootstrap 5
- Funções JavaScript:
  - `validarComIA()` - abre modal e chama API
  - `coletarDadosFormulario()` - coleta dados do form
  - `mostrarResultadoValidacao()` - exibe resultado

---

## Problemas Resolvidos

### 1. Modal não fechava
- **Problema**: Usava `data-dismiss` (Bootstrap 4)
- **Solução**: Alterado para `data-bs-dismiss` (Bootstrap 5)

### 2. Seletor de destinatário errado
- **Problema**: Buscava `#destinatario_id`
- **Solução**: ID correto é `#destinatario`

### 3. Seletor de itens errado
- **Problema**: Buscava `#tabelaProdutos` e `[id^="item-card-"]`
- **Solução**: Container é `#itensContainer`, itens são `.card`

### 4. Token GitHub não configurado
- **Problema**: `GITHUB_TOKEN` não estava no .env do servidor
- **Solução**: Adicionado token e reiniciado `api-nfe-ia`

---

## Configurações Importantes

### SSH para Servidor AWS
```bash
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106
```

### Deploy de arquivos
```bash
scp -i ~/Downloads/nfe-new-api-key.pem arquivo ubuntu@3.87.73.106:/home/ubuntu/api_nfe/caminho
```

### Caminhos no servidor
- API principal: `/home/ubuntu/api_nfe/`
- Serviço IA: `/home/ubuntu/api_nfe/ia_service/`
- .env: `/home/ubuntu/api_nfe/.env`

### Serviços systemd
```bash
sudo systemctl restart api-nfe-ia        # Serviço FastAPI (porta 8081)
sudo systemctl restart api-nfe-principal # Serviço Flask (porta 8080)
```

### GITHUB_TOKEN
- Configurado em: `/home/ubuntu/api_nfe/.env`
- Token: `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`
- Usado por: GitHub Models API (GPT-4o-mini)

---

## IDs de Elementos HTML (emitir.html)

| Elemento | ID Correto | ID Errado (antigo) |
|----------|------------|-------------------|
| Destinatário | `destinatario` | `destinatario_id` |
| Container itens | `itensContainer` | `tabelaProdutos` |
| Cards de item | `.card` ou `[id^="item-"]` | `[id^="item-card-"]` |

### Padrão de campos de item
- `produto_N`, `ncm_N`, `cfop_N`, `csosn_N`
- `quantidade_N`, `valor_unitario_N`, `valor_total_N`
- Onde N = 1, 2, 3...

---

## Próximos Passos
1. Testar validação IA completa
2. Remover console.logs de debug
3. Commit e push das alterações

---

## Timestamp
- Última atualização: 2026-01-28 15:05
- Próxima atualização programada: A cada 10 minutos durante a sessão
