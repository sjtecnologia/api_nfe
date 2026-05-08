# 🚀 INSTRUÇÕES DE DEPLOY - Atualização IBS/CBS no Servidor

## 📦 Arquivo Gerado

✅ **atualizacao_ibs_cbs_servidor.tar.gz** (81 KB)

Este arquivo contém tudo que você precisa:
- ✅ Script Python de atualização
- ✅ Script Bash auxiliar  
- ✅ Script de deploy automatizado
- ✅ Documentação completa
- ✅ Arquivo Excel com dados atualizados

---

## 🎯 MÉTODO RÁPIDO (Recomendado)

### 1️⃣ Fazer Upload para o Servidor

```bash
# Do seu computador local
scp atualizacao_ibs_cbs_servidor.tar.gz usuario@servidor:~/api_nfe/
```

### 2️⃣ Conectar ao Servidor

```bash
ssh usuario@servidor
cd ~/api_nfe
```

### 3️⃣ Executar Deploy Automatizado

```bash
# Extrair e executar o script de deploy
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz
chmod +x deploy_ibs_cbs.sh
./deploy_ibs_cbs.sh
```

O script de deploy irá:
- ✅ Verificar todos os arquivos
- ✅ Configurar permissões
- ✅ Verificar dependências Python
- ✅ Instalar pacotes se necessário
- ✅ Perguntar se deseja executar a atualização

### 4️⃣ Pronto! 🎉

---

## 📋 MÉTODO MANUAL (Passo a Passo)

Se preferir controle total, siga estes passos:

### 1. Upload dos Arquivos

```bash
# Do computador local
cd /Users/renato/Documents/Developement/api_nfe
scp atualizacao_ibs_cbs_servidor.tar.gz usuario@IP_SERVIDOR:/caminho/api_nfe/
```

### 2. No Servidor - Descompactar

```bash
ssh usuario@servidor
cd /caminho/api_nfe
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz
```

### 3. Verificar Arquivos Extraídos

```bash
ls -la scripts/atualizar_*
ls -la Documentacao/cClassTrib*
```

Deve ver:
- `scripts/atualizar_ibs_cbs_servidor.py`
- `scripts/atualizar_ibs_cbs.sh`
- `scripts/README_ATUALIZACAO_IBS_CBS.md`
- `Documentacao/cClassTrib 2025-12-12.xlsx`

### 4. Instalar Dependências (se necessário)

```bash
# Verificar se pandas está instalado
python3 -c "import pandas" 2>/dev/null && echo "OK" || echo "FALTA"

# Se faltar, instalar:
pip3 install pandas openpyxl sqlalchemy psycopg2-binary
```

### 5. Tornar Scripts Executáveis

```bash
chmod +x scripts/atualizar_ibs_cbs.sh
chmod +x scripts/atualizar_ibs_cbs_servidor.py
```

### 6. Executar Atualização

```bash
# Opção 1: Com script bash (mais fácil)
./scripts/atualizar_ibs_cbs.sh

# Opção 2: Python direto
python3 scripts/atualizar_ibs_cbs_servidor.py

# Opção 3: Sem confirmação (para automação)
./scripts/atualizar_ibs_cbs.sh --yes
```

---

## 🛡️ Segurança e Backup

### Antes da Atualização

O script **automaticamente**:
- ✅ Cria backup em `backups/classificacoes_ibs_cbs_backup_YYYYMMDD_HHMMSS.sql`
- ✅ Valida estrutura do arquivo Excel
- ✅ Pede confirmação antes de executar

### Backup Manual (Opcional)

```bash
# Fazer dump da tabela antes
pg_dump -U usuario -d banco -t classificacoes_ibs_cbs > backup_manual_ibs_cbs.sql
```

### Restaurar Backup (se necessário)

```bash
# Ver backups disponíveis
ls -la backups/classificacoes_ibs_cbs_backup_*.sql

# Restaurar
psql -U usuario -d banco < backups/classificacoes_ibs_cbs_backup_20251217_091500.sql
```

---

## 📊 O que Será Atualizado

### Dados Atuais → Novos Dados

| Item | Antes | Depois |
|------|-------|--------|
| Total de registros | Varia | **145** |
| Fonte de dados | Antiga | **LC 214/2025** |
| Estrutura de códigos | Varia | **CST-cClassTrib** |
| Alíquotas | Desatualizadas | **Conformes LC 214** |

### Classificações por CST

Após atualização:
- CST 00: Tributação integral (4 classificações)
- CST 10: Alíquotas uniformes (2 classificações)
- CST 11: Reduções de 60% (4 classificações)
- CST 20: Reduções específicas (variadas)
- CST 30-90: Regimes especiais

---

## 📖 Documentação

### Ver Documentação Completa

```bash
cat scripts/README_ATUALIZACAO_IBS_CBS.md
```

### Ver Log da Execução

```bash
# Se executou com redirecionamento
tail -f logs/ibs_cbs_update.log
```

---

## ❓ Troubleshooting

### Problema: "Arquivo Excel não encontrado"

```bash
# Verificar se existe
ls -la "Documentacao/cClassTrib 2025-12-12.xlsx"

# Se não existir, fazer upload novamente
scp "cClassTrib 2025-12-12.xlsx" usuario@servidor:~/api_nfe/Documentacao/
```

### Problema: "ModuleNotFoundError: pandas"

```bash
# Instalar dependências
pip3 install pandas openpyxl sqlalchemy psycopg2-binary

# Ou se tiver requirements.txt
pip3 install -r requirements.txt
```

### Problema: "Permission denied"

```bash
# Dar permissões corretas
chmod +x scripts/atualizar_ibs_cbs.sh
chmod +x deploy_ibs_cbs.sh
```

### Problema: Erro de conexão com banco

```bash
# Verificar conexão
python3 -c "from database.connection import SessionLocal; SessionLocal()"

# Verificar config
cat config/settings.py | grep -i database
```

---

## 🔄 Automatização (Opcional)

### Agendar Atualização Periódica

```bash
# Editar crontab
crontab -e

# Executar toda segunda às 3h
0 3 * * 1 cd /caminho/api_nfe && ./scripts/atualizar_ibs_cbs.sh --yes >> logs/ibs_cbs_cron.log 2>&1

# Executar todo dia 1 do mês
0 2 1 * * cd /caminho/api_nfe && ./scripts/atualizar_ibs_cbs.sh --yes >> logs/ibs_cbs_cron.log 2>&1
```

---

## ✅ Checklist de Validação

Após executar, verificar:

- [ ] Script executou sem erros
- [ ] 145 registros foram inseridos
- [ ] Backup foi criado em `backups/`
- [ ] Consulta funciona: `SELECT COUNT(*) FROM classificacoes_ibs_cbs;`
- [ ] Sistema principal continua funcionando
- [ ] Emissão de NFe funciona com novos cálculos

### Query de Teste

```sql
-- Ver total
SELECT COUNT(*) FROM classificacoes_ibs_cbs;

-- Ver exemplos
SELECT codigo, descricao, aliquota_ibs_uf, aliquota_cbs 
FROM classificacoes_ibs_cbs 
LIMIT 10;

-- Ver com redução
SELECT codigo, aliquota_ibs_uf, aliquota_cbs 
FROM classificacoes_ibs_cbs 
WHERE aliquota_ibs_uf < 0.10 OR aliquota_cbs < 0.90;
```

---

## 📞 Suporte

### Em caso de problemas:

1. ✅ Verificar logs de erro
2. ✅ Verificar backup foi criado
3. ✅ Consultar README completo
4. ✅ Testar restauração do backup
5. ✅ Contatar suporte técnico

### Contatos:
- Documentação: `scripts/README_ATUALIZACAO_IBS_CBS.md`
- Logs: `backups/` e saída do terminal

---

## 📌 Notas Importantes

⚠️ **IMPORTANTE:**
- Sempre teste em ambiente de homologação primeiro
- Faça backup manual antes de executar
- Execute em horário de baixo uso
- Monitore logs após atualização
- Valide cálculos de NFe após atualização

✅ **GARANTIAS:**
- Backup automático antes de qualquer alteração
- Rollback automático em caso de erro
- Validação de dados antes de inserir
- Logs detalhados de toda operação

---

## 🎉 Conclusão

Após seguir este guia, sua tabela IBS/CBS estará atualizada com os dados corretos da LC 214/2025!

**Tempo estimado:** 5-10 minutos
**Downtime:** Nenhum (operação rápida)
**Reversível:** Sim (via backup)
