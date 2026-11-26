#!/usr/bin/env bash
set -u

# Healthcheck IA - Local e EC2
# Uso:
#   scripts/healthcheck_ia.sh
#   scripts/healthcheck_ia.sh --mode local
#   scripts/healthcheck_ia.sh --mode remote --remote-host ubuntu@100.26.12.107 --ssh-key ~/Downloads/nfe-new-api-key.pem

MODE="local"
REMOTE_HOST=""
SSH_KEY=""
TIMEOUT="30"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"
      shift 2
      ;;
    --remote-host)
      REMOTE_HOST="$2"
      shift 2
      ;;
    --ssh-key)
      SSH_KEY="$2"
      shift 2
      ;;
    --timeout)
      TIMEOUT="$2"
      shift 2
      ;;
    -h|--help)
      echo "Uso:"
      echo "  scripts/healthcheck_ia.sh [--mode local]"
      echo "  scripts/healthcheck_ia.sh --mode remote --remote-host ubuntu@IP --ssh-key /caminho/chave.pem"
      exit 0
      ;;
    *)
      echo "[FAIL] Argumento desconhecido: $1"
      exit 2
      ;;
  esac
done

FAILED=0

ok() {
  echo "[OK] $1"
}

fail() {
  echo "[FAIL] $1"
  FAILED=1
}

warn() {
  echo "[WARN] $1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Comando ausente: $1"
  fi
}

check_http_json() {
  local name="$1"
  local url="$2"
  local payload="$3"

  local http_code
  http_code=$(curl -sS -m "$TIMEOUT" -o /tmp/healthcheck_ia_body.json -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -X POST "$url" \
    -d "$payload" 2>/tmp/healthcheck_ia_err.log)

  if [[ "$http_code" == "200" ]]; then
    ok "$name retornou HTTP 200"
  else
    local body
    body=$(head -c 220 /tmp/healthcheck_ia_body.json 2>/dev/null || true)
    local err
    err=$(head -c 220 /tmp/healthcheck_ia_err.log 2>/dev/null || true)
    fail "$name retornou HTTP $http_code | body: ${body:-vazio} | err: ${err:-vazio}"
  fi
}

run_local() {
  echo "== Healthcheck IA (local) =="
  require_cmd curl

  check_http_json \
    "Sugestao IA" \
    "http://127.0.0.1:8081/sugestao" \
    '{"descricao":"Caneta esferografica azul","tipo_item":"Produto","unidade_comercial":"UN"}'

  check_http_json \
    "Validacao regra IA" \
    "http://127.0.0.1:8081/valida/regra" \
    '{"regime_tributario":"Simples Nacional","cfop":"5102","csosn_icms":"102","ncm":"96081000","descricao":"Caneta"}'
}

run_remote() {
  echo "== Healthcheck IA (remoto) =="
  if [[ -z "$REMOTE_HOST" ]]; then
    fail "Informe --remote-host para modo remote"
    return
  fi

  if [[ -z "$SSH_KEY" ]]; then
    fail "Informe --ssh-key para modo remote"
    return
  fi

  if ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "sudo systemctl is-active api-nfe-ia.service" >/tmp/healthcheck_ia_remote_ia.txt 2>&1; then
    ok "api-nfe-ia.service ativo"
  else
    fail "api-nfe-ia.service inativo"
  fi

  if ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "sudo systemctl is-active api-nfe-principal.service" >/tmp/healthcheck_ia_remote_principal.txt 2>&1; then
    ok "api-nfe-principal.service ativo"
  else
    fail "api-nfe-principal.service inativo"
  fi

  if ssh -i "$SSH_KEY" -o BatchMode=yes "$REMOTE_HOST" "python3 - <<'PY'
import requests

checks = [
  (
    'Sugestao IA',
    'http://127.0.0.1:8081/sugestao',
    {'descricao':'Caneta esferografica azul','tipo_item':'Produto','unidade_comercial':'UN'}
  ),
  (
    'Validacao regra IA',
    'http://127.0.0.1:8081/valida/regra',
    {'regime_tributario':'Simples Nacional','cfop':'5102','csosn_icms':'102','ncm':'96081000','descricao':'Caneta'}
  ),
]

failed = 0
for name, url, payload in checks:
    try:
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code == 200:
            print(f'[OK] {name} retornou HTTP 200')
        else:
            failed = 1
            body = (resp.text or '')[:220].replace('\n', ' ')
            print(f'[FAIL] {name} retornou HTTP {resp.status_code} | body: {body}')
    except Exception as exc:
        failed = 1
        print(f'[FAIL] {name} erro: {type(exc).__name__} {exc}')

raise SystemExit(failed)
PY"; then
    ok "Endpoints remotos de IA responderam conforme esperado"
  else
    fail "Falha em um ou mais endpoints remotos de IA"
  fi
}

case "$MODE" in
  local)
    run_local
    ;;
  remote)
    run_remote
    ;;
  *)
    fail "Modo invalido: $MODE (use local ou remote)"
    ;;
esac

if [[ "$FAILED" -eq 0 ]]; then
  echo "RESULTADO: OK"
  exit 0
fi

echo "RESULTADO: FALHA"
exit 1
