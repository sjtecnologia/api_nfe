# Correção Final - Logo no DANFE

## 🐛 Problema
- NFe sendo emitida com sucesso
- Mas aparece "Internal Server Error" na tela
- DANFE gerado sem logo do cliente

## 🔍 Causa
O arquivo `services/danfe_service.py` estava tentando importar `get_db_connection` que não existe no `database/connection.py`.

## ✅ Solução

### Arquivo: `services/danfe_service.py`

**LINHA ~613** - Trocar:
```python
from database.connection import get_db_connection
from sqlalchemy import text
db = get_db_connection()
```

**Por:**
```python
from database.connection import SessionLocal
from sqlalchemy import text
db = SessionLocal()
```

## 🚀 Deploy no Servidor Windows

### 1. Copiar arquivo atualizado
Copie o arquivo `services/danfe_service.py` do Mac para o servidor Windows:
```
C:\nfe_app\services\danfe_service.py
```

### 2. Reiniciar serviço
```powershell
nssm restart NFe_Backend
```

### 3. Testar
1. Acesse: Emitir NFe
2. Preencha os dados (incluindo transportadora com ANTT, Marca, Numeração)
3. Emita a NFe
4. ✅ Não deve mais dar "Internal Server Error"
5. ✅ DANFE deve gerar normalmente
6. ✅ Se o cliente tiver logo cadastrada, ela aparecerá no DANFE

## 📋 Verificação

Após reiniciar, execute:
```powershell
python diagnostico_servidor.py
```

**Deve mostrar:**
```
3️⃣ Testando conexão com banco de dados...
   ✅ Coluna logo_path existe na tabela clientes
   ✅ Conexão com banco OK
```

## 🎯 Resultado Esperado

- ✅ Emissão de NFe sem erros
- ✅ DANFE oficial gerado (engine brazilfiscalreport)
- ✅ Campos de transportadora (ANTT, Marca, Numeração) no DANFE
- ✅ Logo do cliente aparecendo no DANFE (se cadastrada)
- ✅ Sem "Internal Server Error"

---

**Data:** 02/12/2025  
**Versão:** 1.3 FINAL  
**Status:** ✅ Pronto para deploy
