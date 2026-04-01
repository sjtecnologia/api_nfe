# 🚀 INSTRUÇÕES PARA WINDOWS - Atualização IBS/CBS

## 🪟 MÉTODO WINDOWS (PowerShell)

### Opção 1: Script PowerShell Automatizado (Recomendado)

#### 1. Extrair o arquivo

No Windows Explorer:
- Clique com botão direito em `atualizacao_ibs_cbs_servidor.tar.gz`
- Selecione "Extrair tudo..." ou use 7-Zip/WinRAR

Ou no PowerShell (Windows 10/11):
```powershell
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz
```

#### 2. Executar o deploy

```powershell
# Permitir execução de scripts (apenas primeira vez)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Executar deploy
.\deploy_ibs_cbs_windows.ps1
```

### Opção 2: Comando Direto

```powershell
# Extrair arquivo
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz

# Executar atualização
python scripts\atualizar_ibs_cbs_servidor.py
```

---

## 🛠️ Pré-requisitos Windows

### 1. Python
```powershell
# Verificar se Python está instalado
python --version

# Se não estiver, baixar de:
# https://www.python.org/downloads/
# ⚠️ IMPORTANTE: Marcar "Add Python to PATH"
```

### 2. Dependências Python
```powershell
# Instalar dependências
pip install pandas openpyxl sqlalchemy psycopg2-binary
```

### 3. Ferramenta de Extração
- **Windows 10/11**: Comando `tar` já incluído ✅
- **Windows 7/8**: Instalar [7-Zip](https://www.7-zip.org/)

---

## 📋 Passo a Passo Completo (Windows)

### 1️⃣ Preparar Ambiente

```powershell
# Navegar para diretório do projeto
cd C:\nfe_app

# Verificar Python
python --version

# Instalar dependências se necessário
pip install pandas openpyxl sqlalchemy psycopg2-binary
```

### 2️⃣ Extrair Arquivos

```powershell
# Método 1: Usar tar (Windows 10+)
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz

# Método 2: Usar 7-Zip
7z x atualizacao_ibs_cbs_servidor.tar.gz
7z x atualizacao_ibs_cbs_servidor.tar

# Método 3: Clique direito → Extrair tudo
```

### 3️⃣ Permitir Scripts PowerShell (Primeira Vez)

```powershell
# Verificar política atual
Get-ExecutionPolicy

# Se for "Restricted", mudar para:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Confirmar com "S" (Sim)
```

### 4️⃣ Executar Atualização

**Opção A: Com Script PowerShell**
```powershell
.\deploy_ibs_cbs_windows.ps1
```

**Opção B: Direto com Python**
```powershell
python scripts\atualizar_ibs_cbs_servidor.py
```

**Opção C: Sem confirmação (automação)**
```powershell
python scripts\atualizar_ibs_cbs_servidor.py --yes
```

---

## ⚠️ Problemas Comuns no Windows

### Erro: "tar não é reconhecido"

**Solução 1**: Usar Windows 10 ou superior (tem tar nativo)

**Solução 2**: Instalar 7-Zip
```powershell
# Baixar de: https://www.7-zip.org/
# Depois usar:
7z x atualizacao_ibs_cbs_servidor.tar.gz
7z x atualizacao_ibs_cbs_servidor.tar
```

**Solução 3**: Extrair manualmente
- Clique direito no arquivo
- "Extrair tudo..." ou "Extract here"

### Erro: "Python não é reconhecido"

```powershell
# Verificar se Python está instalado
where python

# Se não aparecer nada, instalar:
# https://www.python.org/downloads/
# ⚠️ Marcar "Add Python to PATH" durante instalação

# Alternativa: usar py launcher
py --version
```

### Erro: "Não é possível carregar o arquivo... não está assinado digitalmente"

```powershell
# Permitir execução de scripts locais
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Ou executar uma vez:
PowerShell -ExecutionPolicy Bypass -File .\deploy_ibs_cbs_windows.ps1
```

### Erro: "ModuleNotFoundError: No module named 'pandas'"

```powershell
# Instalar dependências
pip install pandas openpyxl sqlalchemy psycopg2-binary

# Se pip não funcionar:
python -m pip install pandas openpyxl sqlalchemy psycopg2-binary
```

### Erro: "psycopg2 não compila no Windows"

```powershell
# Usar versão binária pré-compilada
pip install psycopg2-binary

# Se ainda falhar, baixar wheel de:
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#psycopg
```

---

## 🔧 Configurações Específicas Windows

### Caminhos de Arquivo

No Windows, usar barra invertida `\`:
```powershell
python scripts\atualizar_ibs_cbs_servidor.py
Get-Content Documentacao\cClassTrib*.xlsx
```

### Variáveis de Ambiente

```powershell
# Ver Python no PATH
$env:Path -split ';' | Select-String -Pattern 'Python'

# Adicionar Python ao PATH (se necessário)
$env:Path += ";C:\Python311;C:\Python311\Scripts"
```

### PostgreSQL no Windows

Se usar PostgreSQL local no Windows:
```powershell
# Verificar serviço
Get-Service -Name postgresql*

# Iniciar se parado
Start-Service postgresql-x64-14  # Ajustar versão
```

---

## 📊 Exemplo de Execução no Windows

```powershell
PS C:\nfe_app> tar -xzf atualizacao_ibs_cbs_servidor.tar.gz

PS C:\nfe_app> .\deploy_ibs_cbs_windows.ps1

===========================================================
  DEPLOY - Atualização Classificações IBS/CBS (Windows)
===========================================================

📁 Diretório do projeto: C:\nfe_app

📦 Descompactando arquivos...
   Usando tar (Windows 10+)...
✅ Arquivos descompactados

📋 Verificando arquivos...
✅ Todos os arquivos presentes

🐍 Verificando Python...
✅ Python 3.11.5

📦 Verificando dependências Python...
✅ Dependências OK

===========================================================
  ✅ DEPLOY CONCLUÍDO
===========================================================

Deseja executar a atualização agora? (S/N): S

===========================================================
  ATUALIZAÇÃO DE CLASSIFICAÇÕES IBS/CBS
===========================================================

📦 Criando backup dos dados atuais...
✅ Backup salvo

📖 Lendo arquivo Excel...
✅ 145 registros

💾 Salvando alterações...
✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO!
```

---

## 🔒 Backup no Windows

```powershell
# Fazer backup manual antes
pg_dump -U usuario -d banco -t classificacoes_ibs_cbs > backup_manual.sql

# Ver backups automáticos
Get-ChildItem backups\classificacoes_ibs_cbs_backup_*.sql

# Restaurar backup
psql -U usuario -d banco -f backups\classificacoes_ibs_cbs_backup_20251217_091500.sql
```

---

## 🎯 Comandos Rápidos (Windows)

```powershell
# Setup completo em 4 comandos:
cd C:\nfe_app
tar -xzf atualizacao_ibs_cbs_servidor.tar.gz
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\deploy_ibs_cbs_windows.ps1
```

---

## 📞 Suporte Windows

### Ferramentas Úteis

- **Python**: https://www.python.org/downloads/
- **7-Zip**: https://www.7-zip.org/
- **PostgreSQL Windows**: https://www.postgresql.org/download/windows/
- **VS Code**: https://code.visualstudio.com/

### Verificar Instalação

```powershell
# Python
python --version
pip --version

# PostgreSQL
psql --version

# Git (se usar)
git --version
```

---

## ✅ Checklist Windows

- [ ] Python instalado e no PATH
- [ ] Dependências instaladas (pandas, openpyxl, etc)
- [ ] Arquivo .tar.gz extraído
- [ ] ExecutionPolicy configurado
- [ ] Conexão com banco funcionando
- [ ] Script executado sem erros
- [ ] 145 registros inseridos
- [ ] Backup criado em `backups\`

---

## 🔄 Automatização Windows (Task Scheduler)

```powershell
# Criar tarefa agendada
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\nfe_app\scripts\atualizar_ibs_cbs_servidor.py --yes"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 3am
Register-ScheduledTask -TaskName "Atualizar_IBS_CBS" -Action $action -Trigger $trigger
```

---

## 💡 Dicas Windows

1. ✅ Use PowerShell (não CMD)
2. ✅ Execute como Administrador se houver erros de permissão
3. ✅ Verifique antivírus (pode bloquear scripts)
4. ✅ Use caminhos completos se houver problemas
5. ✅ Teste conexão com banco antes de executar

---

Pronto! Agora você consegue executar no Windows! 🪟✅
