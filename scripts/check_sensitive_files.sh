#!/bin/sh

# Bloqueia arquivos privados novos no working tree ou no índice do Git.
# Não imprime conteúdo, apenas caminhos.

set -u

blocked=0
for path in $(git ls-files --cached --others --exclude-standard 2>/dev/null); do
    case "$path" in
        .env|.env.*|*.key|*.p12|*.pfx|*.pem)
            case "$path" in
                ca-bundle-icpbrasil.pem) ;;
                *)
                    printf 'SENSITIVE_FILE=%s\n' "$path"
                    blocked=1
                    ;;
            esac
            ;;
    esac
done

if [ "$blocked" -ne 0 ]; then
    printf '%s\n' 'Sensitive files detected; review rotation and Git index.'
    exit 1
fi

printf '%s\n' 'No blocked sensitive files detected.'
exit 0
