# Checklist Rápido - Deploy Seguro (Hotfix Login)

## Execução com 1 comando
- [ ] Rodar: `bash scripts/deploy_login_hotfix_remote.sh`
- [ ] Se necessário, sobrescrever variáveis:
```bash
SSH_KEY="$HOME/Downloads/nfe-new-api-key.pem" \
EC2_HOST="ubuntu@100.26.12.107" \
SERVICE_NAME="api-nfe-principal" \
bash scripts/deploy_login_hotfix_remote.sh
```

## 1. Pré-deploy
- [ ] Confirmar branch e commit que será enviado.
- [ ] Fazer backup remoto dos arquivos-alvo.
- [ ] Validar dependências do código no servidor (evitar importar módulo inexistente em produção).

## 2. Backup remoto (obrigatório)
```bash
ssh -i "$HOME/Downloads/nfe-new-api-key.pem" ubuntu@100.26.12.107 '
BACKUP_DIR=/home/ubuntu/api_nfe/backups/hotfix_$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"
cp /home/ubuntu/api_nfe/routes/auth_routes.py "$BACKUP_DIR"/
cp /home/ubuntu/api_nfe/app.py "$BACKUP_DIR"/
echo "$BACKUP_DIR"
'
```

## 3. Deploy cirúrgico
- [ ] Subir apenas arquivos do hotfix.
- [ ] Evitar sobrescrever arquivo inteiro divergente sem comparar versão remota.

## 4. Restart controlado
```bash
ssh -i "$HOME/Downloads/nfe-new-api-key.pem" ubuntu@100.26.12.107 '
sudo systemctl restart api-nfe-principal
sleep 3
sudo systemctl is-active api-nfe-principal
'
```

## 5. Smoke tests obrigatórios
```bash
# Health interno
curl -i -s http://127.0.0.1:8080/health | head -n 20

# Health público
curl -i -s http://100.26.12.107:8080/health | head -n 20

# 404 não pode virar 500
curl -i -s http://100.26.12.107:8080/rota-que-nao-existe | head -n 20

# Login GET
curl -i -s http://100.26.12.107:8080/auth/login | head -n 20
```

## 6. Verificação funcional do login
- [ ] Testar login com usuário real (Argon2id e legado, se disponível).
- [ ] Confirmar redirecionamento pós-login e sessão ativa.
- [ ] Confirmar que credencial inválida mostra mensagem amigável sem erro interno.

## 7. Observabilidade imediata
```bash
ssh -i "$HOME/Downloads/nfe-new-api-key.pem" ubuntu@100.26.12.107 '
tail -n 120 /home/ubuntu/api_nfe/logs/error.log
'
```
- [ ] Sem traceback novo após tentativa de login real.

## 8. Rollback (se necessário)
```bash
ssh -i "$HOME/Downloads/nfe-new-api-key.pem" ubuntu@100.26.12.107 '
LATEST=$(ls -dt /home/ubuntu/api_nfe/backups/hotfix_* | head -n 1)
cp "$LATEST"/auth_routes.py /home/ubuntu/api_nfe/routes/auth_routes.py
cp "$LATEST"/app.py /home/ubuntu/api_nfe/app.py
sudo systemctl restart api-nfe-principal
'
```

## 9. Critério de sucesso
- [ ] Serviço `active`.
- [ ] `/health` interno e público retornando 200.
- [ ] Login real funcionando.
- [ ] Sem regressão de rotas (404 permanece 404).
