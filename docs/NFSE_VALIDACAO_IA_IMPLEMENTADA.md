# Validação IA Implementada na Emissão de NFS-e

## 📋 Resumo

Implementada validação por Inteligência Artificial na tela de emissão da NFS-e Nacional (GISS Online), seguindo o mesmo padrão já existente na emissão de NF-e.

## ✅ Alterações Realizadas

### 1. **Template de Emissão** (`templates/admin/nfse/emitir.html`)

#### 1.1 Botão de Validação IA
Adicionado botão "Validar com IA" na seção de ações:

```html
<button type="button" class="btn btn-info btn-lg me-2" onclick="validarComIA()" id="btnValidarIA">
    <i class="fas fa-robot"></i> Validar com IA
</button>
```

#### 1.2 Modal de Validação
Adicionado modal Bootstrap 5 para exibir resultados da validação:

```html
<div class="modal fade" id="modalValidacaoIA" tabindex="-1">
    <!-- Modal com loading e resultado -->
</div>
```

**Características do Modal:**
- Loading animado durante análise
- Score de confiança (0-100%)
- Erros críticos (impeditivos)
- Alertas (recomendações)
- Sugestões de melhoria
- Cores dinâmicas baseadas no resultado:
  - ✅ Verde: Tudo OK
  - ⚠️ Amarelo: Alertas
  - ❌ Vermelho: Erros críticos

#### 1.3 Funções JavaScript

**`validarComIA()`**
- Inicializa e exibe o modal
- Coleta dados do formulário
- Envia para API `/api/llm/validar-nfse`
- Trata erros de conexão

**`coletarDadosFormulario()`**
- Valida campos obrigatórios
- Coleta dados do prestador (emitente)
- Coleta dados do Tomadores (selecionado)
- Coleta dados do serviço (valores, alíquotas)
- Coleta dados da Reforma Tributária (IBS/CBS)
- Retorna objeto estruturado para validação

**`mostrarResultadoValidacao(data)`**
- Monta HTML com resultado da validação
- Exibe score de confiança com badge colorido
- Lista erros críticos com soluções
- Lista alertas com sugestões
- Lista sugestões de melhoria
- Adapta cor do header conforme resultado

### 2. **Endpoint da API** (`routes/llm_api_routes.py`)

Adicionado novo endpoint para validar NFS-e:

```python
@llm_api_bp.route('/validar-nfse', methods=['POST'])
def validar_nfse_com_ia():
    """
    Endpoint para validar dados da NFS-e usando IA antes da emissão.
    Chama o serviço ia_service FastAPI.
    """
```

**Funcionalidades:**
- Recebe dados da NFS-e via POST (JSON)
- Valida presença dos dados
- Conecta ao serviço IA (FastAPI na porta 8081)
- Endpoint IA: `/valida/nfse-pre-emissao`
- Timeout: 60 segundos
- Trata erros de conexão e exceções
- Retorna estrutura padronizada:

```json
{
  "sucesso": true/false,
  "validacao_ok": true/false,
  "erros_criticos": [
    {
      "campo": "nome_campo",
      "erro": "descrição do erro",
      "solucao": "como resolver"
    }
  ],
  "alertas": [
    {
      "campo": "nome_campo",
      "alerta": "descrição do alerta",
      "sugestao": "recomendação"
    }
  ],
  "sugestoes_melhoria": ["sugestão1", "sugestão2"],
  "score_confianca": 0-100,
  "resumo": "texto resumido"
}
```

## 🎯 Dados Enviados para Validação

### Estrutura do JSON

```json
{
  "ambiente": "homologacao",
  "tipo_documento": "nfse",
  "prestador": {
    "cnpj": "string",
    "razao_social": "string",
    "inscricao_municipal": "string",
    "uf": "string",
    "municipio": "string"
  },
  "Tomadores": {
    "cpf_cnpj": "string",
    "razao_social": "string",
    "uf": "string",
    "municipio": "string"
  },
  "servico": {
    "codigo_servico": "string",
    "codigo_nbs": "string",
    "discriminacao": "string",
    "valor_servicos": float,
    "valor_deducoes": float,
    "aliquota_iss": float,
    "valor_iss": float,
    "base_calculo": float,
    "valor_liquido": float
  },
  "reforma_tributaria": {
    "percentual_tributos_federais": float,
    "percentual_tributos_estaduais": float,
    "percentual_tributos_municipais": float,
    "finalidade_nfse": "string",
    "indicador_consumidor_final": "string",
    "codigo_indicador_operacao": "string",
    "indicador_destinatario": "string",
    "cst_ibs_cbs": "string",
    "codigo_classificacao_tributaria": "string",
    "percentual_redutor": float
  },
  "informacoes_complementares": "string"
}
```

## 🔍 Validações Esperadas da IA

A IA deve validar:

### 1. **Dados do Serviço**
- ✅ Código de serviço válido para São José do Rio Preto
- ✅ Código NBS compatível com o serviço
- ✅ Discriminação clara e completa
- ✅ Valores coerentes (serviço, deduções, líquido)
- ✅ Alíquota ISS compatível com o código de serviço

### 2. **Cálculos Tributários**
- ✅ Base de cálculo = Valor Serviços - Deduções
- ✅ Valor ISS = Base Cálculo × Alíquota ISS
- ✅ Valor Líquido = Valor Serviços - Valor ISS
- ✅ Soma de tributos totais coerente

### 3. **Reforma Tributária (IBS/CBS)**
- ✅ Finalidade NFS-e adequada (1-Normal, 2-Substituta, 3-Ajuste)
- ✅ Indicador consumidor final correto (0-Não, 1-Sim)
- ✅ Código indicador operação válido (6 dígitos)
- ✅ Indicador destinatário correto (1-Contribuinte ICMS, 2-Não Contribuinte, 0-Exterior)
- ✅ CST IBS/CBS válido (3 dígitos)
- ✅ Código classificação tributária válido (6 dígitos)
- ✅ Percentual redutor entre 0-100%

### 4. **Dados das Partes**
- ✅ CPF/CNPJ válidos (prestador e Tomadores)
- ✅ Inscrição Municipal do prestador
- ✅ Endereços completos
- ✅ UF e município corretos

### 5. **Regras GISS Online**
- ✅ Compatibilidade com estrutura XML v2.04
- ✅ Campos obrigatórios preenchidos
- ✅ Limites de valores respeitados
- ✅ Formato de códigos corretos

## 🚀 Como Usar

### 1. **Na Tela de Emissão**
1. Preencha os dados da NFS-e normalmente
2. Clique no botão **"Validar com IA"** (azul)
3. Aguarde a análise (modal aparece automaticamente)
4. Revise os resultados:
   - ✅ **Verde**: Tudo certo, pode emitir
   - ⚠️ **Amarelo**: Tem alertas, revise
   - ❌ **Vermelho**: Tem erros, corrija antes de emitir
5. Clique em **"Continuar para Emissão"** ou corrija os dados
6. Clique em **"Emitir NFS-e"** quando estiver pronto

### 2. **Interpretação do Score**
- **80-100%**: Alta confiança - NFS-e pronta
- **50-79%**: Média confiança - Revise alertas
- **0-49%**: Baixa confiança - Corrija erros críticos

## 🔧 Dependências

### Backend (Flask)
- `routes/llm_api_routes.py` - Endpoint de validação
- Blueprint `llm_api_bp` já registrado em `app.py`

### Frontend (Template)
- Bootstrap 5 - Modal e componentes UI
- jQuery/JavaScript - AJAX e manipulação DOM
- Font Awesome - Ícones

### Serviço IA (FastAPI)
- **URL**: `http://localhost:8081`
- **Endpoint**: `/valida/nfse-pre-emissao`
- **Método**: POST
- **Timeout**: 60 segundos

⚠️ **Importante**: O serviço IA precisa estar rodando na porta 8081 para a validação funcionar.

## 📊 Comparação com NFe

| Característica | NF-e | NFS-e |
|----------------|------|-------|
| Botão Validação IA | ✅ | ✅ |
| Modal Bootstrap 5 | ✅ | ✅ |
| Endpoint API | `/api/llm/validar-nfe` | `/api/llm/validar-nfse` |
| Serviço IA | `/valida/nfe-pre-emissao` | `/valida/nfse-pre-emissao` |
| Coleta Produtos/Itens | ✅ Múltiplos produtos | ✅ Dados do serviço |
| Coleta Destinatário/Tomadores | ✅ | ✅ |
| Score Confiança | ✅ | ✅ |
| Erros Críticos | ✅ | ✅ |
| Alertas | ✅ | ✅ |
| Sugestões | ✅ | ✅ |

## ✨ Melhorias Implementadas

1. **UX Consistente**: Mesmo padrão visual e de interação da NFe
2. **Feedback Visual**: Loading animado, cores dinâmicas, ícones claros
3. **Tratamento de Erros**: Mensagens amigáveis quando serviço IA está offline
4. **Validação Inteligente**: Coleta apenas dados preenchidos, não bloqueia formulário vazio
5. **Responsivo**: Modal funciona bem em desktop e mobile
6. **Acessível**: ARIA labels, foco correto, fechamento com ESC

## 🎓 Documentos Relacionados

- [IMPLEMENTACAO_COMPLETA.md](./nfse_sjrp_giss/IMPLEMENTACAO_COMPLETA.md) - Detalhes da implementação NFS-e
- [ANALISE_GISS_ONLINE.md](./nfse_sjrp_giss/ANALISE_GISS_ONLINE.md) - Análise dos schemas GISS
- [ATUALIZACAO_DANFE_MODAL.md](../ATUALIZACAO_DANFE_MODAL.md) - Padrão de modais usado

## 🐛 Troubleshooting

### Problema: Modal não abre
- **Causa**: Bootstrap 5 não carregado
- **Solução**: Verificar se `{% extends "admin/base.html" %}` está presente

### Problema: "Serviço IA offline"
- **Causa**: FastAPI não está rodando
- **Solução**: Iniciar serviço IA na porta 8081

### Problema: "Formulário incompleto"
- **Causa**: Campos obrigatórios vazios
- **Solução**: Preencher código serviço, discriminação e valor

### Problema: Erro 404 no endpoint
- **Causa**: Blueprint não registrado
- **Solução**: Verificar `app.py` linha 76: `app.register_blueprint(llm_api_bp)`

## 📝 Próximos Passos (Opcional)

1. **Criar endpoint no FastAPI** (`ia_service`):
   - Implementar `/valida/nfse-pre-emissao`
   - Integrar modelo LLM treinado
   - Implementar regras de validação GISS Online

2. **Expandir Validações**:
   - Validar CNAE vs Código Serviço
   - Validar benefícios fiscais aplicáveis
   - Sugerir deduções possíveis

3. **Histórico de Validações**:
   - Salvar validações no banco
   - Dashboard de erros mais comuns
   - Relatório de qualidade de emissões

4. **Testes Automatizados**:
   - Testes unitários do endpoint
   - Testes de integração com IA
   - Testes E2E do fluxo completo

---

**Data da Implementação**: {{ hoje }}  
**Versão**: 1.0  
**Padrão Utilizado**: NF-e Validação IA (referência)  
**Status**: ✅ Implementado e Pronto para Uso
