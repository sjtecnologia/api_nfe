# 📚 Índice de Documentação - Deploy AWS

**Navegue facilmente por toda a documentação de deploy**

---

## 🎯 Por Onde Começar?

### Nunca fez deploy na AWS?
👉 Comece por: [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md)
- Visão geral completa
- Custos estimados
- Tempo necessário
- O que você vai precisar

### Quer entender tudo em detalhes?
👉 Leia: [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md)
- Guia completo (800+ linhas)
- Explicações detalhadas
- Arquitetura do sistema
- Melhores práticas

### Quer fazer rápido?
👉 Siga: [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md)
- Passo a passo direto
- Comandos prontos
- ~2 horas para deploy completo

### Prefere um checklist para marcar?
👉 Use: [CHECKLIST_DEPLOY_AWS.md](CHECKLIST_DEPLOY_AWS.md)
- Formato imprimível
- Marque cada etapa
- Campos para anotar credenciais

---

## 📖 Documentação Completa

### 1. Guias de Deploy

| Arquivo | Descrição | Quando Usar |
|---------|-----------|-------------|
| [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md) | Visão geral executiva | **Comece aqui!** |
| [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md) | Guia detalhado completo | Deploy com explicações |
| [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md) | Quick start simplificado | Deploy rápido (2h) |
| [CHECKLIST_DEPLOY_AWS.md](CHECKLIST_DEPLOY_AWS.md) | Checklist imprimível | Acompanhar progresso |

### 2. Suporte e Troubleshooting

| Arquivo | Descrição | Quando Usar |
|---------|-----------|-------------|
| [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md) | Resolução de problemas | Quando algo der errado |
| [README_AWS.md](README_AWS.md) | README principal | Navegar arquivos |
| Este arquivo | Índice geral | Encontrar documentação |

### 3. Scripts de Automação

| Arquivo | Descrição | Quando Executar |
|---------|-----------|-----------------|
| [setup_aws_inicial.sh](setup_aws_inicial.sh) | Setup inicial do servidor | Uma vez, após criar EC2 |
| [deploy_aws.sh](deploy_aws.sh) | Deploy da aplicação | Após copiar código |
| [atualizar_codigo_aws.sh](atualizar_codigo_aws.sh) | Atualizar código | Quando houver atualizações |
| [bashrc_aws_aliases.sh](bashrc_aws_aliases.sh) | Aliases e funções úteis | Copiar para ~/.bashrc |

### 4. Configurações

| Arquivo | Descrição | Como Usar |
|---------|-----------|-----------|
| [.env.template.aws](.env.template.aws) | Template de configuração | Copiar e preencher valores |
| [nginx-api-nfe.conf](nginx-api-nfe.conf) | Config Nginx | Copiar para sites-available |
| Arquivos systemd | Services do sistema | Criados pelos scripts |

---

## 🗺️ Fluxo de Trabalho Recomendado

```
1. PREPARAÇÃO
   ├─ Ler RESUMO_EXECUTIVO_AWS.md
   ├─ Criar conta AWS
   └─ Preparar terminal SSH
   
2. INFRAESTRUTURA
   ├─ [AWS Console] Criar RDS PostgreSQL
   └─ [AWS Console] Criar EC2 (t2.large)
   
3. SETUP INICIAL
   ├─ [SSH] Conectar na EC2
   └─ [SSH] Executar setup_aws_inicial.sh
   
4. APLICAÇÃO
   ├─ [SSH] Copiar código (git ou scp)
   ├─ [SSH] Configurar .env
   ├─ [SSH] Migrar banco
   └─ [SSH] Executar deploy_aws.sh
   
5. WEB SERVER
   └─ [SSH] Configurar Nginx
   
6. TESTES
   └─ [Browser] Testar aplicação
   
7. OPCIONAL
   ├─ Configurar domínio
   └─ Instalar SSL (certbot)
```

---

## 🔍 Busca Rápida

### Quero saber sobre...

**Custos:**
- [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md#-custos-estimados) - Estimativas
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-monitoramento-de-custos) - Como monitorar

**RDS (Banco de Dados):**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-1-configurar-rds-postgresql) - Setup completo
- [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md#-problema-rds-não-aceita-conexões) - Problemas

**EC2 (Servidor):**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-2-criar-e-configurar-instância-ec2) - Criar instância
- [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md#2️⃣-criar-ec2) - Passo rápido

**Ollama/IA:**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-4-instalar-lm-studio-cli-mode) - Instalação
- [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md#-problema-ollama-não-responde) - Problemas

**Nginx:**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-8-configurar-nginx-reverse-proxy) - Configuração
- [nginx-api-nfe.conf](nginx-api-nfe.conf) - Arquivo de config

**SSL/HTTPS:**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-9-configurar-domínio-opcional) - Configurar
- [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md#-problema-sslhttps-não-funciona) - Problemas

**Backups:**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-10-configurar-backups-automáticos) - Setup
- [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md#-problema-backup-falha) - Problemas

**Monitoramento:**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-11-monitoramento-e-logs) - Como monitorar
- [bashrc_aws_aliases.sh](bashrc_aws_aliases.sh) - Comandos úteis

**Segurança:**
- [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md#-etapa-13-segurança) - Configurar
- [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md#️-pontos-de-atenção) - Atenção

**Atualização:**
- [atualizar_codigo_aws.sh](atualizar_codigo_aws.sh) - Script de atualização
- [README_AWS.md](README_AWS.md#-scripts-disponíveis) - Como usar

**Problemas:**
- [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md) - **Consulte primeiro!**

---

## 📊 Tabela de Referência Rápida

### Comandos Mais Usados

| Comando | Arquivo de Referência | Seção |
|---------|----------------------|-------|
| `sudo systemctl status` | [bashrc_aws_aliases.sh](bashrc_aws_aliases.sh) | Aliases de Status |
| `sudo journalctl -u` | [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md) | Diagnóstico |
| `psql -h ...` | [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md) | Etapa 1.3 |
| `ssh -i ...` | [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md) | Etapa 2 |
| `sudo nginx -t` | [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md) | Etapa 8.2 |
| `sudo certbot --nginx` | [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md) | Etapa 10 |

### Arquivos de Configuração

| Arquivo | Local no Servidor | Referência |
|---------|------------------|------------|
| `.env` | `/home/ubuntu/api_nfe/.env` | [.env.template.aws](.env.template.aws) |
| Nginx config | `/etc/nginx/sites-available/api-nfe` | [nginx-api-nfe.conf](nginx-api-nfe.conf) |
| Flask service | `/etc/systemd/system/api-nfe-principal.service` | [deploy_aws.sh](deploy_aws.sh) |
| IA service | `/etc/systemd/system/api-nfe-ia.service` | [deploy_aws.sh](deploy_aws.sh) |
| Ollama service | `/etc/systemd/system/ollama.service` | [setup_aws_inicial.sh](setup_aws_inicial.sh) |

### Portas do Sistema

| Serviço | Porta | Config |
|---------|-------|--------|
| Nginx (HTTP) | 80 | [nginx-api-nfe.conf](nginx-api-nfe.conf) |
| Nginx (HTTPS) | 443 | [nginx-api-nfe.conf](nginx-api-nfe.conf) |
| Flask App | 8080 | [deploy_aws.sh](deploy_aws.sh) |
| IA Service | 8081 | [deploy_aws.sh](deploy_aws.sh) |
| Ollama LLM | 1234 | [setup_aws_inicial.sh](setup_aws_inicial.sh) |
| PostgreSQL RDS | 5432 | AWS Console |

---

## 🎓 Níveis de Conhecimento

### Iniciante (Pouca experiência com AWS)
**Recomendação:**
1. Ler [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md) completo
2. Seguir [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md) passo a passo
3. Marcar progresso em [CHECKLIST_DEPLOY_AWS.md](CHECKLIST_DEPLOY_AWS.md)
4. Ter [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md) aberto em outra aba

**Tempo estimado:** 4-5 horas

### Intermediário (Já usou AWS antes)
**Recomendação:**
1. Ler [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md) - seções de custo e arquitetura
2. Seguir [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md)
3. Executar scripts automatizados
4. Consultar [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md) se necessário

**Tempo estimado:** 2-3 horas

### Avançado (DevOps/SysAdmin experiente)
**Recomendação:**
1. Ler [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md) - arquitetura
2. Revisar scripts: [setup_aws_inicial.sh](setup_aws_inicial.sh), [deploy_aws.sh](deploy_aws.sh)
3. Adaptar conforme necessário
4. Executar com suas próprias modificações

**Tempo estimado:** 1-2 horas

---

## 🆘 Preciso de Ajuda!

### Antes do Deploy:
1. Leia [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md)
2. Verifique custos estimados
3. Prepare conta AWS

### Durante o Deploy:
1. Siga [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md) ou [AWS_DEPLOY_COMPLETO.md](AWS_DEPLOY_COMPLETO.md)
2. Marque progresso em [CHECKLIST_DEPLOY_AWS.md](CHECKLIST_DEPLOY_AWS.md)
3. Anote todas as credenciais

### Se Algo Der Errado:
1. **Primeiro:** Consulte [AWS_TROUBLESHOOTING.md](AWS_TROUBLESHOOTING.md)
2. Ver logs: `sudo journalctl -u api-nfe-principal -n 50`
3. Testar manualmente: `cd /home/ubuntu/api_nfe && python app.py`
4. Verificar [CHECKLIST_DEPLOY_AWS.md](CHECKLIST_DEPLOY_AWS.md) - qual etapa?

### Após o Deploy:
1. Verificar [CHECKLIST_DEPLOY_AWS.md](CHECKLIST_DEPLOY_AWS.md) - tudo marcado?
2. Testar aplicação completa
3. Configurar billing alerts
4. Documentar credenciais

---

## 📱 Acesso Rápido Mobile

Salve estes links no seu celular:

- **AWS Console:** https://console.aws.amazon.com/
- **AWS Status:** https://status.aws.amazon.com/
- **AWS Support:** https://console.aws.amazon.com/support/
- **Let's Encrypt Status:** https://letsencrypt.status.io/

---

## 🔖 Marcadores Sugeridos

Adicione nos seus favoritos do navegador:

- **[RESUMO EXECUTIVO]** RESUMO_EXECUTIVO_AWS.md
- **[GUIA COMPLETO]** AWS_DEPLOY_COMPLETO.md
- **[GUIA RÁPIDO]** AWS_GUIA_RAPIDO.md
- **[TROUBLESHOOTING]** AWS_TROUBLESHOOTING.md
- **[AWS Console]** https://console.aws.amazon.com/

---

## 📊 Estatísticas da Documentação

- **Total de arquivos:** 10
- **Total de linhas:** ~3.500+
- **Scripts executáveis:** 4
- **Configurações:** 3
- **Guias:** 5
- **Comandos úteis:** 30+
- **Problemas documentados:** 15+

---

## ✅ Validação Final

Seu deploy está completo quando:
- [ ] Todos os arquivos revisados
- [ ] Scripts testados
- [ ] Aplicação rodando
- [ ] Testes funcionais ok
- [ ] Backups configurados
- [ ] Documentação salva

---

## 🎯 Objetivo Final

Ao final do deploy usando esta documentação, você terá:

✅ Sistema completo rodando na AWS  
✅ IA local funcionando (Ollama)  
✅ Banco de dados seguro (RDS)  
✅ HTTPS configurado  
✅ Backups automáticos  
✅ Monitoramento ativo  
✅ Conhecimento para manter o sistema  

---

## 🚀 Vamos Começar?

**Próximo passo:** [RESUMO_EXECUTIVO_AWS.md](RESUMO_EXECUTIVO_AWS.md)

ou

**Deploy rápido:** [AWS_GUIA_RAPIDO.md](AWS_GUIA_RAPIDO.md)

---

**💡 Dica:** Mantenha este arquivo aberto como referência durante todo o processo!

**📞 Dúvidas?** Consulte [README_AWS.md](README_AWS.md)

**🎉 Boa sorte com seu deploy!**
