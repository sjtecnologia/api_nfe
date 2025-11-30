# 🔄 Atualização Windows Server - DANFE Debug Logs

## ✅ O QUE FOI FEITO

1. ✅ Habilitada biblioteca `nfelib==2.2.0` em requirements.txt
2. ✅ Adicionados logs detalhados em `services/danfe_service.py`
3. ✅ Corrigidos erros de navegação (cliente_id) em 3 locais
4. ✅ Código commitado no Git (commit `f0f928d`)

## 📋 ROTEIRO DE ATUALIZAÇÃO NO WINDOWS SERVER

### PASSO 1: Conectar ao Servidor

```powershell
# Via PowerShell local:
ssh Administrator@192.168.15.18

# Ou via Remote Desktop + PowerShell
```

### PASSO 2: Parar o Serviço

```powershell
cd C:\nfe_app
.\nssm.exe stop NFe_Backend
```

**Resultado Esperado**:
```
NFe_Backend: STOP: A operação foi concluída com êxito.
```

### PASSO 3: Fazer Backup (Opcional mas Recomendado)

```powershell
# Backup dos arquivos que serão alterados
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item services\danfe_service.py "services\danfe_service.py.backup_$timestamp"
Copy-Item requirements.txt "requirements.txt.backup_$timestamp"
Copy-Item routes\admin_routes.py "routes\admin_routes.py.backup_$timestamp"
Copy-Item templates\cliente\resumo.html "templates\cliente\resumo.html.backup_$timestamp"

Write-Host "✅ Backup concluído: $timestamp" -ForegroundColor Green
```

### PASSO 4: Atualizar Código do Git

```powershell
# Atualizar branch
git fetch origin
git pull origin copilot/vscode1759248218459
```

**Resultado Esperado**:
```
From https://github.com/seu-repo/api_nfe
   5ede726..f0f928d  copilot/vscode1759248218459 -> origin/copilot/vscode1759248218459
Updating 5ede726..f0f928d
Fast-forward
 services/danfe_service.py | 25 +++++++++++++++++++++----
 requirements.txt          |  8 ++++----
 routes/admin_routes.py    | 15 ++++++++++-----
 templates/cliente/resumo.html | 2 +-
 4 files changed, 36 insertions(+), 14 deletions(-)
```

### PASSO 5: Verificar Commit Aplicado

```powershell
git log --oneline -1
```

**Deve Mostrar**:
```
f0f928d fix: Add debug logs for DANFE generation and enable nfelib
```

### PASSO 6: Reiniciar o Serviço

```powershell
.\nssm.exe start NFe_Backend
```

**Resultado Esperado**:
```
NFe_Backend: START: A operação foi concluída com êxito.
```

### PASSO 7: Aguardar Inicialização (10 segundos)

```powershell
Start-Sleep -Seconds 10
```

### PASSO 8: Verificar Status do Serviço

```powershell
.\nssm.exe status NFe_Backend
```

**Resultado Esperado**:
```
SERVICE_RUNNING
```

### PASSO 9: Monitorar Logs Iniciais

```powershell
Get-Content C:\nfe_app\logs\service.log -Tail 30
```

**O que Procurar**:
```
nfelib carregado com sucesso
SefazService carregado com sucesso
OK: Serviços locais carregados com sucesso
=== ROTAS REGISTRADAS ===
...
* Running on http://0.0.0.0:5000
```

## 🧪 TESTE DA FUNCIONALIDADE

### PASSO 10: Abrir Segunda Sessão PowerShell para Logs em Tempo Real

**Em outra janela PowerShell no servidor**:

```powershell
cd C:\nfe_app
Get-Content C:\nfe_app\logs\service.log -Wait -Tail 50
```

**Deixe esta janela aberta para ver os logs em tempo real.**

### PASSO 11: Testar Geração de DANFE

#### No Navegador:

1. Acesse: `http://192.168.15.18:5000`
2. Login: `admin` (ou usuário configurado)
3. Menu: **NFes** → **Listar NFes**
4. Escolha uma NFe com status "AUTORIZADA"
5. Clique em "Visualizar"
6. Clique em "**Gerar DANFE**"

#### Na Janela de Logs (PowerShell #2):

**Você DEVE ver algo assim**:

```
2025-11-30 14:30:45 - services.danfe_service - INFO - 🔍 [MÉTODO 1] Iniciando tentativa com nfelib
2025-11-30 14:30:45 - services.danfe_service - INFO - 🔍 Verificando se nfelib está instalada...
2025-11-30 14:30:45 - services.danfe_service - INFO - ✅ nfelib está instalada, chamando generate_danfe_nfelib()
2025-11-30 14:30:45 - services.danfe_service - INFO - 🚀 [NFELIB] Iniciando generate_danfe_nfelib
2025-11-30 14:30:45 - services.danfe_service - INFO -    xml_content type: <class 'str'>, size: 4523
2025-11-30 14:30:45 - services.danfe_service - INFO -    output_pdf_path: C:\nfe_app\static\danfe\danfe_45.pdf
2025-11-30 14:30:45 - services.danfe_service - INFO - 📄 [NFELIB] Processando como NFe (modelo 55)
2025-11-30 14:30:45 - services.danfe_service - INFO - 📚 Tentando importar bindings v4.0...
```

### PASSO 12: Analisar Resultado

#### ✅ CENÁRIO 1: SUCESSO (MELHOR CASO)

**Logs mostram**:
```
✅ Bindings v4.0 carregados com sucesso
🔄 Iniciando parse do XML...
✅ NFe carregada do XML com sucesso
🔄 Gerando PDF...
🔄 Tentando engine padrão
✅ PDF gerado com engine padrão
✅ DANFE nfelib gerado com sucesso: C:\nfe_app\static\danfe\danfe_45.pdf
📊 Tamanho do arquivo: 15234 bytes
🎉 DANFE oficial gerado com sucesso usando nfelib
```

**Ação**: Problema resolvido! Abrir o PDF e confirmar que é o DANFE oficial (não diz "SIMPLIFICADO").

---

#### ⚠️ CENÁRIO 2: FALLBACK PARA V3.1 (ACEITÁVEL)

**Logs mostram**:
```
📚 Tentando importar bindings v4.0...
⚠️ Bindings v4.0 não disponíveis, tentando v3.1...
✅ Bindings v3.1 carregados com sucesso
[... resto do processo com sucesso]
```

**Ação**: Funcional, mas subótimo. Considerar atualizar nfelib ou instalar: `pip install nfelib[pdf]`

---

#### ❌ CENÁRIO 3: ERRO NO PARSE DO XML

**Logs mostram**:
```
🔄 Iniciando parse do XML...
❌ Erro ao fazer parse do XML: [mensagem de erro detalhada]
❌ generate_danfe_nfelib retornou False
```

**Ações Corretivas**:

```powershell
# 1. Verificar encoding do XML (deve ser UTF-8)
# 2. Verificar se xsdata está instalado:
C:\nfe_app\venv\Scripts\activate
pip list | Select-String xsdata

# Se não estiver instalado:
pip install xsdata==25.7

# Reiniciar serviço:
deactivate
cd C:\nfe_app
.\nssm.exe restart NFe_Backend
```

---

#### ❌ CENÁRIO 4: ERRO NA GERAÇÃO DO PDF

**Logs mostram**:
```
🔄 Gerando PDF...
🔄 Tentando engine padrão (None)
⚠️ Engine padrão falhou: [erro]
🔄 Tentando BrazilFiscalReport engine
⚠️ BrazilFiscalReport falhou: [erro]
🔄 Tentando erpbrasil.edoc.pdf engine
❌ Todos os engines de PDF falharam
```

**Ações Corretivas**:

```powershell
# Instalar dependências de PDF:
C:\nfe_app\venv\Scripts\activate
pip install reportlab brazilnum

# Ou instalar nfelib com suporte completo:
pip install nfelib[pdf]

# Reiniciar:
deactivate
cd C:\nfe_app
.\nssm.exe restart NFe_Backend
```

---

#### ❌ CENÁRIO 5: ARQUIVO NÃO SALVA

**Logs mostram**:
```
✅ PDF gerado com engine padrão
❌ Erro ao salvar arquivo: [PermissionError ou IOError]
```

**Ações Corretivas**:

```powershell
# Verificar permissões do diretório:
icacls C:\nfe_app\static\danfe

# Se necessário, dar permissões:
icacls C:\nfe_app\static\danfe /grant "SYSTEM:(OI)(CI)F" /T
icacls C:\nfe_app\static\danfe /grant "Administrators:(OI)(CI)F" /T

# Verificar se diretório existe:
if (-not (Test-Path C:\nfe_app\static\danfe)) {
    New-Item -ItemType Directory -Path C:\nfe_app\static\danfe
}
```

---

#### ❌ CENÁRIO 6: NÃO CHEGA NO MÉTODO 1

**Logs NÃO mostram**:
```
🔍 [MÉTODO 1] Iniciando tentativa com nfelib
```

**Ação Corretiva**:

```powershell
# Verificar se há erros antes:
Get-Content C:\nfe_app\logs\service.log -Tail 100 | Select-String "ERROR|Exception|Traceback"

# Verificar se requirements.txt foi atualizado:
Get-Content C:\nfe_app\requirements.txt | Select-String "nfelib"

# Deve mostrar (sem #):
# nfelib==2.2.0

# Se estiver comentado, fazer pull novamente:
git status
git pull origin copilot/vscode1759248218459
.\nssm.exe restart NFe_Backend
```

## 📊 CHECKLIST DE VALIDAÇÃO

Após os testes, marque os itens:

- [ ] Serviço reiniciou sem erros
- [ ] Logs mostram "🔍 [MÉTODO 1] Iniciando..."
- [ ] Logs mostram "✅ nfelib está instalada"
- [ ] Logs mostram "🚀 [NFELIB] Iniciando generate_danfe_nfelib"
- [ ] Logs mostram "✅ PDF gerado com sucesso"
- [ ] PDF abriu corretamente no navegador
- [ ] PDF NÃO contém texto "DANFE - SIMPLIFICADO"
- [ ] PDF contém layout oficial SEFAZ (campos completos)

## 🎉 SUCESSO CONFIRMADO

**Se todos os checkboxes acima estiverem marcados:**

1. ✅ O problema está resolvido!
2. ✅ Sistema gerando DANFE oficial com nfelib
3. ✅ Conformidade com requisitos SEFAZ garantida

## 🔄 SE AINDA HOUVER PROBLEMAS

**Copiar e Colar no Chat:**

```
LOGS OBTIDOS:

[Cole aqui os últimos 50 linhas do log durante a geração do DANFE]

ERRO ESPECÍFICO:

[Cole a mensagem de erro específica, se houver]

PDF GERADO:

[ ] Sim, mas ainda diz "DANFE - SIMPLIFICADO"
[ ] Não, erro ao gerar
[ ] Não, página em branco
[ ] Outro: _______________________
```

## 📞 COMANDOS ÚTEIS

```powershell
# Verificar status do serviço:
.\nssm.exe status NFe_Backend

# Reiniciar serviço:
.\nssm.exe restart NFe_Backend

# Ver últimas 50 linhas do log:
Get-Content C:\nfe_app\logs\service.log -Tail 50

# Monitorar logs em tempo real:
Get-Content C:\nfe_app\logs\service.log -Wait -Tail 50

# Ver apenas erros:
Get-Content C:\nfe_app\logs\service.log | Select-String "ERROR|Exception"

# Verificar versão do Git local:
git log --oneline -1

# Comparar com remoto:
git fetch origin
git log HEAD..origin/copilot/vscode1759248218459 --oneline

# Verificar bibliotecas instaladas:
C:\nfe_app\venv\Scripts\activate
pip list | Select-String "nfelib|xsdata|lxml"
deactivate
```

## 📚 REFERÊNCIAS

- **Documentação Completa**: Ver arquivo `DANFE_DEBUG_IMPLEMENTATION.md`
- **Commit Git**: `f0f928d`
- **Branch**: `copilot/vscode1759248218459`

---

**BOA SORTE! 🚀**

A implementação está pronta. Agora é só atualizar o servidor e analisar os logs para identificar o problema específico do nfelib.
