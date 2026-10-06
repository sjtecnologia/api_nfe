"""Pré-flight seguro para homologação fiscal.

Este comando não transmite documentos e não altera banco. Ele só confirma que
o ambiente possui os artefatos mínimos antes de executar um smoke test real.
"""
from pathlib import Path
import os
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    migration_files = [
        ROOT / "database/migrations/016_create_fiscal_api_idempotency.sql",
        ROOT / "database/migrations/017_add_api_key_environment.sql",
        ROOT / "database/migrations/018_create_transport_documents.sql",
    ]
    checks.append(("migrations fiscais", all(path.exists() for path in migration_files)))
    checks.append(("documentação API fiscal", (ROOT / "docs/API_FISCAL.md").exists()))
    checks.append(("checklist de release", (ROOT / "deployment/CHECKLIST_RELEASE_FISCAL.md").exists()))
    checks.append(("adapter NFS-e Nacional", (ROOT / "services/nfse_sefin_nacional.py").exists()))

    cert_paths = [
        os.getenv("FISCAL_CERT_PATH"),
        os.getenv("SEFAZ_CERT_PATH"),
        os.getenv("NFSE_CERT_PATH"),
    ]
    configured_cert = next((Path(value) for value in cert_paths if value), None)
    checks.append(("certificado fiscal configurado", bool(configured_cert and configured_cert.exists())))
    checks.append(("ambiente explícito", os.getenv("FISCAL_ENVIRONMENT") in {"homologacao", "producao"}))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"{'OK' if ok else 'PENDENTE'}: {name}")
    if failed:
        print("Pré-flight não liberado; nenhum documento foi transmitido.", file=sys.stderr)
        return 1
    print("Pré-flight liberado para o smoke test controlado de homologação.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
