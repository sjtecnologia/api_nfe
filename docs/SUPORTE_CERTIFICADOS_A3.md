# Suporte a Certificados A3 (Tokens/Smartcards)

## 📋 Implementação Completa

O sistema EmiteMax agora suporta **certificados digitais A1 e A3**:

- **A1**: Arquivos .pfx/.p12 (implementação original)
- **A3**: Tokens USB e Smartcards via PKCS#11 (nova implementação)

---

## 🚀 Passo a Passo para Ativar Suporte A3

### 1. Executar Migration do Banco de Dados

```bash
cd /Users/renato/Documents/Developement/api_nfe
psql -U seu_usuario -d nome_banco -f database/migrations/add_tipo_certificado.sql
```

**Ou via código Python:**

```python
from database.connection import get_db
db = next(get_db())

# Executar SQL da migration
with open('database/migrations/add_tipo_certificado.sql', 'r') as f:
    sql = f.read()
    db.execute(sql)
    db.commit()
```

### 2. Instalar PyKCS11

**Linux:**
```bash
# Instalar dependências do sistema
sudo apt-get install swig libpcsclite-dev

# Instalar PyKCS11
pip install PyKCS11
```

**macOS:**
```bash
brew install swig pcsc-lite
pip install PyKCS11
```

**Windows:**
```bash
# Baixar e instalar SWIG: https://www.swig.org/download.html
# Adicionar SWIG ao PATH

pip install PyKCS11
```

### 3. Instalar Drivers do Token

Cada fabricante tem seu próprio driver:

**SafeNet eToken:**
- Windows: https://support.globalsign.com/ca-certificates/local-registration-authorities-lras/safenet-drivers
- Linux: https://www.globalsign.com/en/safenet-drivers

**Certisign:**
- https://www.certisign.com.br/downloads

**Gemalto/Thales:**
- https://www.thalesgroup.com/en/markets/digital-identity-and-security/government/customer-services/software-downloads

**Watchdata:**
- https://www.watchdata.com/downloads

### 4. Verificar Instalação

```python
python3 -c "import PyKCS11; print('PyKCS11 OK')"
```

Se não houver erro, a instalação está correta.

---

## 💻 Como Usar no Sistema

### Registrar Certificado A3

1. **Acessar página do cliente**
2. **Clicar em "Adicionar Certificado A3"** (ou ir para `/a3/select/<cliente_id>`)
3. **Conectar o token USB**
4. **Clicar em "Detectar Tokens"**
   - O sistema detecta automaticamente bibliotecas PKCS#11 instaladas
   - Lista todos os tokens conectados
5. **Selecionar o token desejado**
6. **Digitar o PIN** (⚠️ cuidado com tentativas erradas - pode bloquear)
7. **Selecionar o certificado** na lista
8. **Clicar em "Registrar Certificado"**

### Assinar Nota Fiscal com A3

Não há diferença no uso! O sistema detecta automaticamente o tipo:

```python
# Mesma função para A1 e A3
from services.xml_signature_service import XMLSignatureService

signer = XMLSignatureService()
xml_assinado = signer.sign_nfe_xml(xml_content, db_session, cliente_id)
```

O serviço verifica o campo `tipo_certificado` e usa a estratégia correta automaticamente.

---

## 🔧 Arquitetura Técnica

### Arquivos Criados/Modificados

**1. Migration de Banco:**
- `database/migrations/add_tipo_certificado.sql`
- Adiciona colunas: `tipo_certificado`, `token_slot_id`, `token_label`, `pkcs11_library`

**2. Modelo de Dados:**
- `database/models.py` - Classe `CertificadoDigital` atualizada

**3. Serviço PKCS#11:**
- `services/pkcs11_service.py` (NOVO)
- Funções:
  - `detect_libraries()` - Detecta drivers instalados
  - `list_tokens()` - Lista tokens conectados
  - `list_certificates_in_token()` - Lista certificados no token
  - `sign_data_with_token()` - Assina dados com chave privada do token
  - `get_certificate_from_token()` - Extrai certificado em DER

**4. Serviço de Certificados:**
- `services/certificate_service.py`
- Nova função: `process_certificate_a3_registration()`

**5. Serviço de Assinatura XML:**
- `services/xml_signature_service.py`
- Nova função: `_sign_with_a3_token()`
- Atualizada: `sign_nfe_xml()` - detecta tipo e delega

**6. Rotas API:**
- `routes/a3_routes.py` (NOVO)
- Endpoints:
  - `GET /a3/detect-tokens` - Detectar tokens
  - `POST /a3/list-certificates` - Listar certificados
  - `POST /a3/register` - Registrar certificado
  - `GET /a3/select/<cliente_id>` - Página de seleção

**7. Template HTML:**
- `templates/a3/select_certificate.html` (NOVO)
- Interface interativa em 3 steps

**8. App Principal:**
- `app.py` - Registra blueprint `a3_bp`

**9. Dependências:**
- `requirements.txt` - Adicionado `PyKCS11>=1.5.12`

---

## 🏗️ Fluxo de Assinatura com A3

```
1. Usuário emite NFe
   ↓
2. Sistema busca certificado ativo (get_active_certificate_for_client)
   ↓
3. Verifica tipo_certificado
   ├── A1: Carrega .pfx da base64 em memória
   └── A3: Usa PKCS#11 para acessar token
   ↓
4. Canonicaliza XML (infNFe)
   ↓
5. Calcula digest SHA-1
   ↓
6. Cria SignedInfo
   ↓
7. Assina SignedInfo
   ├── A1: Usa cryptography com chave em memória
   └── A3: Envia para token via PyKCS11.sign()
   ↓
8. Monta elemento <Signature>
   ↓
9. Insere no XML
   ↓
10. Retorna XML assinado
```

---

## 🔐 Segurança

### Armazenamento de PIN (A3)

- PIN é **criptografado** usando Fernet (mesma estratégia de senha A1)
- Chave derivada via PBKDF2HMAC com 100.000 iterações
- Salt fixo: `cert_salt_nfe_2024`
- Master key: variável ambiente `CERT_MASTER_KEY`

### Boas Práticas

✅ **Recomendado:**
- Usar variável de ambiente `CERT_MASTER_KEY` única por instalação
- Trocar PIN do token após primeiro uso
- Limitar tentativas de PIN (3x = bloqueio)
- Usar tokens com proteção física (botão de confirmação)

❌ **Evitar:**
- Deixar master key padrão em produção
- Compartilhar PINs entre usuários
- Deixar token conectado 24/7

---

## 🧪 Testes

### Testar Detecção de Tokens

```python
from services.pkcs11_service import get_pkcs11_service

pkcs11 = get_pkcs11_service()

# Detectar bibliotecas
libs = pkcs11.detect_libraries()
print(f"Bibliotecas encontradas: {len(libs)}")

# Listar tokens
tokens = pkcs11.list_tokens()
print(f"Tokens conectados: {len(tokens)}")

for token in tokens:
    print(f"- {token['label']} (Slot {token['slot_id']})")
```

### Testar Listagem de Certificados

```python
library_path = "/usr/lib/libeTPkcs11.so"  # ou caminho Windows
slot_id = 0
pin = "1234"  # seu PIN

certs = pkcs11.list_certificates_in_token(library_path, slot_id, pin)
print(f"Certificados encontrados: {len(certs)}")

for cert in certs:
    print(f"- {cert['common_name']}")
    print(f"  Válido: {cert['is_valid']}")
    print(f"  Até: {cert['not_after']}")
```

### Testar Assinatura

```python
from services.xml_signature_service import XMLSignatureService
from database.connection import get_db

db = next(get_db())
cliente_id = 1  # seu cliente com certificado A3

xml_nfe = """<?xml version="1.0" encoding="UTF-8"?>
<NFe>
    <infNFe Id="NFe12345678901234567890123456789012345678901234">
        <ide>...</ide>
    </infNFe>
</NFe>"""

signer = XMLSignatureService()
xml_assinado = signer.sign_nfe_xml(xml_nfe, db, cliente_id)

print("✓ XML assinado com sucesso!")
print(f"Tamanho: {len(xml_assinado)} bytes")
```

---

## 🐛 Troubleshooting

### "PyKCS11 não instalado"
```bash
pip install PyKCS11
```

### "Nenhuma biblioteca PKCS#11 encontrada"
- Instale drivers do token
- No Linux: `sudo apt-get install pcscd pcsc-tools`
- Verifique se token está conectado: `pcsc_scan`

### "Erro ao abrir sessão"
- Verifique se PIN está correto
- Tente desconectar e reconectar o token
- No Linux: `sudo systemctl restart pcscd`

### "Certificado não encontrado"
- Verifique se há certificados válidos no token
- Use ferramenta do fabricante para verificar
- SafeNet: Authentication Client
- Certisign: Token Manager

### "Assinatura inválida"
- Verifique sincronização de hora do sistema
- Token pode estar com hora desatualizada
- Alguns tokens exigem botão físico de confirmação

### Windows: "DLL load failed"
- Instale Visual C++ Redistributable
- Execute como Administrador
- Verifique PATH do driver

---

## 📊 Comparação A1 vs A3

| Característica | A1 (Arquivo) | A3 (Token) |
|----------------|--------------|------------|
| **Formato** | .pfx / .p12 | Hardware USB |
| **Validade** | 1 ano | 3-5 anos |
| **Segurança** | Média (arquivo copiável) | Alta (chave não exportável) |
| **Custo** | ~R$ 150-300 | ~R$ 250-500 |
| **Mobilidade** | Fácil (arquivo) | Requer token físico |
| **Backup** | Simples (cópia do arquivo) | Impossível (chave única) |
| **Instalação** | Simples | Requer drivers |
| **Uso no Sistema** | Transparente | Requer token conectado |

---

## 🎯 Próximos Passos

- [ ] Adicionar suporte a múltiplos certificados por cliente
- [ ] Implementar cache de sessão PKCS#11 (evitar relogin)
- [ ] Adicionar logs detalhados de uso de A3
- [ ] Criar dashboard de certificados ativos/vencidos
- [ ] Implementar notificações de vencimento
- [ ] Suportar HSM (Hardware Security Modules) via PKCS#11

---

## 📚 Referências

- **PKCS#11**: https://docs.oasis-open.org/pkcs11/pkcs11-base/v2.40/pkcs11-base-v2.40.html
- **PyKCS11**: https://github.com/LudovicRousseau/PyKCS11
- **ICP-Brasil**: https://www.gov.br/iti/pt-br/assuntos/certificacao-digital
- **NFe**: http://www.nfe.fazenda.gov.br/portal/principal.aspx

---

## ✅ Status da Implementação

- ✅ Migration de banco de dados
- ✅ Modelo CertificadoDigital atualizado
- ✅ Serviço PKCS#11 completo
- ✅ Adaptação do certificate_service
- ✅ Interface de seleção A3
- ✅ Assinatura XML com A3
- ✅ Dependência PyKCS11 adicionada
- ✅ Rotas registradas no app.py

**Sistema pronto para uso com certificados A1 e A3!** 🎉
