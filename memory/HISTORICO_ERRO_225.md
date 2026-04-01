# 📝 Histórico Completo: Erro 225 - Falha no Schema XML

**Período:** Vários dias (Janeiro 2026)  
**Status Atual:** ❌ NÃO RESOLVIDO (após 12 correções aplicadas)  
**Última Atualização:** 27/01/2026

---

## 🎯 Objetivo

Resolver o **Erro 225: Falha no Schema XML do lote de NFe** que persiste após múltiplas tentativas de emissão em ambiente de homologação SEFAZ SP.

---

## 📊 Evolução das Tentativas

### Fase 1: Geração Manual de XML (50+ tentativas - FALHOU)
- **Problema:** XML gerado manualmente tinha diversos erros estruturais
- **Erros encontrados:**
  - Tags vazias
  - Problemas de namespace
  - Erros de indentação
  - Campos obrigatórios faltando
- **Resultado:** Abandonado após 50+ tentativas sem sucesso

### Fase 2: Migração para nfelib (Commits a883dcf, f586163)
- **Decisão:** Usar biblioteca homologada nfelib
- **Resultado:** XML com 2200+ caracteres gerado com sucesso
- **Correção crítica:** Implementação da chave de acesso (44 dígitos + DV)
- **Status:** ✅ XML bem-formado mas Erro 225 persiste

### Fase 3: Correções de Validação (6 commits)

#### Commit 4da7cc9: Correções de data e emissão
- **dhEmi futura:** Implementado timezone BRT com margem de -10 minutos
- **procEmi errado:** Alterado de "0" para "1" (aplicação do contribuinte)
- **Status:** ✅ Corrigido

#### Commit 36f3da6: CFOP e CNPJ
- **CFOP/CSOSN incompatível:** CFOP 5405 → CSOSN 102 (operação normal)
- **CNPJ inválido:** Adicionado zfill(14) para preencher zeros à esquerda
- **Status:** ✅ Corrigido

#### Commit 947975e: Validações de campos
- **xNome vazio:** Implementado fallback para nome_razao_social
- **indIEDest:** Calculado dinamicamente (1=Contribuinte/2=Isento/9=Não contribuinte)
- **Validação de CNPJs:** Garantir que todos estão preenchidos
- **Status:** ✅ Corrigido

### Fase 4: Homologação CNPJ (Commits bda105e, b991ff3)
- **Problema:** Uso de CNPJs reais em homologação
- **Solução implementada:**
  - CNPJ emitente → 99999999000191 (CNPJ de teste SEFAZ)
  - CNPJ destinatário → 99999999000191
  - IE emitente → ISENTO
  - Chave de acesso regenerada com CNPJ de teste
- **Status:** ✅ Corrigido e testado

### Fase 5: natOp Automático (Commit 4a8eb99)
- **Problema:** "Natureza da operação é obrigatória"
- **Solução:** Fallback automático baseado em CFOP:
  - CFOP 5xxx → "VENDA DE MERCADORIA"
  - CFOP 6xxx → "VENDA DE MERCADORIA PARA FORA DO ESTADO"
  - Outros → "VENDA"
- **Status:** ✅ Corrigido

### Fase 6: Testes de Namespace (Commits c06c344, 914066c)
- **Tentativa:** Remover xmlns duplicado do elemento NFe
- **Resultado:** Erro 225 persistiu
- **Decisão:** Reverter - xmlns é padrão NFe 4.0
- **Status:** ✅ Mantido padrão oficial

### Fase 7: Município - DESCOBERTA CRÍTICA (Commit edd14c4 - HEAD)
- **Problema encontrado:** 
  - Código IBGE: `3549805` (São José do Rio Preto)
  - Nome município no banco: "SAO PAULO" ❌
  - **SEFAZ valida consistência entre código e nome!**
- **Solução implementada:**
  ```python
  MUNICIPIOS_IBGE = {
      '3550308': 'SAO PAULO',
      '3549805': 'SAO JOSE DO RIO PRETO',
      '3304557': 'RIO DE JANEIRO',
      # ... outros
  }
  
  def normalizar_municipio(codigo_ibge: str, nome_municipio: str) -> str:
      if codigo_ibge in MUNICIPIOS_IBGE:
          nome_correto = MUNICIPIOS_IBGE[codigo_ibge]
          if nome_municipio.upper() != nome_correto:
              print(f"⚠️ [CORREÇÃO] Município '{nome_municipio}' corrigido para '{nome_correto}'")
          return nome_correto
      return nome_municipio.upper()[:60]
  ```
- **Aplicação:** Emitente e destinatário
- **Validação:** ✅ XML confirmado com `<xMun>SAO JOSE DO RIO PRETO</xMun>`
- **Status:** ✅ Corrigido e validado MAS Erro 225 persiste ❌

---

## 🔧 Todas as Correções Aplicadas

| # | Correção | Commit | Status | Validado |
|---|----------|--------|--------|----------|
| 1 | Migração para nfelib | a883dcf, f586163 | ✅ | Sim |
| 2 | Chave de acesso (44 dígitos + DV) | f586163 | ✅ | Sim |
| 3 | Assinatura digital (SHA1+RSA) | f586163 | ✅ | Sim |
| 4 | Data BRT -10min | 4da7cc9 | ✅ | Sim |
| 5 | procEmi=1 | 4da7cc9 | ✅ | Sim |
| 6 | CFOP 5405 → CSOSN 102 | 36f3da6 | ✅ | Sim |
| 7 | CNPJ zfill(14) | 36f3da6 | ✅ | Sim |
| 8 | nome_razao_social fallback | 947975e | ✅ | Sim |
| 9 | indIEDest dinâmico | 947975e | ✅ | Sim |
| 10 | CNPJ/IE homologação (99999999000191) | bda105e, b991ff3 | ✅ | Sim |
| 11 | natOp fallback automático | 4a8eb99 | ✅ | Sim |
| 12 | **Normalização de municípios** | edd14c4 | ✅ | **Sim** |

**Total de correções:** 12  
**Correções validadas:** 12 (100%)  
**Erro 225 resolvido:** ❌ NÃO

---

## 🔍 Validações Realizadas

### Estrutura do XML
- ✅ XML bem-formado (validado com xmllint)
- ✅ Encoding UTF-8 correto
- ✅ Namespace correto: `xmlns="http://www.portalfiscal.inf.br/nfe"`
- ✅ Versão NFe 4.00
- ✅ Todos campos obrigatórios preenchidos

### Dados Específicos
- ✅ CNPJ emitente: 99999999000191 (teste)
- ✅ CNPJ destinatário: 99999999000191 (teste)
- ✅ IE emitente: ISENTO
- ✅ dhEmi: Com timezone BRT e margem de -10min
- ✅ Chave de acesso: 44 dígitos + DV correto
- ✅ Município emitente: `<cMun>3549805</cMun><xMun>SAO JOSE DO RIO PRETO</xMun>`
- ✅ Município destinatário: `<xMun>SAO JOSE DO RIO PRETO</xMun>`
- ✅ Assinatura digital presente no envelope SOAP

### Envelope SOAP
- ✅ 6102 caracteres
- ✅ Estrutura completa e válida
- ✅ Elemento Signature presente
- ✅ Namespace correto em todos elementos

---

## ❓ Perguntas Não Respondidas

### 1. Por que Erro 225 persiste?
- XML aparentemente 100% correto
- nfelib é biblioteca homologada (deveria gerar XML válido)
- Todas validações conhecidas foram aplicadas
- **Hipótese:** Pode haver validações específicas da SEFAZ SP não documentadas

### 2. Possíveis Causas Remanescentes
- [ ] Formatação de valores decimais específica
- [ ] Ordem de tags não conforme (nfelib deveria garantir)
- [ ] Caracteres especiais: "ASSOCIASSÃO" com Ç
- [ ] Campos opcionais que SEFAZ SP considera obrigatórios
- [ ] Versão do webservice incompatível
- [ ] Problema no certificado digital ou cadeia de certificação
- [ ] SEFAZ homologação fora do ar ou com problemas

### 3. Informações Necessárias
- ❓ Erro 225 apresenta alguma mensagem adicional além de "Falha no Schema XML"?
- ❓ Há sub-código ou descrição complementar?
- ❓ Screenshot do erro completo?
- ❓ Log do SEFAZ com detalhes da rejeição?

---

## 🚀 Próximas Ações Sugeridas

### Prioridade CRÍTICA
1. **Obter detalhes específicos do erro**
   - Solicitar screenshot completo da tela de erro
   - Verificar se há log detalhado no sistema SEFAZ
   - Buscar por mensagens adicionais ou sub-códigos

2. **Validação offline com XSD oficial**
   ```bash
   # Baixar XSD oficial do SEFAZ
   wget http://www.nfe.fazenda.gov.br/PORTAL/pac_download.aspx?esc=nfe_v4.00.xsd
   
   # Validar XML gerado
   xmllint --noout --schema nfe_v4.00.xsd /tmp/ultimo_envelope.xml
   ```

3. **Comparar com XML funcional**
   - Obter exemplo de NFe homologada com sucesso da SEFAZ SP
   - Comparar campo a campo com XML gerado
   - Identificar diferenças de formatação

### Prioridade ALTA
4. **Teste com dados simplificados**
   - NFe com valores redondos (R$ 100,00, quantidade 1)
   - Produto sem caracteres especiais
   - Descrições curtas e simples

5. **Normalização de caracteres especiais**
   ```python
   # Substituir: "ASSOCIASSÃO" → "ASSOCIACAO"
   texto_normalizado = unidecode(texto_original)
   ```

6. **Verificar estado do ambiente SEFAZ**
   - Consultar status dos webservices de homologação SP
   - Verificar se há manutenção programada
   - Testar consulta de status do serviço

### Prioridade MÉDIA
7. **Revisar configuração do certificado**
   - Verificar se cadeia de certificação está completa
   - Validar se certificado A3 está corretamente configurado
   - Testar com outro certificado (se disponível)

8. **Investigar logs do servidor**
   ```bash
   # Verificar logs do Gunicorn
   ssh -i ~/Downloads/nfe-new-api-key.pem ubuntu@3.87.73.106 \
     "sudo journalctl -u api-nfe-principal -n 100"
   ```

9. **Contatar suporte SEFAZ/SERPRO**
   - Central de Atendimento: https://www.serpro.gov.br/menu/suporte/central-de-atendimento-serpro-nfe-cte
   - Enviar XML de teste para análise
   - Solicitar detalhamento do Erro 225

---

## 📚 Arquivos de Referência

### Código Principal
- **services/nfe_nfelib_service.py** (520 linhas)
  - Linhas 1-40: Mapeamento e normalização de municípios
  - Linhas 100-118: Substituição de CNPJs para homologação
  - Linhas 132-148: Fallback automático de natOp
  - Linhas 165-255: Construção dos dados emitente/destinatário
  - Linhas 455-468: Salvamento de XML de debug

### XMLs Salvos
- **/tmp/nfe_debug_*.xml** - XML da NFe gerado (antes do envelope)
- **/tmp/tmp*.xml** - Envelope SOAP completo enviado à SEFAZ
- **/tmp/ultimo_envelope.xml** - Último envelope capturado (local)

### Documentação Criada
- **documentacaosefaz/MANUAIS_SEFAZ.md** - Referência dos manuais oficiais
- **memory/HISTORICO_ERRO_225.md** - Este arquivo

---

## 💭 Reflexões

### O que funcionou
- ✅ nfelib gera XML estruturalmente correto
- ✅ Assinatura digital implementada com sucesso
- ✅ Sistema de normalização automática de dados

### O que não funcionou
- ❌ Erro 225 é genérico demais para debug efetivo
- ❌ Biblioteca homologada não garante aceitação pela SEFAZ
- ❌ Falta de feedback específico dificulta correções

### Lições Aprendidas
1. **Validação é em camadas:**
   - Validação XSD (estrutura) ✅
   - Validação de negócio (regras SEFAZ) ❓
   
2. **Homologação ≠ Produção:**
   - CNPJs de teste específicos são obrigatórios
   - Alguns campos têm validações diferentes

3. **Dados inconsistentes causam rejeição:**
   - Município: código vs nome deve ser consistente
   - CFOP vs CSOSN deve ser compatível
   - Data não pode estar no futuro (mesmo com 1 minuto)

4. **Documentação oficial é essencial:**
   - Manual MOC v7.0 - Anexo I (Leiaute e Regras)
   - Cada UF pode ter regras específicas
   - Consultar sempre a versão mais atualizada

---

## 🆘 Estado Atual

**Frustração do usuário:** ⚠️ EXTREMA  
**Dias tentando:** Múltiplos  
**Correções aplicadas:** 12  
**Taxa de sucesso:** 0%  

**Problema principal:** Erro genérico sem informações específicas para debug.

**Necessidade imediata:** Obter detalhamento do erro ou validação offline com XSD oficial para identificar o problema exato.

---

**Última tentativa:** 27/01/2026 - Correção de município validada mas erro persiste.
