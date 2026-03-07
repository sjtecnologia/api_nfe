#!/usr/bin/env python3
"""
Patch cirurgico - Suporte a Produtor Rural (CPF sem CNPJ) no servidor.
Aplica mudancas em: models.py, nfe_routes.py, nfe_service.py, admin_routes.py
"""
import os, re

BASE = '/home/ubuntu/api_nfe'

def read(path):
    with open(os.path.join(BASE, path), 'r', encoding='utf-8') as f:
        return f.read()

def write(path, content):
    with open(os.path.join(BASE, path), 'w', encoding='utf-8') as f:
        f.write(content)

def patch_str(path, old, new, desc):
    c = read(path)
    if old not in c:
        print(f'  [SKIP] {desc}')
        return False
    write(path, c.replace(old, new, 1))
    print(f'  [OK]   {desc}')
    return True

def patch_re(path, pattern, replacement, desc, flags=re.DOTALL):
    c = read(path)
    new_c, n = re.subn(pattern, replacement, c, count=1, flags=flags)
    if n == 0:
        print(f'  [SKIP] {desc}')
        return False
    write(path, new_c)
    print(f'  [OK]   {desc}')
    return True

# ─────────────────────────────────────────────────────────────
# 1. database/models.py
# ─────────────────────────────────────────────────────────────
print('\n=== 1. database/models.py ===')

patch_str(
    'database/models.py',
    '    cnpj = Column(String(18), unique=True, nullable=False)',
    '    cnpj = Column(String(18), unique=True, nullable=True)',
    'cnpj nullable=True'
)

c = read('database/models.py')
if 'produtor_rural = Column(Boolean' not in c:
    c = c.replace(
        '    cnpj = Column(String(18), unique=True, nullable=True)\n    razao_social',
        '    cnpj = Column(String(18), unique=True, nullable=True)\n    cpf = Column(String(14), unique=True, nullable=True)\n    produtor_rural = Column(Boolean, default=False, nullable=False)\n    razao_social'
    )
    write('database/models.py', c)
    print('  [OK]   adicionar cpf e produtor_rural ao modelo Cliente')
else:
    print('  [SKIP] cpf/produtor_rural ja existem no modelo')

# ─────────────────────────────────────────────────────────────
# 2. routes/nfe_routes.py - validacao CNPJ emitente
# ─────────────────────────────────────────────────────────────
print('\n=== 2. routes/nfe_routes.py - validacao CNPJ ===')

patch_re(
    'routes/nfe_routes.py',
    r'        # VALIDAR CNPJ DO EMITENTE\n        cnpj_emitente_limpo = emitente_data\.cnpj\.replace.*?print\(f"[^"]*CNPJ emitente v[^"]*lido"\)',
    '''        # VALIDAR CNPJ DO EMITENTE
        if getattr(emitente_data, 'produtor_rural', False):
            print("[VALIDACAO] Emitente e Produtor Rural (CPF), pulando validacao CNPJ")
        else:
            cnpj_emitente_limpo = (emitente_data.cnpj or '').replace('.', '').replace('/', '').replace('-', '').strip()
            if not validar_cnpj(cnpj_emitente_limpo):
                flash(f'CNPJ do emitente \u00e9 inv\u00e1lido: {emitente_data.cnpj}. Corrija o cadastro do cliente antes de emitir NFe.', 'danger')
                return redirect(url_for('home.home'))
            print("[VALIDACAO] CNPJ emitente valido")''',
    'bypass validacao CNPJ para produtor rural'
)

# ─────────────────────────────────────────────────────────────
# 3. routes/nfe_routes.py - emitente_data_for_template
# ─────────────────────────────────────────────────────────────
print('\n=== 3. routes/nfe_routes.py - emitente_data_for_template ===')

patch_str(
    'routes/nfe_routes.py',
    "            'cnpj': emitente_data.cnpj,\n            'nome_fantasia': emitente_data.nome_fantasia,",
    "            'cnpj': emitente_data.cnpj,\n            'cpf': getattr(emitente_data, 'cpf', None),\n            'produtor_rural': getattr(emitente_data, 'produtor_rural', False),\n            'nome_fantasia': emitente_data.nome_fantasia,",
    'adicionar cpf e produtor_rural ao emitente_data_for_template'
)

# ─────────────────────────────────────────────────────────────
# 4. services/nfe_service.py - cnpj_emit para chave de acesso
# ─────────────────────────────────────────────────────────────
print('\n=== 4. services/nfe_service.py - cnpj_emit para chave de acesso ===')

patch_str(
    'services/nfe_service.py',
    "        cnpj_emit = emitente_data.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')",
    "        if emitente_data.get('produtor_rural'):\n            cpf_raw = (emitente_data.get('cpf') or '').replace('.', '').replace('-', '')\n            cnpj_emit = cpf_raw.zfill(14)  # CPF padded a 14 digitos para chave de acesso\n        else:\n            cnpj_emit = emitente_data.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')",
    'cnpj_emit: CPF padded para produtor rural'
)

# ─────────────────────────────────────────────────────────────
# 5. services/nfe_service.py - XML emit CNPJ -> CPF condicional
# ─────────────────────────────────────────────────────────────
print('\n=== 5. services/nfe_service.py - XML emit CNPJ/CPF ===')

patch_str(
    'services/nfe_service.py',
    '        etree.SubElement(emit, "CNPJ").text = cnpj_emit\n        etree.SubElement(emit, "xNome")',
    '        if emitente_data.get(\'produtor_rural\'):\n            cpf_emit = (emitente_data.get(\'cpf\') or \'\').replace(\'.\', \'\').replace(\'-\', \'\')\n            etree.SubElement(emit, "CPF").text = cpf_emit\n        else:\n            etree.SubElement(emit, "CNPJ").text = cnpj_emit\n        etree.SubElement(emit, "xNome")',
    'XML emit: CPF para produtor rural, CNPJ para empresa'
)

# ─────────────────────────────────────────────────────────────
# 6. admin_routes.py - create_cliente: limpeza CPF
# ─────────────────────────────────────────────────────────────
print('\n=== 6. admin_routes.py - create_cliente ===')

patch_str(
    'routes/admin_routes.py',
    "            cnpj_limpo = ''.join(filter(str.isdigit, cnpj_raw))\n            \n            # Processar upload da logo (se enviada)\n            logo_path = None",
    "            cnpj_limpo = ''.join(filter(str.isdigit, cnpj_raw))\n\n            # Limpar CPF (remover formatacao)\n            cpf_raw = request.form.get('cpf', '')\n            cpf_limpo = ''.join(filter(str.isdigit, cpf_raw)) or None\n\n            # Processar upload da logo (se enviada)\n            logo_path = None",
    'create_cliente: limpeza CPF'
)

# 6b. data dict - adicionar cpf/produtor_rural
patch_str(
    'routes/admin_routes.py',
    "                'cnpj': cnpj_limpo,  # Limpo\n                'inscricao_estadual': request.form.get('inscricao_estadual'),",
    "                'cnpj': cnpj_limpo or None,  # Limpo\n                'cpf': cpf_limpo,\n                'produtor_rural': request.form.get('produtor_rural') == 'on',\n                'inscricao_estadual': request.form.get('inscricao_estadual'),",
    'create_cliente: cpf e produtor_rural no data dict'
)

# 6c. INSERT - adicionar cpf e produtor_rural
patch_str(
    'routes/admin_routes.py',
    "                        razao_social, nome_fantasia, cnpj, inscricao_estadual, inscricao_municipal,\n                        regime_tributario_id, ambiente, cnae, cep, logradouro, numero, complemento, bairro,\n                        nome_municipio, codigo_municipio, uf, email_contato, telefone_contato, logo_path, ativo, data_cadastro, created_by_user_id\n                    ) VALUES (\n                        :razao_social, :nome_fantasia, :cnpj, :inscricao_estadual, :inscricao_municipal,\n                        :regime_tributario_id, :ambiente, :cnae, :cep, :logradouro, :numero, :complemento, :bairro,\n                        :nome_municipio, :codigo_municipio, :uf, :email_contato, :telefone_contato, :logo_path, :ativo, :data_cadastro, :created_by_user_id\n                    ) RETURNING cliente_id",
    "                        razao_social, nome_fantasia, cnpj, cpf, produtor_rural, inscricao_estadual, inscricao_municipal,\n                        regime_tributario_id, ambiente, cnae, cep, logradouro, numero, complemento, bairro,\n                        nome_municipio, codigo_municipio, uf, email_contato, telefone_contato, logo_path, ativo, data_cadastro, created_by_user_id\n                    ) VALUES (\n                        :razao_social, :nome_fantasia, :cnpj, :cpf, :produtor_rural, :inscricao_estadual, :inscricao_municipal,\n                        :regime_tributario_id, :ambiente, :cnae, :cep, :logradouro, :numero, :complemento, :bairro,\n                        :nome_municipio, :codigo_municipio, :uf, :email_contato, :telefone_contato, :logo_path, :ativo, :data_cadastro, :created_by_user_id\n                    ) RETURNING cliente_id",
    'create_cliente: INSERT com cpf e produtor_rural'
)

# ─────────────────────────────────────────────────────────────
# 7. admin_routes.py - edit_cliente: limpeza CPF
# ─────────────────────────────────────────────────────────────
print('\n=== 7. admin_routes.py - edit_cliente ===')

patch_str(
    'routes/admin_routes.py',
    "                cnpj_limpo = ''.join(filter(str.isdigit, cnpj_raw))\n                \n                # Processar upload da logo (se enviada)\n                logo_path = cliente.get('logo_path')  # Manter logo existente",
    "                cnpj_limpo = ''.join(filter(str.isdigit, cnpj_raw))\n\n                # Limpar CPF (remover formatacao)\n                cpf_raw = request.form.get('cpf', '')\n                cpf_limpo = ''.join(filter(str.isdigit, cpf_raw)) or None\n\n                # Processar upload da logo (se enviada)\n                logo_path = cliente.get('logo_path')  # Manter logo existente",
    'edit_cliente: limpeza CPF'
)

# 7b. data dict - adicionar cpf/produtor_rural
patch_str(
    'routes/admin_routes.py',
    "                    'cnpj': cnpj_limpo,  # Limpo\n                    'inscricao_estadual': request.form.get('inscricao_estadual'),",
    "                    'cnpj': cnpj_limpo or None,  # Limpo\n                    'cpf': cpf_limpo,\n                    'produtor_rural': request.form.get('produtor_rural') == 'on',\n                    'inscricao_estadual': request.form.get('inscricao_estadual'),",
    'edit_cliente: cpf e produtor_rural no data dict'
)

# 7c. UPDATE SET - adicionar cpf e produtor_rural
patch_str(
    'routes/admin_routes.py',
    "                    UPDATE clientes SET\n                        razao_social = :razao_social,\n                        nome_fantasia = :nome_fantasia,\n                        cnpj = :cnpj,\n                        inscricao_estadual = :inscricao_estadual,",
    "                    UPDATE clientes SET\n                        razao_social = :razao_social,\n                        nome_fantasia = :nome_fantasia,\n                        cnpj = :cnpj,\n                        cpf = :cpf,\n                        produtor_rural = :produtor_rural,\n                        inscricao_estadual = :inscricao_estadual,",
    'edit_cliente: UPDATE SET com cpf e produtor_rural'
)

print('\n=== Patch concluido! ===')
print('Execute agora para reiniciar o servico:')
print('  sudo systemctl restart api-nfe-principal.service')
print('  sudo systemctl status api-nfe-principal.service')
