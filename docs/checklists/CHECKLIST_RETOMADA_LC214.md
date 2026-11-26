# ✅ Checklist de Retomada - LC 214/2025

**Data de criação:** 30/11/2025  
**Branch ativa:** `lc214-migration`  
**Status:** Aguardando próximas ações

---

## 📋 O que já foi feito:

- [x] ✅ Branch `lc214-migration` criada
- [x] ✅ Script de backup criado (`scripts/backup_pre_lc214.sh`)
- [x] ✅ Comunicado para clientes criado (`comunicados/COMUNICADO_LC214_CLIENTES.md`)
- [x] ✅ Script de documentação criado (`scripts/documentar_regras_atuais.py`)
- [x] ✅ Plano de ação completo criado (`PLANO_ACAO_LC214_2025.md`)

---

## 🔄 Quando Retomar - Execute Nesta Ordem:

### 1️⃣ **PRIMEIRO: Fazer Backup** (5-10 min)
```bash
cd /Users/renato/Documents/Developement/api_nfe
./scripts/backup_pre_lc214.sh
```
**Resultado esperado:** Backup completo em `backups/backup_pre_lc214_XXXXXXXX_completo.tar.gz`

---

### 2️⃣ **SEGUNDO: Documentar Regras Atuais** (2-5 min)
```bash
python3 scripts/documentar_regras_atuais.py
```
**Resultado esperado:** 4 arquivos em `documentacao/pre_lc214/`:
- CSV (planilha)
- JSON (estruturado)
- Markdown (relatório)
- SQL (recriação)

---

### 3️⃣ **TERCEIRO: Personalizar Comunicado** (15-30 min)

Editar `comunicados/COMUNICADO_LC214_CLIENTES.md` e substituir:

- [ ] `[Nome da Sua Empresa]` → Nome real da empresa
- [ ] `seudominio.com.br` → Domínio real
- [ ] `(11) 0000-0000` → Telefones reais
- [ ] `suporte@seudominio.com.br` → Email real
- [ ] `[Link de inscrição]` → Links dos webinars (criar no Google Meet/Zoom)
- [ ] `[Link da pesquisa: forms.google.com/xxxxx]` → Criar Google Form

---

### 4️⃣ **QUARTO: Agendar Reuniões** (30 min)

- [ ] Reunião com contador (discutir LC 214/2025)
- [ ] Reunião interna com equipe (kickoff)
- [ ] Agendar webinars de Janeiro/2026:
  - 10/01/2026 às 14h - "Entendendo a LC 214/2025"
  - 17/01/2026 às 14h - "Como usar o novo sistema"
  - 24/01/2026 às 14h - "Créditos Não-Cumulativos"

---

### 5️⃣ **QUINTO: Monitorar Legislação** (Diário)

Sites para acompanhar:
- [ ] [Portal Comitê Gestor IBS](https://www.ibs.gov.br) (quando disponível)
- [ ] [Receita Federal - CBS](https://www.gov.br/receitafederal)
- [ ] [CONFAZ](https://www.confaz.fazenda.gov.br)
- [ ] [FENACON](https://fenacon.org.br)

**Configure alertas Google para:**
- "alíquotas IBS 2026"
- "CBS receita federal"
- "Lei Complementar 214"

---

### 6️⃣ **SEXTO: Criar Formulário de Pesquisa** (20 min)

**Google Forms com 4 perguntas:**

1. Qual seu nível de conhecimento sobre a LC 214/2025?
   - [ ] Nunca ouvi falar
   - [ ] Já ouvi falar mas não entendo
   - [ ] Entendo o básico
   - [ ] Entendo bem

2. Você já conversou com seu contador sobre o tema?
   - [ ] Sim
   - [ ] Não
   - [ ] Vou agendar

3. Qual sua principal dúvida/preocupação?
   - [ ] Campo aberto

4. Prefere treinamento online ou presencial?
   - [ ] Online (webinar)
   - [ ] Presencial
   - [ ] Ambos

**Após criar, adicionar link no comunicado!**

---

## 📅 Calendário de Eventos Importantes

### Dezembro/2025
- **02/12:** Enviar comunicado para clientes
- **10/12:** Deadline para pesquisa de impacto
- **15/12:** Reunião com contador
- **20/12:** Backup e documentação concluídos
- **31/12:** Fase 1 completa

### Janeiro/2026
- **07/01:** Importar alíquotas oficiais (quando disponíveis)
- **10/01:** Webinar 1
- **17/01:** Webinar 2
- **24/01:** Webinar 3
- **31/01:** Fase 2 completa

---

## 🔗 Links Rápidos

### Arquivos Importantes
- [Plano de Ação Completo](./PLANO_ACAO_LC214_2025.md)
- [Comunicado Clientes](./comunicados/COMUNICADO_LC214_CLIENTES.md)
- [Script Backup](./scripts/backup_pre_lc214.sh)
- [Script Documentação](./scripts/documentar_regras_atuais.py)

### Branches Git
- Branch atual: `lc214-migration`
- Branch anterior: `copilot/vscode1759248218459`
- Branch principal: `main`

### Comandos Úteis
```bash
# Ver branch atual
git branch

# Voltar para branch anterior (se necessário)
git checkout copilot/vscode1759248218459

# Voltar para branch LC214
git checkout lc214-migration

# Ver commits recentes
git log --oneline -5

# Status atual
git status
```

---

## ⏰ Próxima Sessão de Trabalho

Quando retomar, comece por:

1. ✅ Ler este checklist
2. ✅ Executar backup (item 1️⃣)
3. ✅ Executar documentação (item 2️⃣)
4. ✅ Revisar resultados
5. ✅ Decidir próximos passos

**Tempo estimado:** 30-60 minutos

---

## 📞 Contatos de Emergência

(Preencher quando relevante)

- **Contador responsável:** _______________
- **Gerente de TI:** _______________
- **Suporte SEFAZ:** _______________

---

## 💾 Backup de Segurança

Antes de fazer QUALQUER alteração no banco:
```bash
./scripts/backup_pre_lc214.sh
```

**Nunca mexa no banco sem backup recente!**

---

## 🎯 Meta da Fase 1 (Dezembro/2025)

- [ ] Todos os clientes notificados
- [ ] Contador consultado
- [ ] Backup completo realizado
- [ ] Documentação das regras atuais completa
- [ ] Pesquisa de impacto respondida por 80% dos clientes
- [ ] Webinars agendados
- [ ] Material educativo disponibilizado

**Conclusão prevista:** 31/12/2025

---

**Última atualização:** 30/11/2025 às 23:45  
**Próxima revisão:** Quando retomar o trabalho

**Boa sorte! 🚀**
