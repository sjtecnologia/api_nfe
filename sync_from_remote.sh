#!/bin/bash
set -e
REMOTE="origin/lc214-migration"

files=(
  "models/user.py"
  "auth/login_manager.py"
  "auth/decorators.py"
  "database/models.py"
  "routes/admin_routes.py"
  "routes/auth_routes.py"
  "routes/cliente_routes.py"
  "routes/home_routes.py"
  "routes/nfe_routes.py"
  "routes/api_routes.py"
  "routes/api_v2_routes.py"
  "routes/api_keys_routes.py"
  "app.py"
)

for f in "${files[@]}"; do
  git show "$REMOTE:$f" > "$f" && echo "OK: $f"
done

echo "=== Todos os arquivos sincronizados ==="
