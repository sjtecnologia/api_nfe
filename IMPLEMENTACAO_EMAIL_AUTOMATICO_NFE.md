# Implementação: Envio Automático de Email após Autorização de NFe

**Data:** 11 de fevereiro de 2026  
**Desenvolvedor:** Sistema EmiteMax  
**Versão:** 1.0

## 📋 Resumo da Implementação

Implementado sistema de **envio automático de email** para destinatários quando uma NFe é autorizada pela SEFAZ, incluindo XML e DANFE como anexos. O email possui design profissional com logo da EmiteMax para maior credibilidade.

---

## 🎯 Funcionalidades Implementadas

### 1. **Envio Automático de Email**
- ✅ Dispara automaticamente quando NFe é **AUTORIZADA** pela SEFAZ
- ✅ Busca email do destinatário no **cadastro** (tabela `destinatarios_nfe`)
- ✅ Alternativa: busca email nos **dados da API** (campo `destinatario.email` no JSON)
- ✅ Anexa **XML** da nota fiscal
- ✅ Anexa **DANFE em PDF**
- ✅ Validação e tratamento de erros sem bloquear emissão

### 2. **Template de Email Profissional**
- ✅ **Logo EmiteMax** em destaque (📄 EMITEMAX)
- ✅ Design responsivo e moderno
- ✅ Cores institucionais (gradiente azul #00bcd4 → #0097a7)
- ✅ Informações completas da NFe:
  - Número da nota
  - Emitente e destinatário
  - Valor total formatado
  - Chave de acesso
  - Protocolo de autorização
  - Data/hora de autorização
- ✅ Lista de anexos inclusos
- ✅ Avisos importantes (guardar email, contabilidade)

### 3. **Integração Completa**
- ✅ Interface web (emissão manual via formulário)
- ✅ API v2 (emissão via integração JSON)
- ✅ Botão "Compartilhar" atualizado com novo template

---

## 📁 Arquivos Modificados

### 1. **`services/email_service.py`**

#### Nova Função: `enviar_nfe_automaticamente()`
```python
def enviar_nfe_automaticamente(nfe_id, db_session=None):
    """
    Envia NFe automaticamente após autorização pela SEFAZ
    Busca o email do destinatário no cadastro ou nos dados da NFe
    """
```

**Fluxo:**
1. Busca NFe com JOIN no cadastro do destinatário
2. Valida se destinatário tem email cadastrado
3. Se não tiver, busca email nos dados JSON (para API)
4. Valida formato do email
5. Prepara anexos (XML + DANFE)
6. Gera template profissional
7. Envia email
8. Retorna resultado (success/failure)

#### Nova Função: `gerar_template_email_nfe()`
```python
def gerar_template_email_nfe(nfe_id, numero_nfe, emitente, destinatario, 
                             chave_acesso, protocolo, data_autorizacao, 
                             valor_total, anexos):
    """
    Gera template HTML profissional para email de NFe com logo da EmiteMax
    """
```

**Características do Template:**
- Logo grande e destacada no header
- Gradiente de cores institucional
- Tabela de informações com ícones
- Box de anexos diferenciado
- Footer com informações da empresa
- Totalmente responsivo

---

### 2. **`routes/nfe_routes.py`**

#### Modificação 1: Emissão Web (linha ~723)
Após gerar DANFE com sucesso, adiciona:

```python
# === ENVIAR EMAIL AUTOMATICAMENTE PARA O DESTINATÁRIO ===
try:
    print(" === ENVIANDO EMAIL AUTOMÁTICO PARA DESTINATÁRIO ===")
    from services.email_service import enviar_nfe_automaticamente
    
    resultado_email = enviar_nfe_automaticamente(nfe_id, db)
    
    if resultado_email.get('success'):
        print(f"✅ Email automático enviado com sucesso!")
        flash('Email com NFe enviado automaticamente para o destinatário!', 'success')
    else:
        msg_erro = resultado_email.get('message', 'Erro desconhecido')
        print(f"⚠️  Email automático não enviado: {msg_erro}")
        if 'sem email' not in msg_erro.lower():
            flash(f'Aviso: Não foi possível enviar email automático - {msg_erro}', 'warning')
            
except Exception as email_error:
    print(f"❌ Erro ao enviar email automático: {str(email_error)}")
    import traceback
    traceback.print_exc()
    flash('NFe emitida com sucesso, mas houve erro no envio automático do email.', 'warning')
```

**Comportamento:**
- ✅ Não bloqueia a emissão se houver erro no email
- ✅ Mostra mensagem de sucesso ao usuário
- ✅ Avisa se não conseguiu enviar (mas sem alarmar)
- ✅ Logs detalhados para debug

#### Modificação 2: Função Compartilhar (linha ~3290)
Substituído template antigo pelo novo:

```python
# Usar o template profissional com logo da EmiteMax
corpo_html = gerar_template_email_nfe(
    nfe_id=nfe_id,
    numero_nfe=nfe_data.get('numero', nfe_id),
    emitente=nfe_data.get('cliente_nome', 'N/A'),
    destinatario=nfe_data.get('destinatario_razao_social', 'N/A'),
    chave_acesso=nfe_data.get('chave_acesso', 'N/A'),
    protocolo=nfe_data.get('protocolo_sefaz', 'N/A'),
    data_autorizacao=data_autorizacao_str,
    valor_total=nfe_data.get('valor_total', 0),
    anexos=anexos
)
```

---

### 3. **`routes/api_v2_routes.py`**

#### Modificação: Emissão via API (linha ~487)
Substituído código antigo por envio automático:

```python
# === ENVIAR EMAIL AUTOMATICAMENTE ===
enviar_email_auto = data.get('enviar_email', True)  # Por padrão, enviar

if enviar_email_auto:
    try:
        print(f"📧 [API-V2] Tentando enviar email automático para NFe #{nfe.nfe_emitida_id}")
        from services.email_service import enviar_nfe_automaticamente
        
        resultado_email = enviar_nfe_automaticamente(nfe.nfe_emitida_id, db)
        
        if resultado_email.get('success'):
            print(f"✅ [API-V2] Email enviado com sucesso!")
        else:
            print(f"⚠️  [API-V2] Email não enviado: {resultado_email.get('message')}")
    except Exception as e:
        print(f"❌ [API-V2] Erro ao enviar email: {str(e)}")
```

**Parâmetro API:**
- `enviar_email`: `true` (padrão) ou `false`
- Se `false`, não envia email automático

---

## 🗄️ Requisitos de Banco de Dados

### Tabela: `destinatarios_nfe`
Campo necessário:
```sql
email VARCHAR(255) NULL
```

✅ **Campo já existe** na estrutura atual do banco.

### Query Utilizada:
```sql
SELECT 
    n.*,
    c.razao_social as emitente_nome,
    d.email as destinatario_email,
    d.nome_razao_social as destinatario_nome
FROM nfe_emitidas n
JOIN clientes c ON n.cliente_id = c.cliente_id
LEFT JOIN destinatarios_nfe d ON d.cpf_cnpj = n.destinatario_cnpj_cpf
WHERE n.nfe_emitida_id = :nfe_id
```

---

## 📧 Configuração de Email (/.env)

Variáveis necessárias (já existentes):
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=seu_email@gmail.com
SMTP_PASSWORD=sua_senha_de_app
SMTP_FROM_NAME=EmiteMax
```

---

## 🔄 Fluxo de Funcionamento

### Cenário 1: Emissão Web (Interface)
```
1. Usuário preenche formulário de emissão
2. Sistema valida e gera XML
3. Assina XML com certificado
4. Envia para SEFAZ
5. ✅ SEFAZ autoriza (status = "AUTORIZADA")
6. Sistema salva NFe no banco
7. Sistema gera DANFE automaticamente
8. 📧 Sistema envia email automático para destinatário
   - Busca email no cadastro
   - Anexa XML + DANFE
   - Usa template profissional
   - Envia via SMTP
9. Usuário recebe confirmação visual
```

### Cenário 2: Emissão via API
```
1. Cliente envia POST /api/v2/nfes/emitir
2. Sistema processa e autoriza
3. ✅ NFe autorizada
4. 📧 Se enviar_email=true (padrão):
   - Busca email do destinatário
   - Envia automaticamente
5. Retorna JSON com sucesso
```

### Cenário 3: Compartilhamento Manual
```
1. Usuário acessa lista de NFes
2. Clica em "Compartilhar" na NFe desejada
3. Informa email do destinatário
4. Sistema usa novo template profissional
5. 📧 Envia email
6. Confirmação de envio
```

---

## ⚠️ Tratamento de Erros

### 1. **Destinatário sem Email**
```
⚠️ [AUTO-EMAIL] NFe #123 - Destinatário sem email cadastrado
```
- Não bloqueia emissão
- Apenas loga aviso
- NFe é emitida normalmente

### 2. **Email Inválido**
```
❌ [AUTO-EMAIL] NFe #123 - Email inválido: teste@exemplo
```
- Valida formato com regex
- Não envia se inválido
- Loga erro específico

### 3. **Erro ao Gerar DANFE**
```
⚠️ [AUTO-EMAIL] DANFE não encontrado em: /path/to/danfe_123.pdf
```
- Envia apenas XML
- Continua com envio
- Avisa sobre ausência do DANFE

### 4. **Erro de SMTP**
```python
{
    'success': False,
    'message': 'Erro de autenticação: Verifique o email e senha de app do Gmail'
}
```
- Captura erro específico
- Retorna mensagem clara
- Não quebra aplicação

---

## 🧪 Como Testar

### Teste 1: Email Cadastrado
```sql
-- Verificar se destinatário tem email
SELECT d.nome_razao_social, d.email, d.cpf_cnpj
FROM destinatarios_nfe d
WHERE d.cpf_cnpj = '12345678901234';

-- Se não tiver, adicionar:
UPDATE destinatarios_nfe 
SET email = 'destinatario@exemplo.com'
WHERE cpf_cnpj = '12345678901234';
```

### Teste 2: Emitir NFe via Web
1. Acesse: `/nfe/emitir`
2. Selecione destinatário com email cadastrado
3. Preencha formulário
4. Clique em "Emitir NFe"
5. Aguarde autorização
6. **Verificar:**
   - ✅ Flash message: "Email com NFe enviado automaticamente..."
   - ✅ Logs: "✅ Email automático enviado com sucesso!"
   - ✅ Destinatário recebe email com XML + DANFE

### Teste 3: Emitir via API
```bash
curl -X POST http://localhost:8080/api/v2/nfes/emitir \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "destinatario": {
      "nome": "Fulano da Silva",
      "cpf_cnpj": "12345678901",
      "email": "fulano@exemplo.com"
    },
    "enviar_email": true,
    ...
  }'
```

**Verificar:**
- ✅ Resposta JSON: `"success": true`
- ✅ Log: `[API-V2] Email enviado com sucesso!`
- ✅ Email recebido

### Teste 4: Compartilhar Manualmente
1. Acesse lista de NFes
2. Clique em "Compartilhar" em uma NFe autorizada
3. Digite email do destinatário
4. Marque XML e DANFE
5. Enviar
6. **Verificar:**
   - ✅ Template profissional no email
   - ✅ Logo EmiteMax visível
   - ✅ Todos os dados corretos

---

## 📊 Logs e Monitoramento

### Logs Importantes:
```
📧 [AUTO-EMAIL] Iniciando envio automático para NFe #123
✅ [AUTO-EMAIL] XML adicionado
✅ [AUTO-EMAIL] DANFE adicionado
📧 [AUTO-EMAIL] Enviando para: cliente@exemplo.com
✅ [AUTO-EMAIL] Email enviado com sucesso para cliente@exemplo.com
```

### Logs de Erro:
```
❌ [AUTO-EMAIL] NFe #123 não encontrada
⚠️  [AUTO-EMAIL] NFe #123 - Destinatário sem email cadastrado
❌ [AUTO-EMAIL] NFe #123 - Email inválido: teste@
❌ [AUTO-EMAIL] Erro ao enviar NFe #123: Connection refused
```

---

## 🎨 Visualização do Email

### Header (Logo EmiteMax):
```
┌─────────────────────────────────────┐
│                                     │
│       📄 EMITEMAX                   │
│   SISTEMA DE EMISSÃO DE NOTAS       │
│          FISCAIS                    │
│                                     │
└─────────────────────────────────────┘
```

### Corpo:
```
Olá, [Nome do Destinatário]!

Você recebeu uma Nota Fiscal Eletrônica autorizada pela SEFAZ.

┌─────────────────────────────────┐
│ 🔢 Número NFe: #1234            │
│ 🏢 Emitente: Empresa Ltda       │
│ 👤 Destinatário: Cliente SA     │
│ 💰 Valor Total: R$ 1.500,00     │
│ 🔐 Protocolo: 135...            │
│ 📅 Autorização: 11/02/26 14:30  │
│ 🔑 Chave: 3526...               │
└─────────────────────────────────┘

📎 Arquivos anexados:
• NFe_1234.xml
• DANFE_NFe_1234.pdf

⚠️ Importante: Guarde este email e os arquivos...
```

---

## 🚀 Melhorias Futuras (Opcional)

### Fase 2:
- [ ] **Histórico de envio**: Tabela `nfe_emails_enviados` com log completo
- [ ] **Reenvio manual**: Botão para reenviar email caso destinatário não receba
- [ ] **CC/CCO**: Permitir cópias para contabilidade
- [ ] **Personalização**: Cliente poder customizar cor e logo do email
- [ ] **Rastreamento**: Saber se email foi aberto (pixel tracking)

### Fase 3:
- [ ] **WhatsApp**: Enviar DANFE também via WhatsApp API
- [ ] **SMS**: Notificação via SMS da emissão
- [ ] **Multi-idioma**: Templates em inglês/espanhol

---

## 📝 Checklist de Deploy

Antes de subir para produção:

- [x] ✅ Função `enviar_nfe_automaticamente()` criada
- [x] ✅ Template `gerar_template_email_nfe()` criado
- [x] ✅ Integração em `nfe_routes.py` (web)
- [x] ✅ Integração em `api_v2_routes.py` (API)
- [x] ✅ Botão compartilhar atualizado
- [x] ✅ Tratamento de erros implementado
- [ ] ⏳ Testar em ambiente de homologação
- [ ] ⏳ Verificar configuração SMTP no .env
- [ ] ⏳ Testar com diferentes destinatários
- [ ] ⏳ Validar template em clientes de email (Gmail, Outlook, etc.)
- [ ] ⏳ Deploy para produção
- [ ] ⏳ Monitorar logs primeiras 24h

---

## 🆘 Troubleshooting

### Problema: Email não está sendo enviado
**Verificar:**
1. Logs do console (procurar por `[AUTO-EMAIL]`)
2. Destinatário tem email cadastrado?
3. Variáveis `.env` estão corretas?
4. Senha de app do Gmail está válida?
5. DANFE foi gerado com sucesso?

### Problema: Email vai para SPAM
**Solução:**
- Adicionar SPF, DKIM, DMARC no domínio
- Usar servidor SMTP confiável
- Pedir para destinatários adicionarem remetente na whitelist

### Problema: Template não renderiza corretamente
**Verificar:**
- Cliente de email (Outlook antigo pode ter problemas)
- Testar em https://putsmail.com/ antes

---

## 📞 Suporte

Para dúvidas sobre esta implementação:
- **Documentação Técnica**: Este arquivo
- **Logs**: `/logs/error.log` e console do Flask
- **Código-fonte**: `services/email_service.py` e `routes/nfe_routes.py`

---

**Fim da Documentação** ✅
