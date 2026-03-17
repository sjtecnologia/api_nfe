#!/usr/bin/env python3
"""Script para corrigir classes Bootstrap 5 nos templates, tornando-os compatíveis com Bootstrap 4."""
import re
from pathlib import Path

templates_dir = Path('/Users/renato/Documents/Developement/api_nfe/templates')

# Use regex com \b (word boundary) para substituir apenas palavras inteiras
REGEX_REPLACEMENTS = [
    # Typography
    (r'\bfw-bold\b', 'font-weight-bold'),
    (r'\bfw-semibold\b', 'font-weight-600'),
    (r'\bfw-normal\b', 'font-weight-normal'),
    (r'\bfw-light\b', 'font-weight-light'),
    # Float
    (r'\bfloat-end\b', 'float-right'),
    (r'\bfloat-start\b', 'float-left'),
    # Text alignment
    (r'\btext-end\b', 'text-right'),
    (r'\btext-start\b', 'text-left'),
    # Borders - padroes especificos de card com borda colorida (mais especificos primeiro)
    (r'card border-start border-primary border-4', 'card border-left border-left-primary'),
    (r'card border-start border-success border-4', 'card border-left border-left-success'),
    (r'card border-start border-info border-4', 'card border-left border-left-info'),
    (r'card border-start border-warning border-4', 'card border-left border-left-warning'),
    (r'card border-start border-danger border-4', 'card border-left border-left-danger'),
    (r'card border-start border-secondary border-4', 'card border-left border-left-secondary'),
    (r'card border-start border-dark border-4', 'card border-left border-left-dark'),
    (r'\bborder-start\b', 'border-left'),
    (r'\bborder-end\b', 'border-right'),
    # Close button
    (r'\bbtn-close\b', 'close'),
    # Form controls
    (r'\bform-select\b', 'form-control'),
    (r'\bform-switch\b', 'custom-switch'),
    # Badge
    (r'\bbadge bg-primary\b', 'badge badge-primary'),
    (r'\bbadge bg-secondary\b', 'badge badge-secondary'),
    (r'\bbadge bg-success\b', 'badge badge-success'),
    (r'\bbadge bg-danger\b', 'badge badge-danger'),
    (r'\bbadge bg-warning\b', 'badge badge-warning'),
    (r'\bbadge bg-info\b', 'badge badge-info'),
    (r'\bbadge bg-light\b', 'badge badge-light'),
    (r'\bbadge bg-dark\b', 'badge badge-dark'),
    # Margin end/start
    (r'\bme-0\b', 'mr-0'), (r'\bme-1\b', 'mr-1'), (r'\bme-2\b', 'mr-2'),
    (r'\bme-3\b', 'mr-3'), (r'\bme-4\b', 'mr-4'), (r'\bme-5\b', 'mr-5'),
    (r'\bme-auto\b', 'mr-auto'),
    (r'\bms-0\b', 'ml-0'), (r'\bms-1\b', 'ml-1'), (r'\bms-2\b', 'ml-2'),
    (r'\bms-3\b', 'ml-3'), (r'\bms-4\b', 'ml-4'), (r'\bms-5\b', 'ml-5'),
    (r'\bms-auto\b', 'ml-auto'),
    # Padding end/start
    (r'\bpe-0\b', 'pr-0'), (r'\bpe-1\b', 'pr-1'), (r'\bpe-2\b', 'pr-2'),
    (r'\bpe-3\b', 'pr-3'), (r'\bpe-4\b', 'pr-4'), (r'\bpe-5\b', 'pr-5'),
    (r'\bps-0\b', 'pl-0'), (r'\bps-1\b', 'pl-1'), (r'\bps-2\b', 'pl-2'),
    (r'\bps-3\b', 'pl-3'), (r'\bps-4\b', 'pl-4'), (r'\bps-5\b', 'pl-5'),
    # flex-wrap para todos d-flex justify-content-between que nao tem ainda
    (r'\bd-flex justify-content-between\b(?! flex-wrap)', 'd-flex flex-wrap justify-content-between'),
]

compiled = [(re.compile(pat), repl) for pat, repl in REGEX_REPLACEMENTS]

count = 0
modified_files = []

for fpath in templates_dir.rglob('*.html'):
    try:
        original = fpath.read_text(encoding='utf-8')
        content = original
        for pattern, replacement in compiled:
            content = pattern.sub(replacement, content)
        if content != original:
            fpath.write_text(content, encoding='utf-8')
            count += 1
            modified_files.append(str(fpath.relative_to(templates_dir)))
    except Exception as exc:
        print(f'Erro em {fpath}: {exc}')

print(f'\nArquivos modificados: {count}')
for f in sorted(modified_files):
    print(f'  - {f}')


# Use regex com \b (word boundary) para substituir apenas palavras inteiras
REGEX_REPLACEMENTS = [
    # Typography
    (r'\bfw-bold\b', 'font-weight-bold'),
    (r'\bfw-semibold\b', 'font-weight-600'),
    (r'\bfw-normal\b', 'font-weight-normal'),
    (r'\bfw-light\b', 'font-weight-light'),
    # Float
    (r'\bfloat-end\b', 'float-right'),
    (r'\bfloat-start\b', 'float-left'),
    # Text alignment
    (r'\btext-end\b', 'text-right'),
    (r'\btext-start\b', 'text-left'),
    # Borders - padroes especificos de card com borda colorida (mais especificos primeiro)
    (r'card border-start border-primary border-4', 'card border-left border-left-primary'),
    (r'card border-start border-success border-4', 'card border-left border-left-success'),
    (r'card border-start border-info border-4', 'card border-left border-left-info'),
    (r'card border-start border-warning border-4', 'card border-left border-left-warning'),
    (r'card border-start border-danger border-4', 'card border-left border-left-danger'),
    (r'card border-start border-secondary border-4', 'card border-left border-left-secondary'),
    (r'card border-start border-dark border-4', 'card border-left border-left-dark'),
    (r'\bborder-start\b', 'border-left'),
    (r'\bborder-end\b', 'border-right'),
    # Close button
    (r'\bbtn-close\b', 'close'),
    # Form controls
    (r'\bform-select\b', 'form-control'),
    (r'\bform-switch\b', 'custom-switch'),
    # Badge
    (r'\bbadge bg-primary\b', 'badge badge-primary'),
    (r'\bbadge bg-secondary\b', 'badge badge-secondary'),
    (r'\bbadge bg-success\b', 'badge badge-success'),
    (r'\bbadge bg-danger\b', 'badge badge-danger'),
    (r'\bbadge bg-warning\b', 'badge badge-warning'),
    (r'\bbadge bg-info\b', 'badge badge-info'),
    (r'\bbadge bg-light\b', 'badge badge-light'),
    (r'\bbadge bg-dark\b', 'badge badge-dark'),
    # Margin end/start
    (r'\bme-0\b', 'mr-0'), (r'\bme-1\b', 'mr-1'), (r'\bme-2\b', 'mr-2'),
    (r'\bme-3\b', 'mr-3'), (r'\bme-4\b', 'mr-4'), (r'\bme-5\b', 'mr-5'),
    (r'\bme-auto\b', 'mr-auto'),
    (r'\bms-0\b', 'ml-0'), (r'\bms-1\b', 'ml-1'), (r'\bms-2\b', 'ml-2'),
    (r'\bms-3\b', 'ml-3'), (r'\bms-4\b', 'ml-4'), (r'\bms-5\b', 'ml-5'),
    (r'\bms-auto\b', 'ml-auto'),
    # Padding end/start
    (r'\bpe-0\b', 'pr-0'), (r'\bpe-1\b', 'pr-1'), (r'\bpe-2\b', 'pr-2'),
    (r'\bpe-3\b', 'pr-3'), (r'\bpe-4\b', 'pr-4'), (r'\bpe-5\b', 'pr-5'),
    (r'\bps-0\b', 'pl-0'), (r'\bps-1\b', 'pl-1'), (r'\bps-2\b', 'pl-2'),
    (r'\bps-3\b', 'pl-3'), (r'\bps-4\b', 'pl-4'), (r'\bps-5\b', 'pl-5'),
]

compiled = [(re.compile(pat), repl) for pat, repl in REGEX_REPLACEMENTS]

count = 0
modified_files = []

for fpath in templates_dir.rglob('*.html'):
    try:
        original = fpath.read_text(encoding='utf-8')
        content = original
        for pattern, replacement in compiled:
            content = pattern.sub(replacement, content)
        if content != original:
            fpath.write_text(content, encoding='utf-8')
            count += 1
            modified_files.append(str(fpath.relative_to(templates_dir)))
    except Exception as exc:
        print(f'Erro em {fpath}: {exc}')

print(f'\nArquivos modificados: {count}')
for f in sorted(modified_files):
    print(f'  - {f}')

