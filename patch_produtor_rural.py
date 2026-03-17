#!/usr/bin/env python3
"""
Patch cirurgico - Suporte a Produtor Rural (CPF sem CNPJ) no servidor.
Aplica mudancas em: models.py, nfe_routes.py, nfe_service.py,
                    admin_routes.py, templates/admin/clientes/form.html
"""
import os, re, sys

BASE = '/home/ubuntu/api_nfe'
ERRORS = []

def read_file(path):
    with open(os.path.join(BASE, path), 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(os.path.join(BASE, path), 'w', encoding='utf-8') as f:
        f.write(content)

def patch_re(path, pattern, replacement, description, flags=re.MULTILINE):
    content = read_file(path)
    new_content, count = re.subn(pattern, replacement, content, flags=flags)
    if count == 0:
        print(f'  [SKIP] {description} - padrao nao encontrado (ja aplicado?)')
        return False
    write_file(path, new_content)
    print(f'  [OK]   {description} ({count} substituicao)')
    return True

def patch_str(path, old, new, description):
    content = read_file(path)
    if old not in content:
        print(f'  [SKIP] {description} - string nao encontrada (ja aplicado?)')
        return False
    new_content = content.replace(old, new, 1)
    write_file(path, new_content)
    print(f'  [OK]   {description}')
    return True

# ─────────────────────────────────────────────────────────────
# 1. database/models.py
# ─────────────────────────────────────────────────────────────
print('\n=== 1. database/models.py ===')

# 1a. cnpj nullable=False -> True
patch_re(
    'database/models.py',
    r'(cnpj = Column\(String\(18\), unique=True, nullable=)False\)',
    r'\1True)',
    'cnpj nullable=True'
)

# 1b. Adicionar cpf e produtor_rural apos cnpj se nao existirem
content = read_file('database/models.py')
if 'produtor_rural = Column(Boolean' not in content:
    new_content = re.sub(
        r'(    cnpj = Column\(String\(18\), unique=True, nullable=True\)\n)',
        r'\1    cpf = Column(String(14), unique=True, nullable=True)\n    produtor_rural = Column(Boolean, default=False, nullable=False)\n',
        content
    )
    write_file('database/models.py', new_content)
    print('  [OK]   adicionar cpf e produtor_rural ao modelo Cliente')
else:
    print('  [SKIP] cpf/produtor_rural ja existem no modelo')

# ─────────────────────────────────────────────────────────────
# 2. routes/nfe_routes.py - validacao CNPJ emitente
# ─────────────────────────────────────────────────────────────
print('\n=== 2. routes/nfe_routes.py - validacao CNPJ ===')

patch_re(
    'routes/nfe_routes.py',
    r'(        # VALIDAR CNPJ DO EMITENTE\n)(        cnpj_emitente_limpo = emitente_data\.cnpj\.replace.*?\n        print\(f"🔍 \[VALIDAÇÃO\] CNPJ emitente:.*?\n        if not validar_cnpj\(cnpj_emitente_limpo\):\n            print\(f"❌.*?\n            flash\(f\'CNPJ do emitente.*?\n            return redirect\(url_for\(\'home\.home\'\)\)\n        print\(f"✅ \[VALIDAÇÃO\] CNPJ emitente válido"\))',
    r"""\1        if getattr(emitente_data, 'produtor_rural', False):
            print(f"\u2705 [VALIDA\u00c7\u00c3O] Emitente \u00e9 Produtor Rural (CPF), pulando valida\u00e7\u00e3o CNPJ")
        else:
            cnpj_emitente_limpo = (emitente_data.cnpj or '').replace('.', '').replace('/', '').replace('-', '').strip()
            print(f"\U0001f50d [VALIDA\u00c7\u00c3O] CNPJ emitente: {cnpj_emitente_limpo}")
            if not validar_cnpj(cnpj_emitente_limpo):
                print(f"\u274c [VALIDA\u00c7\u00c3O] CNPJ EMITENTE INV\u00c1LIDO: {cnpj_emitente_limpo}")
                flash(f'CNPJ do emitente \u00e9 inv\u00e1lido: {emitente_data.cnpj}. Corrija o cadastro do cliente antes de emitir NFe.', 'danger')
                return redirect(url_for('home.home'))
            print(f"\u2705 [VALIDA\u00c7\u00c3O] CNPJ emitente v\u00e1lido")""",
    'bypass validacao CNPJ para produtor rural',
    flags=re.DOTALL
)

# ─────────────────────────────────────────────────────────────
# 3. routes/nfe_routes.py - emitente_data_for_template
# ─────────────────────────────────────────────────────────────
print('\n=== 3. routes/nfe_routes.py - emitente_data_for_template ===')

patch_re(
    'routes/nfe_routes.py',
    r"('cnpj': emitente_data\.cnpj,\n)(\s+'nome_fantasia': emitente_data\.nome_fantasia,)",
    r"""\1            'cpf': getattr(emitente_data, 'cpf', None),
            'produtor_rural': getattr(emitente_data, 'produtor_rural', False),
\2""",
    'adicionar cpf e produtor_rural ao emitente_data_for_template'
)

# ─────────────────────────────────────────────────────────────
# 4. services/nfe_service.py - cnpj_emit para chave de acesso
# ─────────────────────────────────────────────────────────────
print('\n=== 4. services/nfe_service.py - cnpj_emit para chave de acesso ===')

patch_re(
    'services/nfe_service.py',
    r"(        cnpj_emit = emitente_data\.get\('cnpj', ''\)\.replace\('\.', ''\)\.replace\('/', ''\)\.replace\('-', ''\))",
    r"""        if emitente_data.get('produtor_rural'):
            cpf_raw = (emitente_data.get('cpf') or '').replace('.', '').replace('-', '')
            cnpj_emit = cpf_raw.zfill(14)  # CPF padded a 14 digitos para chave de acesso
        else:
            cnpj_emit = emitente_data.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')""",
    'cnpj_emit: CPF padded para produtor rural'
)

# ─────────────────────────────────────────────────────────────
# 5. services/nfe_service.py - XML emit CNPJ -> CPF condicional
# ─────────────────────────────────────────────────────────────
print('\n=== 5. services/nfe_service.py - XML emit CNPJ/CPF ===')

patch_re(
    'services/nfe_service.py',
    r'(        etree\.SubElement\(emit, "CNPJ"\)\.text = cnpj_emit\n)(        etree\.SubElement\(emit, "xNome"\))',
    r"""        if emitente_data.get('produtor_rural'):
            cpf_emit = (emitente_data.get('cpf') or '').replace('.', '').replace('-', '')
            etree.SubElement(emit, "CPF").text = cpf_emit
        else:
            etree.SubElement(emit, "CNPJ").text = cnpj_emit
\2""",
    'XML emit: CPF para produtor rural, CNPJ para empresa'
)

# ─────────────────────────────────────────────────────────────
# 6. admin_routes.py - create_cliente
# ─────────────────────────────────────────────────────────────
print('\n=== 6. admin_routes.py - create_cliente ===')

# 6a. Adicionar limpeza CPF apos cnpj_limpo no create_cliente (logo_path = None eh marcador unico)
patch_re(
    'routes/admin_routes.py',
    r"(            cnpj_limpo = ''.join\(filter\(str\.isdigit, cnpj_raw\)\)\n\n)(            # Processar upload da logo \(se enviada\)\n            logo_path = None)",
    r"""\1            # Limpar CPF (remover formatacao)
            cpf_raw = request.form.get('cpf', '')
            cpf_limpo = ''.join(filter(str.isdigit, cpf_raw)) or None

\2""",
    'create_cliente: limpeza CPF'
)

# 6b. Adicionar cpf/produtor_rural ao data dict do create_cliente
# Identificador unico: 'created_by_user_id': current_user.id com data_cadastro antes
patch_re(
    'routes/admin_routes.py',
    r"(                'cnpj': cnpj_limpo,  # Limpo\n)(                'inscricao_estadual': request\.form\.get\('inscricao_estadual'\),)",
    r"""\1                'cpf': cpf_limpo,
                'produtor_rural': request.form.get('produtor_rural') == 'on',
\2""",
    'create_cliente: cpf e produtor_rural no data dict'
)

# 6c. Atualizar INSERT para incluir cpf e produtor_rural
patch_re(
    'routes/admin_routes.py',
    r'(                    INSERT INTO clientes \(\n                        razao_social, nome_fantasia, cnpj,)(.*?)(                    \) RETURNING cliente_id)',
    lambda m: (
        m.group(0) if 'cpf,' in m.group(0) else
        m.group(1).rstrip() + ' cpf, produtor_rural,' + m.group(2) +
        m.group(3)
    ) if False else None,  # placeholder - usa abordagem diferente abaixo
    'SKIP (usando patch direto)',
    flags=re.DOTALL
)

# Nova abordagem para INSERT
content = read_file('routes/admin_routes.py')
insert_marker = 'razao_social, nome_fantasia, cnpj, inscricao_estadual, inscricao_municipal,'
if insert_marker in content and 'cpf, produtor_rural,' not in content.split(insert_marker)[0][-200:]:
    # Verifica quantas ocorrencias existem - a primeira eh create_cliente
    parts = content.split(insert_marker)
    if len(parts) >= 2:
        # Substitui soh na primeira ocorrencia
        new_content = parts[0] + 'razao_social, nome_fantasia, cnpj, cpf, produtor_rural, inscricao_estadual, inscricao_municipal,' + insert_marker.join(parts[1:])
        # Tambem ajustar VALUES
        values_marker = ':razao_social, :nome_fantasia, :cnpj, :inscricao_estadual, :inscricao_municipal,'
        if values_marker in new_content:
            vparts = new_content.split(values_marker)
            new_content = vparts[0] + ':razao_social, :nome_fantasia, :cnpj, :cpf, :produtor_rural, :inscricao_estadual, :inscricao_municipal,' + values_marker.join(vparts[1:])
        write_file('routes/admin_routes.py', new_content)
        print('  [OK]   create_cliente: INSERT com cpf e produtor_rural')
    else:
        print('  [SKIP] create_cliente INSERT - marcador nao encontrado')
else:
    print('  [SKIP] create_cliente INSERT - ja aplicado ou marcador nao encontrado')

# ─────────────────────────────────────────────────────────────
# 7. admin_routes.py - edit_cliente
# ─────────────────────────────────────────────────────────────
print('\n=== 7. admin_routes.py - edit_cliente ===')

# 7a. Adicionar limpeza CPF apos cnpj_limpo no edit_cliente
patch_re(
    'routes/admin_routes.py',
    r"(                cnpj_limpo = ''.join\(filter\(str\.isdigit, cnpj_raw\)\)\n\n)(                # Processar upload da logo \(se enviada\))",
    r"""\1                # Limpar CPF (remover formatacao)
                cpf_raw = request.form.get('cpf', '')
                cpf_limpo = ''.join(filter(str.isdigit, cpf_raw)) or None

\2""",
    'edit_cliente: limpeza CPF'
)

# 7b. Adicionar cpf/produtor_rural ao data dict do edit_cliente
patch_re(
    'routes/admin_routes.py',
    r"(                    'cnpj': cnpj_limpo,  # Limpo\n)(                    'inscricao_estadual': request\.form\.get\('inscricao_estadual'\),)",
    r"""\1                    'cpf': cpf_limpo,
                    'produtor_rural': request.form.get('produtor_rural') == 'on',
\2""",
    'edit_cliente: cpf e produtor_rural no data dict'
)

# 7c. Atualizar UPDATE SET para incluir cpf e produtor_rural
patch_re(
    'routes/admin_routes.py',
    r'(                    UPDATE clientes SET\n                        razao_social = :razao_social,\n                        nome_fantasia = :nome_fantasia,\n                        cnpj = :cnpj,\n)(                        inscricao_estadual)',
    r"""\1                        cpf = :cpf,
                        produtor_rural = :produtor_rural,
\2""",
    'edit_cliente: UPDATE SET com cpf e produtor_rural'
)

print('\n=== Patch concluido ===')
print('Execute agora:')
print('  sudo systemctl restart api-nfe-principal.service')
print('  sudo systemctl status api-nfe-principal.service')
