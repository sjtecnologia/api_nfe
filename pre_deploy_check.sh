#!/bin/bash

###############################################################################
# pre_deploy_check.sh - Validação PRÉ-DEPLOY de NF-e API
#
# PROPÓSITO:
#   Gate de segurança que verifica condições críticas ANTES de qualquer deploy
#   Previne regressions e protege contra duplicações/versões desatualizadas
#
# TRIGGERS:
#   - Deve ser executado POR TODO deploy (inutilizacao, fixes, lc214)
#   - Deve ser automatizado em CI/CD
#
# RETORNA:
#   0 = OK, seguro fazer deploy
#   1 = FALHA, deploy BLOQUEADO
#
###############################################################################

set -e  # Exit on any error

MODE="local"
if [ "${1:-}" = "--deploy" ]; then
    MODE="deploy"
fi

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CHECKS_PASSED=0
CHECKS_FAILED=0
CRITICAL_FAILS=0
FULL_SUITE_OK=0
CRITICAL_SUITE_OK=0
TEMPLATES_OK=0
ROLES_OK=0
JS_OK=0
SECRETS_OK=0
WORKTREE_OK=0

# Função para imprimir header
print_header() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Função para check individual
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

check_fail() {
    local severity=${2:-"WARN"}
    if [ "$severity" = "CRITICAL" ]; then
        echo -e "${RED}✗${NC} $1 ${RED}[CRITICAL]${NC}"
        CRITICAL_FAILS=$((CRITICAL_FAILS + 1))
    else
        echo -e "${YELLOW}⚠${NC} $1 ${YELLOW}[WARNING]${NC}"
    fi
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

###############################################################################
# 1. VERIFICAR GIT STATUS
###############################################################################

print_header "1️⃣  GIT STATUS - modo ${MODE}"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    check_fail "Não é um repositório git" "CRITICAL"
else
    if [ -z "$(git status --porcelain)" ]; then
        WORKTREE_OK=1
        check_pass "Working directory limpo"
    elif [ "$MODE" = "local" ]; then
        check_fail "Há alterações locais; permitido no modo local" "WARN"
        git status --short | head -20
    else
        check_fail "Há alterações não commitadas:" "CRITICAL"
        git status --short | head -20
    fi
fi

###############################################################################
# 2. VERIFICAR DUPLICAÇÕES E VERSÕES DESATUALIZADAS
###############################################################################

print_header "2️⃣  DUPLICAÇÃO DE ARQUIVOS - Verificar versões legadas"

# Verificar arquivo raiz (deve ser menor que routes/)
if [ -f "nfe_routes.py" ] && [ -f "routes/nfe_routes.py" ]; then
    SIZE_ROOT=$(wc -l < nfe_routes.py)
    SIZE_ROUTES=$(wc -l < routes/nfe_routes.py)
    
    if [ "$SIZE_ROUTES" -gt "$SIZE_ROOT" ]; then
        check_pass "routes/nfe_routes.py é mais recente (routes: $SIZE_ROUTES linhas > root: $SIZE_ROOT linhas)"
    else
        check_fail "nfe_routes.py (root) pode estar mais recente que routes/ (verificar datas)" "CRITICAL"
        ls -lh nfe_routes.py routes/nfe_routes.py | awk '{print $6, $7, $8, $9}'
    fi
    
    # Verificar comentário DEPRECATED
    if grep -q "DEPRECATED" nfe_routes.py; then
        check_pass "nfe_routes.py marcado como DEPRECATED"
    else
        check_fail "nfe_routes.py não está marcado como DEPRECATED" "WARN"
    fi
fi

# Verificar template legado
if [ -f "routes/emitir.html" ]; then
    if grep -q "DEPRECATED" routes/emitir.html; then
        check_pass "routes/emitir.html marcado como DEPRECATED"
    else
        check_fail "routes/emitir.html não está marcado como DEPRECATED" "WARN"
    fi
fi

###############################################################################
# 3. VERIFICAR TESTES CRÍTICOS
###############################################################################

print_header "3️⃣  TESTES CRÍTICOS - Executar regressão e validações"

if ! command -v python &> /dev/null; then
    check_fail "Python não encontrado no PATH" "CRITICAL"
else
    # Executar testes de regressão
    if [ -f "tests/test_nfe_critical_regression.py" ]; then
        echo "Executando testes críticos de regressão..."
        
        if python -m pytest tests/test_nfe_critical_regression.py -v --tb=short 2>&1 | tee /tmp/pytest_output.txt; then
            CRITICAL_SUITE_OK=1
            check_pass "Testes de regressão passaram"
        else
            check_fail "Testes de regressão FALHARAM" "CRITICAL"
            tail -30 /tmp/pytest_output.txt
        fi
    else
        check_fail "test_nfe_critical_regression.py não encontrado" "CRITICAL"
    fi
fi

###############################################################################
# 3B. COMPILAÇÃO PYTHON
###############################################################################

print_header "3️⃣B COMPILAÇÃO PYTHON - Arquivos críticos"

if [ -f "config/critical_files.txt" ]; then
    CRITICAL_PY_FILES=$(grep -vE '^[[:space:]]*(#|$)' config/critical_files.txt | grep '\.py$' || true)
    if python -m py_compile $CRITICAL_PY_FILES; then
        check_pass "Arquivos Python críticos compilam"
    else
        check_fail "Falha na compilação Python de arquivo crítico" "CRITICAL"
    fi
else
    check_fail "config/critical_files.txt não encontrado" "CRITICAL"
fi

###############################################################################
# 3C. SUÍTE 4.5B E JS
###############################################################################

print_header "3️⃣C SUÍTE 4.5B - Testes comportamentais e JavaScript"

if python -m pytest tests/test_phase_45b_hardening.py tests/test_nfe_critical_regression.py tests/test_phase_45c_security.py -q --tb=short; then
    check_pass "Suítes NF-e/Fase 4.5B passaram"
else
    check_fail "Suítes NF-e/Fase 4.5B falharam" "CRITICAL"
fi

if command -v node >/dev/null 2>&1 && node tests/check_critical_js_syntax.js; then
    JS_OK=1
    check_pass "JavaScript crítico passou na análise de sintaxe"
else
    check_fail "JavaScript crítico não passou na análise de sintaxe" "CRITICAL"
fi

###############################################################################
# 3D. URL_FOR E NFC-E
###############################################################################

print_header "3️⃣D ROTAS GLOBAIS E NFC-e"

if python -m pytest tests/test_phase_45b_hardening.py -q --tb=short; then
    TEMPLATES_OK=1
    check_pass "Templates globais, mapa de rotas e smoke NFC-e passaram"
else
    check_fail "Templates globais, mapa de rotas ou smoke NFC-e falharam" "CRITICAL"
fi

if python -m pytest tests/test_phase_45c_security.py -q --tb=short; then
    ROLES_OK=1
    check_pass "Matriz de roles e isolamento multiempresa passaram"
else
    check_fail "Matriz de roles ou isolamento multiempresa falharam" "CRITICAL"
fi

###############################################################################
# 3E. BROWSER SMOKE
###############################################################################

print_header "3️⃣E BROWSER SMOKE - Canário de homologação"

BROWSER_SMOKE_OK=0
if [ -f "tests/e2e/browser_smoke_playwright.js" ] && command -v node >/dev/null 2>&1; then
    set +e
    node tests/e2e/browser_smoke_playwright.js
    BROWSER_EXIT=$?
    set -e
    if [ "$BROWSER_EXIT" -eq 0 ]; then
        BROWSER_SMOKE_OK=1
        check_pass "Browser smoke passou"
    elif [ "$BROWSER_EXIT" -eq 78 ]; then
        check_fail "Browser smoke NOT_CONFIGURED: ambiente E2E não configurado" "CRITICAL"
    else
        check_fail "Browser smoke falhou" "CRITICAL"
    fi
else
    check_fail "Browser smoke não disponível" "CRITICAL"
fi

###############################################################################
# 3F. TESTES EXISTENTES DE IA E DOMÍNIO
###############################################################################

print_header "3️⃣E SUÍTES EXISTENTES - IA, produtos e vendas"

EXISTING_TESTS=(
    tests/test_auth_routes.py
    tests/test_admin_stub_permissions.py
    tests/test_admin_user_scope.py
    tests/test_danfe_download_route.py
    tests/test_nfce_reforma_tributaria.py
    tests/test_intelligence_data_layer.py
    tests/test_product_description_service.py
    tests/test_product_description_route.py
    tests/test_sales_analysis_service.py
    tests/test_ai_service.py
    tests/test_consultor_vendas_service.py
)
if python -m pytest "${EXISTING_TESTS[@]}" -q --tb=short; then
    check_pass "Suítes essenciais existentes passaram"
else
    check_fail "Uma suíte essencial existente falhou" "CRITICAL"
fi

###############################################################################
# 3G. SUÍTE COMPLETA
###############################################################################

print_header "3️⃣F SUÍTE COMPLETA - Todos os testes do projeto"

if python -m pytest -q --tb=short; then
    FULL_SUITE_OK=1
    check_pass "Suíte completa passou"
else
    check_fail "Suíte completa falhou" "CRITICAL"
fi

###############################################################################
# 4. VERIFICAR APP.PY - Blueprint correto
###############################################################################

print_header "4️⃣  BLUEPRINT CORRETO - Verificar app.py usa routes/nfe_routes"

if grep -q "from routes.nfe_routes import nfe_bp" app.py; then
    check_pass "app.py importa de routes.nfe_routes ✓"
elif grep -q "from nfe_routes import" app.py; then
    check_fail "app.py ainda importa de nfe_routes (raiz) — deve ser routes.nfe_routes" "CRITICAL"
else
    check_fail "Importação de nfe_bp não encontrada em app.py" "CRITICAL"
fi

###############################################################################
# 5. VERIFICAR TEMPLATES
###############################################################################

print_header "5️⃣  TEMPLATES - Verificar que arquivo ativo é usado"

# Verificar que templates/admin/nfes/emitir.html existe
if [ -f "templates/admin/nfes/emitir.html" ]; then
    check_pass "templates/admin/nfes/emitir.html (arquivo ativo) existe"
    
    # Verificar que tem action=emitir logic
    if grep -q "a.value='emitir\|a.value=\"emitir" templates/admin/nfes/emitir.html; then
        check_pass "Template ativo tem lógica action=emitir"
    else
        check_fail "Template ativo não tem criação de action=emitir" "CRITICAL"
    fi
    
    # Verificar que faz fetch para CSRF
    if grep -q "/api/csrf-token" templates/admin/nfes/emitir.html; then
        check_pass "Template ativo busca token CSRF renovado"
    else
        check_fail "Template ativo não busca CSRF token renovado" "CRITICAL"
    fi
    
    # Verificar submit nativo
    if grep -q "HTMLFormElement.prototype.submit.call" templates/admin/nfes/emitir.html; then
        check_pass "Template ativo usa submit nativo (não AJAX)"
    else
        check_fail "Template ativo não usa submit nativo" "CRITICAL"
    fi
else
    check_fail "templates/admin/nfes/emitir.html não encontrado" "CRITICAL"
fi

###############################################################################
# 6. VERIFICAR ENDPOINT CSRF
###############################################################################

print_header "6️⃣  ENDPOINT CSRF - Verificar /api/csrf-token existe"

if grep -q "def csrf_token_api\|@app.route('/api/csrf-token'" app.py; then
    check_pass "Endpoint /api/csrf-token está registrado em app.py"
else
    check_fail "Endpoint /api/csrf-token não encontrado em app.py" "CRITICAL"
fi

###############################################################################
# 7. VERIFICAR PERMISSÕES
###############################################################################

print_header "7️⃣  PERMISSÕES - Verificar decorators estão implementados"

if grep -q "@editor_or_admin_required\|@permission_required" routes/nfe_routes.py; then
    check_pass "routes/nfe_routes.py tem decorators de permissão"
else
    check_fail "routes/nfe_routes.py sem decorators de permissão" "WARN"
fi

###############################################################################
# 8. BACKUP
###############################################################################

print_header "8️⃣  BACKUP - Verificar que backup será criado"

if [ -f "deploy_inutilizacao_aws.sh" ] || [ -f "deploy_fixes_aws.sh" ] || [ -f "deploy_lc214_aws.sh" ]; then
    check_pass "Scripts de deploy encontrados e farão backup automático"
else
    check_fail "Nenhum script de deploy encontrado" "WARN"
fi

###############################################################################
# 9. VERIFICAR DOCUMENTAÇÃO
###############################################################################

print_header "9️⃣  DOCUMENTAÇÃO - Verificar que auditorias foram criadas"

if [ -f "docs/AUDITORIA_INCIDENTE_20260820.md" ]; then
    check_pass "AUDITORIA_INCIDENTE_20260820.md existe"
else
    check_fail "AUDITORIA_INCIDENTE_20260820.md não encontrado" "WARN"
fi

###############################################################################
# 10. SECRETS E CONFIGURAÇÃO DE RELEASE
###############################################################################

print_header "🔟 SECRETS - Bloquear arquivos sensíveis no modo deploy"

TRACKED_SENSITIVE=$(git ls-files \
    | grep -v '^ca-bundle-icpbrasil\.pem$' \
    | grep -v '^deployment/\.env\.template\.aws$' \
    | grep -E '(^|/)(\.env($|\.)|.*\.(pem|p12|pfx|key|crt)$)' || true)
if [ -n "$TRACKED_SENSITIVE" ]; then
    if [ "$MODE" = "deploy" ]; then
        check_fail "Arquivos sensíveis estão rastreados pelo Git:" "CRITICAL"
        printf '%s\n' "$TRACKED_SENSITIVE"
    else
        check_fail "Arquivos sensíveis rastreados; remediação necessária antes do deploy" "WARN"
    fi
else
    SECRETS_OK=1
    check_pass "Nenhum arquivo sensível rastreado pelo Git"
fi

if [ -f "docs/SECRETS_REMEDIATION.md" ]; then
    check_pass "Relatório de remediação de secrets existe"
else
    check_fail "docs/SECRETS_REMEDIATION.md não encontrado" "CRITICAL"
fi

if [ -f "docs/AUDITORIA_PROFUNDA_FASE_4_5.md" ]; then
    check_pass "AUDITORIA_PROFUNDA_FASE_4_5.md existe"
else
    check_fail "AUDITORIA_PROFUNDA_FASE_4_5.md não encontrado" "WARN"
fi

if [ -f "test_nfe_critical_regression.py" ] || [ -f "tests/test_nfe_critical_regression.py" ]; then
    check_pass "test_nfe_critical_regression.py existe"
else
    check_fail "test_nfe_critical_regression.py não encontrado" "CRITICAL"
fi

###############################################################################
# RESULTADO FINAL
###############################################################################

print_header "📊 RESULTADO PRÉ-DEPLOY"

echo -e "Verificações: ${GREEN}$CHECKS_PASSED passaram${NC}, ${YELLOW}$CHECKS_FAILED avisos${NC}, ${RED}$CRITICAL_FAILS críticas${NC}"
echo ""

echo "EMITEMAX RELEASE GATE"
echo "Critical regression: $([ $CRITICAL_SUITE_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "Full suite: $([ $FULL_SUITE_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "Roles: $([ $ROLES_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "Multi-tenant: $([ $ROLES_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "JavaScript: $([ $JS_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "Templates: $([ $TEMPLATES_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "Browser smoke: $([ $BROWSER_SMOKE_OK -eq 1 ] && echo PASS || echo NOT_CONFIGURED)"
echo "Secrets: $([ $SECRETS_OK -eq 1 ] && echo PASS || echo FAIL)"
echo "Working tree: $([ $WORKTREE_OK -eq 1 ] && echo PASS || echo FAIL)"
RELEASE_BLOCKED=0
if [ $CRITICAL_FAILS -gt 0 ] || [ $BROWSER_SMOKE_OK -ne 1 ] || [ -n "$TRACKED_SENSITIVE" ] || [ -n "$(git status --porcelain)" ]; then
    RELEASE_BLOCKED=1
fi
if [ $RELEASE_BLOCKED -eq 0 ]; then
    echo "FINAL: READY FOR HOMOLOGATION"
else
    echo "FINAL: BLOCKED"
fi
echo ""

if [ $RELEASE_BLOCKED -gt 0 ]; then
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}  ❌ DEPLOY BLOQUEADO - $CRITICAL_FAILS falhas críticas${NC}"
    echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "MOTIVOS DO BLOQUEIO:"
    [ -n "$TRACKED_SENSITIVE" ] && echo "  - Existem secrets/certificados rastreados pelo Git"
    [ -n "$(git status --porcelain)" ] && echo "  - Working tree não está no estado de release"
    [ $CRITICAL_FAILS -gt 0 ] && echo "  - Existem falhas críticas nos checks"
    echo ""
    echo "AÇÕES NECESSÁRIAS:"
    echo "  1. Revisar falhas críticas acima"
    echo "  2. Corrigir problemas localmente"
    echo "  3. Reexecutar ./pre_deploy_check.sh"
    echo "  4. Consultar /docs/AUDITORIA_PROFUNDA_FASE_4_5.md para detalhes"
    echo ""
    exit 1
else
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ READY FOR HOMOLOGATION${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "SEGURO PARA DEPLOY:"
    echo "  - Repositório limpo ✓"
    echo "  - Arquivos corretos identificados ✓"
    echo "  - Testes de regressão passaram ✓"
    echo "  - Configurações críticas validadas ✓"
    echo ""
    echo "PRÓXIMO PASSO:"
    echo "  ./deploy_inutilizacao_aws.sh    (ou outro script de deploy)"
    echo ""
    exit 0
fi
