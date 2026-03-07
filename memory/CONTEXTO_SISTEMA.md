# 🖥️ Contexto Técnico do Sistema API NFe

**Última atualização:** 03/02/2026 13:50  
**Projeto:** API de emissão de Nota Fiscal Eletrônica  
**Branch atual:** lc214-migration

---

## 🌐 Infraestrutura AWS

### Servidor EC2
- **IP Público:** 3.87.73.106
- **Sistema Operacional:** Ubuntu 24.04.3 LTS
- **SSH Key:** ~/Downloads/nfe-new-api-key.pem
- **Usuário:** ubuntu
- **Comando de acesso:**
  ```bash
  ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106
  ```

### Banco de Dados - RDS PostgreSQL
- **Endpoint:** nfe-database.cenw06664z53.us-east-1.rds.amazonaws.com
- **Porta:** 5432
- **Database:** sjtnfe
- **Usuário:** postgres
- **Senha:** gMGM!#)NW$nH1w(wrVIdcmn5
- **Região:** us-east-1
- **Observação:** ⚠️ Senha contém caracteres especiais que requerem escape em shell

### Serviço Principal
- **Nome:** api-nfe-principal
- **Tipo:** systemd service
- **Framework:** Flask + Gunicorn
- **Porta:** 8080
- **Comandos úteis:**
  ```bash
  sudo systemctl status api-nfe-principal
  sudo systemctl restart api-nfe-principal
  sudo journalctl -u api-nfe-principal -f
  ```

---

## 📦 Stack Tecnológica

### Backend
- **Python:** 3.x
- **Framework:** Flask
- **WSGI Server:** Gunicorn
- **ORM:** SQLAlchemy
- **Biblioteca NFe:** nfelib 2.2.0 (biblioteca homologada)

### Certificado Digital
- **Tipo:** A3 (hardware)
- **Fornecedor:** SyngularID Multipla
- **Validade:** Até 19/08/2026
- **Algoritmo de assinatura:** SHA1 + RSA
- **Status:** ✅ Funcionando corretamente

### Integração SEFAZ
- **Ambiente:** Homologação (tpAmb=2)
- **UF:** São Paulo (SP)
- **Schema:** NFe 4.0
- **Namespace:** http://www.portalfiscal.inf.br/nfe
- **Timezone:** BRT (UTC-3) com margem de -10 minutos

---

## 📁 Estrutura de Arquivos Relevantes

### Serviços Principais
```
services/
├── nfe_nfelib_service.py    # ⭐ Geração de XML com nfelib (520 linhas)
├── sefaz_service.py          # Comunicação com SEFAZ
├── email_service.py          # Envio de emails
└── certificate_service.py    # Gestão de certificados
```

### Rotas
```
routes/
├── nfe_routes.py            # Endpoints de emissão de NFe
├── admin_routes.py          # Área administrativa
└── auth_routes.py           # Autenticação
```

### Configuração
```
config/
├── settings.py              # Configurações gerais
├── cep_config.py           # Configuração CEP
└── __init__.py
```

### Autenticação
```
auth/
├── api_key_auth.py         # Autenticação por API key
├── decorators.py           # Decorators de autenticação
├── login_manager.py        # Gestão de login
└── permissions.py          # Controle de permissões
```

---

## 🔧 Configurações Críticas NFe

### CNPJ e IE para Homologação
```python
# Substituição automática implementada
CNPJ_HOMOLOGACAO = "99999999000191"
IE_HOMOLOGACAO = "ISENTO"
```

### Mapeamento de Municípios
```python
MUNICIPIOS_IBGE = {
    '3550308': 'SAO PAULO',
    '3549805': 'SAO JOSE DO RIO PRETO',
    '3304557': 'RIO DE JANEIRO',
    '3106200': 'BELO HORIZONTE',
    '4106902': 'CURITIBA',
    '2927408': 'SALVADOR',
    '2304400': 'FORTALEZA',
    '2611606': 'RECIFE',
    '1302603': 'MANAUS',
    '5300108': 'BRASILIA'
}
```

### Fallback natOp
```python
def obter_natureza_operacao(cfop: str) -> str:
    if cfop.startswith('5'):
        return 'VENDA DE MERCADORIA'
    elif cfop.startswith('6'):
        return 'VENDA DE MERCADORIA PARA FORA DO ESTADO'
    else:
        return 'VENDA'
```

### Mapeamento CFOP → CSOSN
```python
CFOP_CSOSN_MAP = {
    '5102': '102',  # Venda de mercadoria - Simples Nacional sem permissão de crédito
    '5405': '102',  # Venda de mercadoria sujeita ao regime de ST
    '5656': '500',  # Venda de combustível ou lubrificante
    '6102': '103',  # Venda interestadual - Simples Nacional com permissão de crédito
}
```

---

## 📂 Arquivos de Debug

### XMLs Gerados
- **Localização:** `/tmp/` no servidor EC2
- **Padrão NFe:** `nfe_debug_*.xml` (XML da NFe antes do envelope)
- **Padrão Envelope:** `tmp*.xml` (Envelope SOAP completo)
- **Uso:**
  ```bash
  # Ver último XML gerado
  ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106 \
    "ls -lt /tmp/nfe_debug_*.xml | head -1 | awk '{print \$NF}' | xargs cat"
  ```

### Logs do Sistema
```bash
# Logs do serviço principal
sudo journalctl -u api-nfe-principal -n 100

# Logs em tempo real
sudo journalctl -u api-nfe-principal -f

# Logs com filtro
sudo journalctl -u api-nfe-principal --since "1 hour ago"
```

---

## 🔐 Segurança

### Credenciais de Acesso
- ⚠️ Armazenadas em `.env` no servidor
- ⚠️ Senha do banco contém caracteres especiais
- ✅ SSH via chave privada (não senha)
- ✅ Certificado A3 em hardware

### Boas Práticas
- Não commitar `.env` no repositório
- Usar variáveis de ambiente para secrets
- Manter certificado A3 em local seguro
- Renovar certificado antes do vencimento (08/2026)

---

## 🚀 Deploy e Atualização

### Atualizar Código no Servidor
```bash
# 1. SSH no servidor
ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106

# 2. Navegar para o diretório
cd /caminho/do/projeto

# 3. Puxar alterações
git pull origin lc214-migration

# 4. Reiniciar serviço
sudo systemctl restart api-nfe-principal

# 5. Verificar status
sudo systemctl status api-nfe-principal
```

### Verificar Deploy
```bash
# Ver logs em tempo real
sudo journalctl -u api-nfe-principal -f

# Testar endpoint
curl http://localhost:8080/health
```

---

## 🧪 Ambiente de Homologação SEFAZ

### Dados de Teste Obrigatórios
- **CNPJ Emitente:** 99999999000191
- **CNPJ Destinatário:** 99999999000191
- **IE Emitente:** ISENTO
- **tpAmb:** 2 (Homologação)

### Características
- Não gera efeitos fiscais
- Aceita CNPJs específicos de teste
- Algumas validações podem ser diferentes da produção
- Ideal para testes antes do ambiente real

### Webservices
- Autorização de NFe
- Consulta de status
- Cancelamento
- Inutilização de numeração

---

## 📋 Checklist Pré-Emissão

Antes de emitir uma NFe, verificar:

- [ ] Certificado A3 válido e instalado
- [ ] Ambiente configurado (homologação/produção)
- [ ] CNPJ/IE corretos para o ambiente
- [ ] Data/hora dentro do range aceitável
- [ ] Município (código + nome) consistentes
- [ ] CFOP compatível com CSOSN
- [ ] Natureza da operação preenchida
- [ ] Produtos com valores e quantidades válidas
- [ ] XML salvo para debug em /tmp/

---

## 🐛 Debug Comum

### Verificar XML Gerado
```bash
# No servidor
cat /tmp/nfe_debug_*.xml | grep -o '<xMun>[^<]*</xMun>'
cat /tmp/tmp*.xml | grep -o '<dhEmi>[^<]*</dhEmi>'
```

### Verificar Encoding
```bash
file /tmp/ultimo_envelope.xml
# Esperado: XML 1.0 document text, Unicode text, UTF-8 text
```

### Validar Estrutura XML
```bash
xmllint --noout /tmp/ultimo_envelope.xml
# Sem output = XML bem-formado
```

---

## 📞 Contatos de Suporte

### SEFAZ/SERPRO
- **Central de Atendimento:** https://www.serpro.gov.br/menu/suporte/central-de-atendimento-serpro-nfe-cte
- **Portal NFe:** https://www.nfe.fazenda.gov.br/
- **Perguntas Frequentes:** https://www.nfe.fazenda.gov.br/portal/perguntasFrequentes.aspx

### Certificado Digital
- **Fornecedor:** SyngularID
- **Tipo:** A3 (hardware)
- **Validade:** Verificar antes de emitir

---

## 📚 Documentação de Referência

### Oficial SEFAZ
- **MOC v7.0** - Manual de Orientação ao Contribuinte
- **Anexo I** - Leiaute e Regras de Validação
- **Schema NFe 4.0** - XSD oficial
- **Ver:** `/documentacaosefaz/MANUAIS_SEFAZ.md`

### Interna do Projeto
- **README_ESTRUTURA.md** - Estrutura do projeto
- **memory/HISTORICO_ERRO_225.md** - Histórico de correções
- **CORRECOES_APLICADAS.md** - Log de correções
- **GUIA_IMPLEMENTACAO_SEGURANCA.md** - Segurança

---

## 🎯 Próximos Passos

1. Resolver Erro 225 (em andamento)
2. Implementar emissão em produção
3. Testes de cancelamento e inutilização
4. Monitoramento e alertas
5. Backup e recuperação de desastres

---

**Última atualização:** 27/01/2026  
**Responsável:** Renato  
**Status:** Sistema em desenvolvimento - Erro 225 bloqueando emissão
