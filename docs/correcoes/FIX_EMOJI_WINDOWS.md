# 🔧 CORREÇÃO DO ERRO DE EMOJI NO WINDOWS

## ❌ Problema Identificado

```
ERRO: Erro ao listar NFes: 'charmap' codec can't encode character '\U0001f4e5' in position 0: character maps to <undefined>
```

**Causa**: O Windows console usa o codec `charmap` (cp1252) por padrão, que não suporta emojis Unicode (caracteres > U+1F000).

## ✅ Soluções

### Solução 1: Usar wrapper UTF-8 (RECOMENDADO)

1. **Copie o arquivo `run_app_utf8.py` para o servidor**

2. **Reconfigure o serviço NSSM** (como Administrador):

```powershell
# Parar o serviço
nssm stop NFe_Backend

# Reconfigurar para usar o wrapper
nssm set NFe_Backend Application "C:\nfe_app\venv\Scripts\python.exe"
nssm set NFe_Backend AppParameters "C:\nfe_app\run_app_utf8.py"

# Definir diretório de trabalho
nssm set NFe_Backend AppDirectory "C:\nfe_app"

# Configurar encoding UTF-8
nssm set NFe_Backend AppEnvironmentExtra "PYTHONIOENCODING=utf-8"

# Reiniciar o serviço
nssm start NFe_Backend
```

3. **Verificar se funcionou**:

```powershell
# Ver logs
Get-Content C:\nfe_app\logs\service.log -Tail 50

# Testar no navegador
Start-Process "http://localhost:8080/health"
```

### Solução 2: Configurar variável de ambiente (ALTERNATIVA)

Se não quiser usar o wrapper, configure apenas a variável de ambiente:

```powershell
# Parar o serviço
nssm stop NFe_Backend

# Adicionar variável de ambiente
nssm set NFe_Backend AppEnvironmentExtra "PYTHONIOENCODING=utf-8"

# Reiniciar
nssm start NFe_Backend
```

### Solução 3: Modificar código NSSM atual (SEM MUDANÇAS)

Se o serviço já estiver configurado com `app.py`, adicione apenas a variável:

```powershell
nssm set NFe_Backend AppEnvironmentExtra "PYTHONIOENCODING=utf-8"
nssm restart NFe_Backend
```

## 📊 Verificação

Após aplicar a solução, verifique:

```powershell
# 1. Status do serviço
nssm status NFe_Backend
# Resultado esperado: SERVICE_RUNNING

# 2. Logs recentes
Get-Content C:\nfe_app\logs\service.log -Tail 20
# Deve mostrar: [INFO] Encoding UTF-8 configurado para Windows

# 3. Teste de login
Invoke-WebRequest -Uri "http://localhost:8080/auth/login" -Method GET
# Resultado esperado: StatusCode 200
```

## 🎯 Resultado Esperado

Após a correção:
- ✅ Login funciona sem erro 500
- ✅ Dashboard carrega corretamente
- ✅ Lista de NFes exibe sem erros
- ✅ Emojis aparecem como texto ASCII (ex: `[OK]`, `[ERROR]`, `[USER]`)
- ✅ Logs não causam crash por encoding

## 🔍 Debug

Se ainda houver problemas:

```powershell
# Ver configuração atual do NSSM
nssm dump NFe_Backend

# Ver variáveis de ambiente
nssm get NFe_Backend AppEnvironmentExtra

# Testar Python diretamente
cd C:\nfe_app
.\venv\Scripts\python.exe run_app_utf8.py
# Ctrl+C para parar
```

## 📝 Notas

- **Wrapper `run_app_utf8.py`**: Força UTF-8 em stdout/stderr antes de carregar o app
- **PYTHONIOENCODING**: Variável global do Python para encoding de I/O
- **Emojis**: Continuam no código, mas são tratados corretamente pelo wrapper
- **Compatibilidade**: Funciona em Windows Server 2012+, Windows 10+

---

**Status**: ✅ Solução testada e aprovada  
**Última atualização**: 3 de dezembro de 2025
