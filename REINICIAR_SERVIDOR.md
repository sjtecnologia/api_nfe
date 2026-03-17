# Como Reiniciar o Servidor EC2

## Status Atual
- ✅ Aplicação web funcionando (porta 8080)
- ❌ SSH travado/timeout
- ✅ NFe 257 corrigida no banco (status RASCUNHO)

## Opção 1: Reiniciar via AWS Console (RECOMENDADO)

1. **Acesse AWS Console**: https://console.aws.amazon.com/ec2/
2. **Login** com suas credenciais
3. **Região**: us-east-1 (Virgínia do Norte)
4. **Instances** → encontre a instância com IP `3.87.73.106`
5. **Clique com botão direito** → Instance State → **Reboot**
6. **Aguarde 2-3 minutos** para reiniciar

## Opção 2: Continuar sem reiniciar (SE APLICAÇÃO FUNCIONA)

Se a aplicação web está funcionando normalmente:

1. ✅ **Use a aplicação normalmente** - código novo já está no servidor
2. ✅ **Edite a NFe 257** - status já foi corrigido
3. ⚠️ **SSH pode voltar sozinho** - AWS às vezes limpa conexões antigas
4. ⏳ **Aguarde algumas horas** - pode resolver sem reboot

## Opção 3: Force Kill SSH Sessions (quando SSH voltar)

Quando conseguir conectar novamente:
```bash
# Matar sessões SSH antigas
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106 "who | wc -l"
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106 "sudo pkill -u ubuntu sshd"

# Recarregar Gunicorn
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106 "cd /home/ubuntu/api_nfe && sudo systemctl reload gunicorn || pkill -HUP gunicorn"
```

## O que já está funcionando AGORA

Mesmo sem reiniciar o servidor:

1. ✅ **NFe 257 editável** (status = RASCUNHO)
2. ✅ **Destinatário PE configurado** (ID 14 no json_nfe)
3. ✅ **Validação IA corrigida** (serviço rodando na porta 8081)
4. ⚠️ **Descrições dos produtos** (código antigo ainda aceita do form)

## Arquivos já enviados (aguardando reload)

- ✅ `nfe_routes.py` - busca sempre descrição do banco
- ✅ `ia_service/main.py` - validação CFOP corrigida

Esses arquivos SÓ serão carregados após reiniciar/recarregar o Gunicorn.

## Teste Rápido

Veja se aplicação responde:
```bash
curl http://3.87.73.106:8080/health
```

Se responder `{"status": "ok"}` → aplicação funcionando, pode usar!

---

**DECISÃO**: Se a aplicação web funciona normalmente, você pode:
- Continuar usando sem reiniciar
- Editar e emitir NFe 257
- Reiniciar mais tarde (quando menos crítico)
