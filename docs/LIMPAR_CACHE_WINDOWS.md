# Como Limpar Cache Python no Windows Server

## 🎯 Quando usar

- Depois de atualizar arquivos `.py` (especialmente `models/user.py`, `auth/decorators.py`)
- Menu não aparece após mudanças
- Comportamento estranho após deploy
- Mudanças de código não refletem no sistema

---

## 🚀 Método 1: Script Batch (Mais Simples)

### Passo a passo:

1. **Copie o arquivo** `scripts/limpar_cache_windows.bat` para o servidor

2. **Abra o Command Prompt como Administrador:**
   - Pressione `Win + X`
   - Selecione "Command Prompt (Admin)" ou "PowerShell (Admin)"

3. **Navegue até o diretório do projeto:**
   ```cmd
   cd C:\caminho\para\api_nfe
   ```

4. **Execute o script:**
   ```cmd
   scripts\limpar_cache_windows.bat
   ```

5. **Reinicie o serviço Flask:**
   ```cmd
   net stop api_nfe_principal
   net start api_nfe_principal
   ```

---

## 🔥 Método 2: PowerShell (Mais Moderno)

### Passo a passo:

1. **Copie o arquivo** `scripts/limpar_cache_windows.ps1` para o servidor

2. **Abra o PowerShell como Administrador:**
   - Pressione `Win + X`
   - Selecione "Windows PowerShell (Admin)"

3. **Navegue até o diretório do projeto:**
   ```powershell
   cd C:\caminho\para\api_nfe
   ```

4. **Execute o script:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\limpar_cache_windows.ps1
   ```

5. **Reinicie o serviço Flask:**
   ```powershell
   Restart-Service api_nfe_principal
   ```

---

## ⚡ Método 3: Comandos Manuais Rápidos

### No Command Prompt (como Admin):

```cmd
cd C:\caminho\para\api_nfe

REM Limpar .pyc
for /r %i in (*.pyc) do del /q "%i"

REM Limpar __pycache__
for /d /r %i in (__pycache__) do rd /s /q "%i"

REM Reiniciar serviço
net stop api_nfe_principal && net start api_nfe_principal
```

### No PowerShell (como Admin):

```powershell
cd C:\caminho\para\api_nfe

# Limpar .pyc
Get-ChildItem -Filter *.pyc -Recurse | Remove-Item -Force

# Limpar __pycache__
Get-ChildItem -Filter __pycache__ -Directory -Recurse | Remove-Item -Recurse -Force

# Reiniciar serviço
Restart-Service api_nfe_principal
```

---

## 🔧 Método 4: Interface Gráfica (Services.msc)

Se preferir usar a interface gráfica:

1. **Limpe o cache** usando um dos métodos acima

2. **Abra Services:**
   - Pressione `Win + R`
   - Digite: `services.msc`
   - Pressione Enter

3. **Encontre o serviço:**
   - Procure por `api_nfe_principal`

4. **Reinicie o serviço:**
   - Clique com botão direito no serviço
   - Selecione "Restart"

---

## 🎯 Método 5: Limpar Cache Específico (Mais Rápido)

Se souber qual módulo mudou, limpe apenas ele:

### Para mudanças em `models/user.py`:

```cmd
cd C:\caminho\para\api_nfe
rd /s /q models\__pycache__
del /q models\*.pyc
net stop api_nfe_principal && net start api_nfe_principal
```

### Para mudanças em `auth/decorators.py`:

```cmd
cd C:\caminho\para\api_nfe
rd /s /q auth\__pycache__
del /q auth\*.pyc
net stop api_nfe_principal && net start api_nfe_principal
```

---

## ⚠️ Verificação de Permissões

Se receber erro de permissão:

1. **Verifique se está executando como Administrador**

2. **Verifique se o serviço está parado:**
   ```cmd
   net stop api_nfe_principal
   ```

3. **Limpe o cache**

4. **Inicie o serviço:**
   ```cmd
   net start api_nfe_principal
   ```

---

## 🔍 Verificar se o Cache foi Limpo

Após limpar, verifique:

```cmd
cd C:\caminho\para\api_nfe

REM Verificar se ainda existem arquivos .pyc
dir /s /b *.pyc

REM Verificar se ainda existem __pycache__
dir /s /b __pycache__
```

Se não retornar nenhum resultado, o cache foi limpo com sucesso! ✅

---

## 🐛 Troubleshooting

### Problema: Menu ainda não aparece após limpar cache

**Soluções:**

1. **Verifique o usuário no banco:**
   ```sql
   SELECT u.username, r.name 
   FROM users u 
   JOIN user_roles ur ON u.id = ur.user_id 
   JOIN roles r ON ur.role_id = r.id 
   WHERE u.username = 'seu_usuario';
   ```
   - O role deve ser exatamente `Super_Admin` (com S e A maiúsculos)

2. **Verifique o arquivo models/user.py:**
   ```python
   def is_super_admin(self):
       return any(role.get('name', '') == 'Super_Admin' for role in self.roles)
   ```
   - Deve comparar com `'Super_Admin'` (não `'super_admin'`)
   - NÃO deve usar `.lower()`

3. **Faça logout e login novamente** no sistema

4. **Limpe o cache do navegador:**
   - Pressione `Ctrl + Shift + Delete`
   - Limpe cache e cookies
   - Ou use navegação anônima

5. **Verifique os logs da aplicação:**
   ```cmd
   type logs\app.log | findstr "ERROR"
   ```

### Problema: Erro ao reiniciar o serviço

```cmd
REM Verificar status do serviço
sc query api_nfe_principal

REM Forçar parada
sc stop api_nfe_principal
timeout /t 5
sc start api_nfe_principal
```

---

## 📝 Checklist Completo

Após fazer mudanças em `models/user.py` ou `auth/decorators.py`:

- [ ] Copiar arquivos atualizados para o servidor
- [ ] Parar o serviço Flask
- [ ] Limpar cache Python (todos os .pyc e __pycache__)
- [ ] Verificar se cache foi limpo (dir *.pyc deve estar vazio)
- [ ] Iniciar o serviço Flask
- [ ] Fazer logout no navegador
- [ ] Fazer login novamente
- [ ] Verificar se menu "Planos e Assinaturas" aparece

---

## 🎓 Dica Extra: Criar Arquivo .bat Permanente

Crie um arquivo `restart_service.bat` no servidor para facilitar:

```batch
@echo off
echo Parando servico...
net stop api_nfe_principal

echo Limpando cache...
for /r %~dp0 %%i in (*.pyc) do del /q "%%i"
for /d /r %~dp0 %%i in (__pycache__) do rd /s /q "%%i"

echo Iniciando servico...
net start api_nfe_principal

echo Pronto!
pause
```

Salve no diretório do projeto e execute sempre que fizer deploy! 🚀
