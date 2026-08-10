# Operacao IA - Monitoramento e Healthcheck

Este guia consolida a operacao da infraestrutura de IA (microservico 8081 + app principal 8080), com foco em verificacao rapida e resposta a incidentes.

## 1. Checklist rapido (manual)

### Servidor EC2

```bash
sudo systemctl is-active api-nfe-ia.service
sudo systemctl is-active api-nfe-principal.service
```

Ambos devem retornar `active`.

### Endpoints criticos

```bash
curl -s -X POST http://127.0.0.1:8081/sugestao \
  -H "Content-Type: application/json" \
  -d '{"descricao":"Caneta","tipo_item":"Produto","unidade_comercial":"UN"}'

curl -s -X POST http://127.0.0.1:8081/valida/regra \
  -H "Content-Type: application/json" \
  -d '{"regime_tributario":"Simples Nacional","cfop":"5102","csosn_icms":"102","ncm":"96081000","descricao":"Caneta"}'
```

Ambos devem responder HTTP 200.

## 2. Script de healthcheck

Script versionado:

- `scripts/healthcheck_ia.sh`

### Uso local

```bash
./scripts/healthcheck_ia.sh --mode local
```

### Uso remoto

```bash
./scripts/healthcheck_ia.sh --mode remote \
  --remote-host ubuntu@100.26.12.107 \
  --ssh-key ~/Downloads/nfe-new-api-key.pem
```

## 3. Cron no EC2

Entrada recomendada (a cada 5 minutos):

```cron
*/5 * * * * /home/ubuntu/api_nfe/scripts/healthcheck_ia.sh --mode local >> /home/ubuntu/api_nfe/logs/healthcheck_ia.log 2>&1
```

Verificacao:

```bash
crontab -l | grep healthcheck_ia.sh
```

Log:

```bash
tail -n 50 /home/ubuntu/api_nfe/logs/healthcheck_ia.log
```

## 4. Diagnostico rapido de falhas

### 401 no /sugestao

Causa comum: `AI_PROVIDER_API_KEY` invalida/expirada.

Acao:

1. Rotacionar chave na OpenAI.
2. Atualizar `.env`.
3. Reiniciar `api-nfe-ia.service` e `api-nfe-principal.service`.

### Worker failed to boot no principal

Causa comum: drift entre codigo e ambiente (imports/arquivos ausentes).

Acao:

1. Verificar `/home/ubuntu/api_nfe/logs/error.log`.
2. Confirmar arquivos deployados.
3. Reiniciar servico apos correcao.

### Timeout em /sugestao

Causa comum: indisponibilidade externa de provider ou rede.

Acao:

1. Validar saida para internet no host.
2. Confirmar `AI_PROVIDER_URL` e `AI_PROVIDER_TIMEOUT_SECONDS`.

## 5. Verificacao pelo Admin

Tela de validacao sem tocar no fluxo fiscal:

- `Admin > Teste de IA`
- Conferir:
  - Status de configuracao
  - Prompts
  - Previa de prompt
  - Saude operacional
