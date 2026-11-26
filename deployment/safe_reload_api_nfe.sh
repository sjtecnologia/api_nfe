#!/bin/bash
set -euo pipefail

SERVICE_NAME="api-nfe-principal"
LOCK_GLOB="/tmp/nfse_envio_*.lock"
LOCAL_URL="http://127.0.0.1:8080/"
PUBLIC_URL="https://api.emitemax.com.br/"
WAIT_SECONDS="${WAIT_SECONDS:-180}"
SLEEP_STEP=3

has_locks() {
  compgen -G "$LOCK_GLOB" > /dev/null
}

echo "[safe-reload] Verificando locks de envio NFSe..."
elapsed=0
while has_locks; do
  if [ "$elapsed" -ge "$WAIT_SECONDS" ]; then
    echo "[safe-reload] Timeout aguardando envio NFSe concluir (${WAIT_SECONDS}s)."
    echo "[safe-reload] Locks ativos:"
    ls -1 $LOCK_GLOB 2>/dev/null || true
    exit 1
  fi

  echo "[safe-reload] Envio NFSe em andamento. Aguardando... (${elapsed}s)"
  sleep "$SLEEP_STEP"
  elapsed=$((elapsed + SLEEP_STEP))
done

echo "[safe-reload] Sem envio em andamento. Executando reload gracioso..."
if sudo systemctl reload "$SERVICE_NAME"; then
  echo "[safe-reload] Reload executado com sucesso."
else
  echo "[safe-reload] Reload não suportado/falhou. Aplicando restart com fallback..."
  sudo systemctl restart "$SERVICE_NAME"
fi

sleep 2
if [ "$(sudo systemctl is-active "$SERVICE_NAME")" != "active" ]; then
  echo "[safe-reload] Serviço não ficou ativo após reload/restart."
  sudo systemctl status "$SERVICE_NAME" --no-pager -n 40 || true
  exit 1
fi

echo "[safe-reload] Healthcheck local..."
local_code=$(curl -sS -o /tmp/safe_reload_local.out -w "%{http_code}" "$LOCAL_URL" || true)
if [ -z "$local_code" ] || [ "$local_code" = "000" ]; then
  echo "[safe-reload] Falha no healthcheck local."
  exit 1
fi

echo "[safe-reload] Healthcheck público..."
public_code=$(curl -k -sS -o /tmp/safe_reload_public.out -w "%{http_code}" "$PUBLIC_URL" || true)
if [ -z "$public_code" ] || [ "$public_code" = "000" ]; then
  echo "[safe-reload] Falha no healthcheck público."
  exit 1
fi

echo "[safe-reload] OK local=$local_code publico=$public_code"
