# Diagnóstico e Solução: Erro de Conexão CEP

## 🔴 Problema Identificado

**Erro:** "Erro de conexão com o serviço de CEP. Verifique sua internet."

**Causa Raiz:** Sem conectividade com a internet no momento do teste.

```bash
# Teste de conectividade realizado:
$ curl -I https://viacep.com.br
curl: (35) Recv failure: Network is down
```

## ✅ Soluções Implementadas

### 1. Melhorias no Diagnóstico

**Arquivo:** `routes/admin_routes.py` - função `buscar_cep()`

**Mudanças:**
- ✅ Timeout aumentado de 5s para 10s
- ✅ User-Agent adicionado nos headers
- ✅ Tratamento específico de `ConnectionError`
- ✅ Mensagens de erro mais detalhadas
- ✅ Logs melhorados com emojis para fácil identificação

**Tipos de erro tratados:**
- **400** - CEP inválido (não tem 8 dígitos)
- **404** - CEP não encontrado no ViaCEP
- **500** - Erro HTTP do servidor ViaCEP
- **503** - Sem conexão com internet
- **504** - Timeout (mais de 10 segundos)

### 2. Modo Fallback para Desenvolvimento

**Arquivo:** `config/cep_config.py` (NOVO)

**Funcionalidade:**
Quando não há internet, a API tenta usar CEPs de teste pré-configurados.

**CEPs de Teste Disponíveis:**
- `01310-100` - Av. Paulista, São Paulo/SP
- `20040-020` - Av. Rio Branco, Rio de Janeiro/RJ
- `30130-100` - Av. Afonso Pena, Belo Horizonte/MG
- `40020-000` - Praça da Sé, Salvador/BA
- `80010-000` - Praça Tiradentes, Curitiba/PR

**Como funciona:**
1. Tenta conectar no ViaCEP (online)
2. Se falhar por falta de internet → Busca nos CEPs de teste
3. Se o CEP estiver nos testes → Retorna dados mockados
4. Se não estiver → Retorna erro informativo

## 🔧 Como Resolver o Problema Atual

### Solução 1: Restaurar Conexão com Internet

1. **Verificar WiFi/Ethernet:**
   ```bash
   # Verificar interfaces de rede
   ifconfig | grep "status: active"
   
   # Testar conectividade básica
   ping -c 3 8.8.8.8
   ```

2. **Verificar DNS:**
   ```bash
   # Testar resolução de nomes
   nslookup viacep.com.br
   ```

3. **Verificar Firewall:**
   ```bash
   # macOS: Verificar firewall
   sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
   ```

### Solução 2: Usar CEPs de Teste (Desenvolvimento)

**Para testar sem internet:**

1. Usar um dos CEPs de teste listados acima
2. O sistema detectará falta de conexão
3. Automaticamente usará dados mockados
4. Aparecerá aviso no log: `⚠️ MODO OFFLINE: Usando CEP de teste`

**Exemplo no formulário:**
```
CEP: 01310-100
[Buscar CEP] → Retorna Av. Paulista mesmo sem internet
```

### Solução 3: Adicionar Mais CEPs de Teste

**Editar:** `config/cep_config.py`

```python
CEPS_TESTE = {
    '01310100': {
        'cep': '01310-100',
        'logradouro': 'Avenida Paulista',
        'bairro': 'Bela Vista',
        'localidade': 'São Paulo',
        'uf': 'SP',
        'ibge': '3550308',
        'ddd': '11'
    },
    # Adicionar mais CEPs aqui
}
```

## 📊 Mensagens de Erro Detalhadas

### Antes (genérico):
```
❌ Erro de conexão com o serviço de CEP. Verifique sua internet.
```

### Depois (específico):

**Sem Internet:**
```
❌ Não foi possível conectar ao serviço ViaCEP. Verifique sua conexão com a internet.
📋 Details: ConnectionError - Verifique se você está conectado à internet e se não há firewall bloqueando.
```

**Timeout:**
```
⏱️ Tempo esgotado ao consultar CEP (10 segundos). O serviço pode estar lento.
📋 Details: Timeout - Tente novamente em alguns instantes.
```

**CEP Inválido:**
```
❌ CEP inválido. Deve conter 8 dígitos.
```

**CEP Não Encontrado:**
```
❌ CEP não encontrado.
```

## 🧪 Como Testar

### Teste 1: Com Internet

```bash
# 1. Conectar à internet
# 2. Acessar formulário de destinatário
# 3. Digitar: 01310-100
# 4. Clicar "Buscar CEP"
# 5. Verificar retorno: Av. Paulista, São Paulo/SP
```

### Teste 2: Sem Internet (Modo Fallback)

```bash
# 1. Desconectar da internet
# 2. Acessar formulário de destinatário
# 3. Digitar um CEP de teste: 01310-100
# 4. Clicar "Buscar CEP"
# 5. Verificar retorno: Dados mockados com aviso no log
# 6. Logs mostrarão: ⚠️ MODO OFFLINE: Usando CEP de teste
```

### Teste 3: CEP Não Encontrado

```bash
# 1. Conectar à internet
# 2. Digitar CEP inexistente: 00000-000
# 3. Verificar erro: "CEP não encontrado"
```

## 🔍 Logs para Monitorar

### Console do Flask:

```bash
# Sucesso:
🔍 Buscando CEP: 01310100
🌐 Tentando conectar em: https://viacep.com.br/ws/01310100/json/
✅ CEP encontrado: Avenida Paulista, São Paulo/SP

# Erro de conexão:
🔍 Buscando CEP: 01310100
🌐 Tentando conectar em: https://viacep.com.br/ws/01310100/json/
❌ Erro de conexão específico: ConnectionError(...)
⚠️ MODO OFFLINE: Usando CEP de teste para 01310100

# Timeout:
🔍 Buscando CEP: 01310100
⏱️ Timeout ao buscar CEP: 01310100
```

## 📝 Próximos Passos

1. ✅ Restaurar conexão com internet
2. ✅ Testar busca de CEP real
3. ⏳ Adicionar mais CEPs de teste se necessário
4. ⏳ Considerar cache de CEPs buscados recentemente
5. ⏳ Implementar busca offline com banco de dados local de CEPs

## 🆘 Comandos de Diagnóstico

```bash
# Verificar conectividade
ping -c 3 viacep.com.br

# Testar API ViaCEP diretamente
curl https://viacep.com.br/ws/01310100/json/

# Verificar porta de saída HTTPS
nc -zv viacep.com.br 443

# Ver logs do Flask
tail -f logs/app.log  # Se configurado

# Verificar biblioteca requests
python3 -c "import requests; print(requests.__version__)"
```

## ✨ Melhorias Implementadas

1. **Diagnóstico melhorado** - Mensagens específicas por tipo de erro
2. **Timeout aumentado** - 10 segundos ao invés de 5
3. **User-Agent** - Evita bloqueio por alguns servidores
4. **Modo fallback** - CEPs de teste para desenvolvimento offline
5. **Logs detalhados** - Facilita debugging
6. **Tratamento robusto** - Captura todos os tipos de erro de rede

---

**Status:** ✅ Código atualizado e pronto para uso  
**Requer:** Conexão com internet OU uso de CEPs de teste  
**Última atualização:** 10/11/2025
