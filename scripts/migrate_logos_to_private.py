#!/usr/bin/env python3
"""
Migra logos legadas de static para armazenamento privado.

- Origem esperada: static/<logo_path>
- Destino: <PRIVATE_UPLOAD_FOLDER>/logos/
- Atualiza clientes.logo_path para formato: private:logos/<arquivo>

Uso:
  python scripts/migrate_logos_to_private.py --dry-run
  python scripts/migrate_logos_to_private.py
"""

import argparse
import os
import sys
import shutil
from datetime import datetime

from sqlalchemy import text

# Garante imports absolutos do projeto ao executar este script via scripts/.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.connection import SessionLocal

ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}


def private_logo_dir() -> str:
    base = os.getenv('PRIVATE_UPLOAD_FOLDER') or os.path.join('instance', 'private_uploads')
    target = os.path.join(base, 'logos')
    os.makedirs(target, exist_ok=True)
    return target


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Migracao de logos para storage privado')
    parser.add_argument('--dry-run', action='store_true', help='Simula migracao sem copiar/atualizar banco')
    parser.add_argument('--delete-source', action='store_true', help='Remove arquivo legado apos copia')
    return parser.parse_args()


def is_private_path(path_value: str) -> bool:
    return path_value.startswith('private:logos/')


def sanitize_old_logo_path(path_value: str) -> str:
    normalized = path_value.replace('\\', '/').lstrip('/')
    if '..' in normalized.split('/'):
        return ''
    return normalized


def generate_new_name(cliente_id: int, ext: str) -> str:
    token = os.urandom(8).hex()
    stamp = datetime.now().strftime('%Y%m%d%H%M%S')
    return f'cliente_{cliente_id}_{stamp}_{token}{ext}'


def main() -> int:
    args = parse_args()
    dry_run = args.dry_run
    delete_source = args.delete_source and not dry_run

    db = SessionLocal()

    scanned = 0
    migrated = 0
    skipped_private = 0
    skipped_invalid = 0
    missing_source = 0
    db_updates = 0
    errors = 0

    private_dir = private_logo_dir()

    try:
        rows = db.execute(text("""
            SELECT cliente_id, logo_path
            FROM clientes
            WHERE logo_path IS NOT NULL
              AND logo_path <> ''
            ORDER BY cliente_id
        """)).fetchall()

        for row in rows:
            scanned += 1
            cliente_id = int(row[0])
            logo_path = str(row[1])

            if is_private_path(logo_path):
                skipped_private += 1
                continue

            old_rel = sanitize_old_logo_path(logo_path)
            if not old_rel:
                skipped_invalid += 1
                print(f'[SKIP] cliente={cliente_id}: caminho invalido {logo_path}')
                continue

            ext = os.path.splitext(old_rel)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                skipped_invalid += 1
                print(f'[SKIP] cliente={cliente_id}: extensao nao permitida {ext}')
                continue

            src = os.path.join('static', old_rel)
            if not os.path.isfile(src):
                missing_source += 1
                print(f'[MISS] cliente={cliente_id}: arquivo nao encontrado {src}')
                continue

            new_name = generate_new_name(cliente_id, ext)
            dst = os.path.join(private_dir, new_name)
            new_logo_path = f'private:logos/{new_name}'

            try:
                if dry_run:
                    print(f'[DRY] cliente={cliente_id}: {src} -> {dst}')
                    migrated += 1
                    continue

                shutil.copy2(src, dst)
                db.execute(
                    text('UPDATE clientes SET logo_path = :new_logo WHERE cliente_id = :cid'),
                    {'new_logo': new_logo_path, 'cid': cliente_id},
                )
                db_updates += 1
                migrated += 1

                if delete_source:
                    try:
                        os.remove(src)
                    except OSError:
                        print(f'[WARN] cliente={cliente_id}: falha ao remover origem {src}')

                print(f'[OK] cliente={cliente_id}: migrado para {new_logo_path}')

            except Exception as exc:
                errors += 1
                print(f'[ERR] cliente={cliente_id}: {exc}')

        if dry_run:
            db.rollback()
        else:
            db.commit()

        print('\n=== RESUMO MIGRACAO LOGOS ===')
        print(f'scanned={scanned}')
        print(f'migrated={migrated}')
        print(f'db_updates={db_updates}')
        print(f'skipped_private={skipped_private}')
        print(f'skipped_invalid={skipped_invalid}')
        print(f'missing_source={missing_source}')
        print(f'errors={errors}')
        print(f'mode={"dry-run" if dry_run else "apply"}')

        return 0 if errors == 0 else 2

    finally:
        db.close()


if __name__ == '__main__':
    raise SystemExit(main())
