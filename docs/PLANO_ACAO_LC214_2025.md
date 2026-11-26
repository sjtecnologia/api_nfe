# 🎯 Plano de Ação: Adequação Completa à LC 214/2025

**Objetivo:** Migrar sistema de PIS/COFINS/ICMS/IPI para IBS/CBS  
**Prazo:** Dezembro/2025 - Dezembro/2026  
**Status Atual:** 38% completo

---

## 📅 CRONOGRAMA EXECUTIVO

### 🔴 FASE 1: PREPARAÇÃO (Dez/2025) - CRÍTICO
**Prazo:** 01/12/2025 - 31/12/2025  
**Responsável:** Equipe Técnica  
**Status:** 🟡 EM ANDAMENTO

#### Tarefas:

1. **Monitoramento Regulatório** (Diário)
   - [ ] Assinar boletim oficial do Comitê Gestor IBS
   - [ ] Monitorar Portal Nacional IBS (quando disponível)
   - [ ] Acompanhar CONFAZ para alíquotas estaduais
   - [ ] Verificar IN RFB sobre CBS
   - **Deadline:** 31/12/2025
   - **Entregável:** Planilha com alíquotas oficiais

2. **Análise de Impacto nos Clientes** (2 semanas)
   - [ ] Listar todos os clientes ativos
   - [ ] Identificar regimes tributários atuais
   - [ ] Calcular impacto financeiro estimado (simulação)
   - [ ] Criar relatório comparativo cliente a cliente
   - **Deadline:** 15/12/2025
   - **Entregável:** `RELATORIO_IMPACTO_CLIENTES_LC214.xlsx`

3. **Backup e Documentação** (1 semana)
   - [ ] Backup completo do banco de dados atual
   - [ ] Documentar todas as regras tributárias atuais
   - [ ] Criar snapshot do sistema antes da migração
   - [ ] Versionar código em branch específica `lc214-migration`
   - **Deadline:** 20/12/2025
   - **Entregável:** Backup restaurável + documentação

4. **Comunicação com Clientes** (2 semanas)
   - [ ] Criar comunicado oficial sobre LC 214/2025
   - [ ] Agendar webinar explicativo (Janeiro/2026)
   - [ ] Preparar FAQ sobre mudanças
   - [ ] Definir calendário de treinamentos
   - **Deadline:** 31/12/2025
   - **Entregável:** Material de comunicação aprovado

---

### 🟡 FASE 2: DADOS E CONFIGURAÇÃO (Jan/2026)
**Prazo:** 01/01/2026 - 31/01/2026  
**Responsável:** Equipe de Dados + Fiscal  
**Status:** 🔴 NÃO INICIADO

#### Tarefas:

5. **Importação de Alíquotas Oficiais** (1 semana)
   - [ ] Obter arquivo oficial de alíquotas IBS por município
   - [ ] Obter alíquota CBS federal oficial
   - [ ] Validar dados com contador/auditor
   - [ ] Executar script de importação
   - **Script:** `scripts/importar_aliquotas_ibs_oficiais.py`
   - **SQL:**
     ```sql
     UPDATE aliquotas_ibs 
     SET aliquota_ibs = [VALOR_OFICIAL],
         aliquota_cbs = [VALOR_CBS],
         ativo = true,
         fonte_dados = 'Comitê Gestor IBS - Resolução XX/2026'
     WHERE ano = 2026;
     ```
   - **Deadline:** 07/01/2026
   - **Entregável:** Tabela `aliquotas_ibs` populada

6. **Mapeamento NCM → Alíquotas Diferenciadas** (2 semanas)
   - [ ] Identificar NCMs com alíquotas reduzidas (cesta básica, etc)
   - [ ] Identificar NCMs com alíquotas majoradas (luxo, etc)
   - [ ] Criar tabela `ncm_aliquotas_especiais_ibs`
   - [ ] Popular com dados oficiais
   - **Referência:** Art. 382-A LC 214/2025 (alíquotas diferenciadas)
   - **Deadline:** 21/01/2026
   - **Entregável:** Tabela com +500 NCMs mapeados

7. **Configuração de Benefícios Fiscais** (1 semana)
   - [ ] Mapear benefícios ICMS que continuam como IBS
   - [ ] Mapear benefícios PIS/COFINS que continuam como CBS
   - [ ] Cadastrar benefícios específicos de cada cliente
   - [ ] Validar com contador responsável
   - **Deadline:** 28/01/2026
   - **Entregável:** Tabela `beneficios_fiscais_ibs` preenchida

8. **Testes de Cálculo** (1 semana)
   - [ ] Criar 50 cenários de teste (produtos/serviços variados)
   - [ ] Validar cálculos com contador
   - [ ] Comparar com sistema legado (PIS/COFINS/ICMS)
   - [ ] Documentar discrepâncias
   - **Deadline:** 31/01/2026
   - **Entregável:** Suite de testes automatizados

---

### 🟢 FASE 3: DESENVOLVIMENTO (Fev-Mar/2026)
**Prazo:** 01/02/2026 - 31/03/2026  
**Responsável:** Equipe de Desenvolvimento  
**Status:** 🔴 NÃO INICIADO

#### Tarefas:

9. **Atualização do Modelo de Dados** (1 semana)
   - [ ] Adicionar campos IBS/CBS em `itens_nfe`
   - [ ] Criar trigger para cálculo automático
   - [ ] Adicionar campos de crédito não-cumulativo
   - [ ] Migrar dados históricos (conversão)
   - **SQL:**
     ```sql
     ALTER TABLE itens_nfe ADD COLUMN valor_ibs NUMERIC(15,2);
     ALTER TABLE itens_nfe ADD COLUMN valor_cbs NUMERIC(15,2);
     ALTER TABLE itens_nfe ADD COLUMN aliquota_ibs_aplicada NUMERIC(5,2);
     ALTER TABLE itens_nfe ADD COLUMN aliquota_cbs_aplicada NUMERIC(5,2);
     ALTER TABLE itens_nfe ADD COLUMN valor_credito_ibs NUMERIC(15,2);
     ALTER TABLE itens_nfe ADD COLUMN valor_credito_cbs NUMERIC(15,2);
     ```
   - **Deadline:** 07/02/2026

10. **Integração API de Cálculo** (2 semanas)
    - [ ] Criar endpoint `/api/calcular_ibs_cbs`
    - [ ] Integrar com `services/calculo_ibs.py`
    - [ ] Adicionar cache de alíquotas (Redis)
    - [ ] Implementar fallback para erros
    - **Endpoints:**
      ```
      POST /api/calcular_ibs_cbs
      GET /api/aliquotas/municipio/{codigo_ibge}
      GET /api/aliquotas/ncm/{ncm}
      POST /api/simular_tributacao (comparativo)
      ```
    - **Deadline:** 21/02/2026

11. **Atualização do Frontend - Emissão NFe** (3 semanas)
    - [ ] Adicionar toggle "Usar IBS/CBS" ou "Usar Tributação Antiga"
    - [ ] Criar seção de tributos IBS/CBS na tela de itens
    - [ ] Mostrar cálculo comparativo em tempo real
    - [ ] Adicionar campo "Valor Crédito IBS" (para insumos)
    - **Telas afetadas:**
      - `templates/admin/nfes/emitir.html` (principal)
      - `templates/admin/nfes/visualizar.html`
      - `templates/admin/nfes/editar.html`
    - **Deadline:** 14/03/2026

12. **Geração de XML NFe 4.0 com IBS/CBS** (2 semanas)
    - [ ] Atualizar schema XML para incluir tags IBS/CBS
    - [ ] Adicionar grupos `<IBS>` e `<CBS>` no XML
    - [ ] Validar com schema oficial (quando disponível)
    - [ ] Testar assinatura digital
    - **Referência:** Aguardar NT SEFAZ sobre XML 5.0 ou extensão 4.01
    - **Deadline:** 28/03/2026

13. **Relatórios e Dashboards** (2 semanas)
    - [ ] Dashboard comparativo: "Antes LC 214 vs Depois"
    - [ ] Relatório de créditos acumulados (IBS/CBS)
    - [ ] Relatório de apuração mensal (substitui SPED)
    - [ ] Gráficos de carga tributária por produto
    - **Arquivos:**
      - `templates/admin/relatorios/comparativo_lc214.html`
      - `templates/admin/relatorios/creditos_ibs_cbs.html`
      - `routes/relatorios_lc214.py`
    - **Deadline:** 31/03/2026

---

### 🔵 FASE 4: REGIME DE TRANSIÇÃO (Abr-Jun/2026)
**Prazo:** 01/04/2026 - 30/06/2026  
**Responsável:** Equipe Completa  
**Status:** 🔴 NÃO INICIADO

#### Tarefas:

14. **Implementar Cálculo Híbrido 2026** (3 semanas)
    - [ ] Cálculo simultâneo: 80% antiga + 20% IBS/CBS (2026)
    - [ ] Ajustar percentuais progressivos até 2032
    - [ ] Criar tabela `percentuais_transicao_por_ano`
    - [ ] Validar fórmula de transição
    - **Fórmula 2026:**
      ```python
      imposto_total = (
          (ICMS + IPI) * 0.80 +  # 80% sistema antigo
          IBS * 0.20              # 20% IBS
      ) + (
          (PIS + COFINS) * 0.80 + # 80% sistema antigo
          CBS * 0.20              # 20% CBS
      )
      ```
    - **Deadline:** 21/04/2026

15. **Split Payment (Pagamento Dividido)** (4 semanas)
    - [ ] Pesquisar padrão técnico oficial (aguardar regulamentação)
    - [ ] Integrar com gateway de pagamento
    - [ ] Separar automaticamente: valor líquido + IBS + CBS
    - [ ] Gerar arquivo de remessa bancária específico
    - [ ] Testar com bancos homologados
    - **Referência:** Art. 392-A LC 214/2025
    - **Deadline:** 19/05/2026

16. **Sistema de Créditos Não-Cumulativos** (3 semanas)
    - [ ] Criar módulo de apuração de créditos
    - [ ] Integrar com controle de estoque (insumos)
    - [ ] Permitir lançamento manual de créditos
    - [ ] Gerar relatório de créditos acumulados
    - [ ] Exportar para declaração oficial
    - **Deadline:** 09/06/2026

17. **Integração com Comitê Gestor IBS** (2 semanas)
    - [ ] Pesquisar API oficial (quando disponível)
    - [ ] Implementar autenticação (certificado digital)
    - [ ] Enviar dados de apuração mensal
    - [ ] Receber validações e pendências
    - [ ] Criar log de comunicação
    - **Deadline:** 23/06/2026

18. **Testes Integrados e Homologação** (1 semana)
    - [ ] Testar 100 NFes reais em ambiente de homologação
    - [ ] Validar XML com SEFAZ (ambiente teste)
    - [ ] Testar split payment com banco de teste
    - [ ] Validar relatórios com contador
    - [ ] Corrigir bugs críticos
    - **Deadline:** 30/06/2026

---

### 🟣 FASE 5: TREINAMENTO E GO-LIVE (Jul/2026)
**Prazo:** 01/07/2026 - 31/07/2026  
**Responsável:** Suporte + Treinamento  
**Status:** 🔴 NÃO INICIADO

#### Tarefas:

19. **Treinamento de Usuários** (2 semanas)
    - [ ] Criar vídeos tutoriais (5-10 min cada)
    - [ ] Realizar 5 webinars ao vivo
    - [ ] Criar manual do usuário atualizado
    - [ ] Disponibilizar ambiente de testes para clientes
    - **Tópicos:**
      - "Como emitir NFe com IBS/CBS"
      - "Entendendo créditos não-cumulativos"
      - "Split payment na prática"
      - "Lendo relatórios comparativos"
    - **Deadline:** 14/07/2026

20. **Migração Gradual de Clientes** (2 semanas)
    - [ ] Migrar 10% dos clientes (piloto)
    - [ ] Coletar feedback e ajustar
    - [ ] Migrar 40% dos clientes
    - [ ] Migrar 50% restantes
    - **Estratégia:** Começar por clientes menores/menos complexos
    - **Deadline:** 28/07/2026

21. **Monitoramento Pós-Implantação** (contínuo)
    - [ ] Dashboard de erros em tempo real
    - [ ] Plantão de suporte 24/7 (primeira semana)
    - [ ] Hotfix para bugs críticos (SLA 4h)
    - [ ] Coletar métricas de uso
    - **KPIs:**
      - Taxa de erro na emissão de NFe
      - Tempo médio de processamento
      - Satisfação do cliente (NPS)
    - **Deadline:** 31/07/2026

---

## 🛠️ RECURSOS NECESSÁRIOS

### 👥 Equipe

| Função | Horas | Período |
|--------|-------|---------|
| Desenvolvedor Backend | 480h | Fev-Jul/2026 |
| Desenvolvedor Frontend | 320h | Mar-Jul/2026 |
| Analista de Dados | 160h | Jan-Fev/2026 |
| Contador/Especialista Fiscal | 80h | Dez-Jan/2026 |
| QA/Tester | 160h | Jun-Jul/2026 |
| Suporte | 240h | Jul-Ago/2026 |
| **TOTAL** | **1.440h** | **8 meses** |

### 💰 Investimento Estimado

| Item | Custo | Justificativa |
|------|-------|---------------|
| Horas de desenvolvimento | R$ 144.000 | 1.440h × R$ 100/h |
| Consultoria fiscal | R$ 20.000 | Validação técnica |
| Infraestrutura (servidores) | R$ 5.000 | Upgrade para suportar carga |
| Treinamento e materiais | R$ 8.000 | Vídeos, webinars, manuais |
| Certificados digitais | R$ 3.000 | Para integração oficial |
| Contingência (20%) | R$ 36.000 | Imprevistos |
| **TOTAL** | **R$ 216.000** | |

### 🖥️ Infraestrutura

- [ ] Upgrade PostgreSQL 14 → 16 (melhor performance)
- [ ] Adicionar Redis para cache de alíquotas
- [ ] Aumentar storage (logs de transição)
- [ ] Configurar ambiente de homologação separado
- [ ] Contratar CDN para relatórios pesados

---

## 📊 INDICADORES DE SUCESSO

### KPIs Técnicos

1. **Performance**
   - Tempo de cálculo IBS/CBS < 500ms
   - Tempo de emissão NFe < 3s
   - Disponibilidade do sistema > 99.5%

2. **Qualidade**
   - Taxa de erro na emissão < 1%
   - 0 bugs críticos em produção
   - Cobertura de testes > 80%

3. **Conformidade**
   - 100% das NFes com XML válido
   - 100% das alíquotas atualizadas
   - 0 multas por não conformidade

### KPIs de Negócio

1. **Adoção**
   - 100% dos clientes migrados até 31/07/2026
   - NPS > 8.0 após migração
   - < 5% de churn relacionado à mudança

2. **Suporte**
   - Tempo médio de atendimento < 30min
   - Taxa de resolução no primeiro contato > 70%
   - < 50 tickets/dia após estabilização

---

## ⚠️ RISCOS E MITIGAÇÕES

### 🔴 Riscos Críticos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Atraso na publicação de alíquotas oficiais | ALTA | ALTO | Manter placeholders, lançar versão beta em Jan |
| Mudança no formato XML NFe | MÉDIA | ALTO | Desenvolver adapter pattern, fácil ajuste |
| Bugs críticos no cálculo de impostos | MÉDIA | ALTO | Suite de testes robusta, validação com contador |
| Resistência de clientes à mudança | ALTA | MÉDIO | Comunicação clara, treinamento intensivo |
| Sobrecarga no suporte pós-implantação | ALTA | MÉDIO | Contratar suporte temporário, FAQ detalhado |

### 🟡 Riscos Médios

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Performance degradada (cálculos complexos) | MÉDIA | MÉDIO | Cache agressivo, otimização de queries |
| Incompatibilidade com SEFAZ | BAIXA | ALTO | Testar cedo em homologação, contato com SEFAZ |
| Falha no split payment | BAIXA | ALTO | Testes com múltiplos bancos, fallback manual |

---

## 📞 COMUNICAÇÃO DO PROJETO

### Stakeholders

1. **Clientes Finais** (usuários do sistema)
   - Canal: Email + webinars
   - Frequência: Mensal (dez-jul)
   - Responsável: Gerente de Contas

2. **Equipe Interna**
   - Canal: Daily standup + Slack
   - Frequência: Diária
   - Responsável: Tech Lead

3. **Contadores/Consultores**
   - Canal: Reuniões técnicas
   - Frequência: Quinzenal
   - Responsável: Especialista Fiscal

4. **Diretoria**
   - Canal: Report executivo
   - Frequência: Semanal
   - Responsável: Gerente de Projetos

### Calendário de Comunicados

- **15/12/2025:** Comunicado inicial sobre LC 214/2025
- **15/01/2026:** Convite para webinar explicativo
- **01/02/2026:** Divulgação do cronograma de migração
- **01/04/2026:** Liberação da versão beta (testes)
- **01/07/2026:** Início das migrações por lotes
- **15/07/2026:** Status report 50% migrado
- **31/07/2026:** Comunicado de conclusão 100%

---

## 📝 DOCUMENTAÇÃO A CRIAR

### Para Desenvolvedores

- [ ] `docs/API_IBS_CBS.md` - Documentação da API
- [ ] `docs/CALCULOS_TRIBUTARIOS_LC214.md` - Fórmulas detalhadas
- [ ] `docs/SCHEMA_DATABASE_IBS.md` - Modelo de dados
- [ ] `docs/GUIA_CONTRIBUICAO_LC214.md` - Para novos devs

### Para Usuários

- [ ] `MANUAL_USUARIO_IBS_CBS.pdf` - Manual completo
- [ ] `FAQ_LC214.md` - Perguntas frequentes
- [ ] `GLOSSARIO_REFORMA_TRIBUTARIA.md` - Termos técnicos
- [ ] `VIDEOS_TUTORIAIS.md` - Links e índice

### Para Conformidade

- [ ] `AUDITORIA_LC214_COMPLIANCE.md` - Checklist de conformidade
- [ ] `RELATORIO_VALIDACAO_CONTADOR.pdf` - Aprovação fiscal
- [ ] `CERTIFICADO_HOMOLOGACAO_SEFAZ.pdf` - Quando disponível

---

## 🎯 PRÓXIMOS PASSOS IMEDIATOS (Esta Semana)

### Segunda-feira (02/12/2025)
- [ ] Reunião de kickoff com toda equipe
- [ ] Criar projeto no Jira/Trello
- [ ] Definir responsáveis por cada fase

### Terça-feira (03/12/2025)
- [ ] Assinar newsletter do Comitê Gestor IBS
- [ ] Contatar contador para consultoria
- [ ] Iniciar análise de impacto nos clientes

### Quarta-feira (04/12/2025)
- [ ] Criar branch `lc214-migration` no Git
- [ ] Fazer backup completo do banco de dados
- [ ] Instalar Redis para cache

### Quinta-feira (05/12/2025)
- [ ] Reunião com cliente piloto (explicar mudanças)
- [ ] Começar comunicado oficial
- [ ] Pesquisar exemplos de XML IBS/CBS

### Sexta-feira (06/12/2025)
- [ ] Review semanal do progresso
- [ ] Ajustar cronograma se necessário
- [ ] Preparar apresentação para diretoria

---

## 📚 REFERÊNCIAS TÉCNICAS

### Legislação

- [Lei Complementar 214/2025](https://www.planalto.gov.br) - Texto oficial
- Cartilha IBS FENACON - Guia prático
- Resolução CMN (aguardar publicação) - Split payment
- IN RFB (aguardar) - CBS federal

### Tecnologias

- PostgreSQL 16 - Banco de dados
- Python 3.11+ - Backend
- SQLAlchemy 2.0 - ORM
- Redis 7.0 - Cache
- jQuery + Bootstrap - Frontend

### Consultorias

- FENACON - Federação Nacional das Empresas de Contabilidade
- SEFAZ/SP - Ambiente de homologação
- Comitê Gestor IBS - Portal oficial (quando disponível)

---

## ✅ CRITÉRIOS DE ACEITE FINAL

### Para considerar o projeto CONCLUÍDO (31/07/2026):

- [x] 100% dos clientes migrados para IBS/CBS
- [x] 0 bugs críticos em produção há 7 dias
- [x] Todas as NFes emitidas validadas pela SEFAZ
- [x] Relatórios de apuração aprovados por contadores
- [x] NPS médio dos clientes > 8.0
- [x] Documentação completa publicada
- [x] Treinamento de 90% dos usuários concluído
- [x] Split payment funcionando em 100% das operações
- [x] Sistema de créditos calculando corretamente
- [x] Auditoria fiscal sem apontamentos

---

## 🏆 MARCOS IMPORTANTES (MILESTONES)

```
Dez/2025  ████░░░░░░░░░░░░░░░░  FASE 1: Preparação
Jan/2026  ████████░░░░░░░░░░░░  FASE 2: Dados
Fev/2026  ████████████░░░░░░░░  FASE 3: Dev Backend
Mar/2026  ████████████████░░░░  FASE 3: Dev Frontend
Abr/2026  ████████████████████  FASE 4: Transição - Parte 1
Mai/2026  ████████████████████  FASE 4: Transição - Parte 2
Jun/2026  ████████████████████  FASE 4: Testes Finais
Jul/2026  ████████████████████  FASE 5: GO-LIVE 🚀
```

---

**Última atualização:** 30/11/2025  
**Responsável pelo plano:** Equipe Técnica API NFe  
**Aprovação pendente:** Diretoria + Contador responsável  
**Revisão:** Quinzenal

---

## 🚨 ATENÇÃO

Este plano será **revisado e atualizado** assim que:
1. Comitê Gestor IBS publicar alíquotas oficiais
2. SEFAZ divulgar novo schema XML
3. Receita Federal publicar IN sobre CBS
4. Houver mudanças na legislação LC 214/2025

**Mantenha este documento atualizado!**
