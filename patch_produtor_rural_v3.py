#!/usr/bin/env python3
"""
Patch cirurgico v3 - Suporte a Produtor Rural (CPF sem CNPJ) no servidor.
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
        '    cnpj = Column(String(18), unique=True, nullable=True)\n'
        '    cpf = Column(String(14), unique=True, nullable=True)\n'
        '    produtor_rural = Column(Boolean, default=False, nullable=False)\n'
        '    razao_social'
    )
    write('database/models.py', c)
    print('  [OK]   adicionar cpf e produtor_rural ao modelo Cliente')
else:
    print('  [SKIP] cpf/produtor_rural ja existem no modelo')

# ─────────────────────────────────────────────────────────────
# 2. routes/nfe_routes.py - validacao CNPJ emitente
# ─────────────────────────────────────────────────────────────
print('\n=== 2. routes/nfe_routes.py - validacao CNPJ ===')

# Usa regex porque a linha tem emojis UTF-8 que podem complicar match exato
patch_re(
    'routes/nfe_routes.py',
    r'        # VALIDAR CNPJ DO EMITENTE\n'
    r'        cnpj_emitente_limpo = emitente_data\.cnpj\.replace.*?'
    r'print\(f"[^"]*CNPJ emitente v[^"]*lido"\)',
    "        # VALIDAR CNPJ DO EMITENTE\n"
    "        if getattr(emitente_data, 'produtor_rural', False):\n"
    "            print('[VALIDACAO] Emitente e Produtor Rural (CPF) - pulando validacao CNPJ')\n"
    "        else:\n"
    "            cnpj_emitente_limpo = (emitente_data.cnpj or '').replace('.', '').replace('/', '').replace('-', '').strip()\n"
    "            if not validar_cnpj(cnpj_emitente_limpo):\n"
    "                flash(f'CNPJ do emitente \u00e9 inv\u00e1lido: {emitente_data.cnpj}. Corrija o cadastro antes de emitir NFe.', 'danger')\n"
    "                return redirect(url_for('home.home'))\n"
    "            print('[VALIDACAO] CNPJ emitente valido')",
    'bypass validacao CNPJ para produtor rural'
)

# ─────────────────────────────────────────────────────────────
# 3. routes/nfe_routes.py - emitente_data_for_template
# ─────────────────────────────────────────────────────────────
print('\n=== 3. routes/nfe_routes.py - emitente_data_for_template ===')

patch_str(
    'routes/nfe_routes.py',
    "            'cnpj': emitente_data.cnpj,\n"
    "            'nome_fantasia': emitente_data.nome_fantasia,",
    "            'cnpj': emitente_data.cnpj,\n"
    "            'cpf': getattr(emitente_data, 'cpf', None),\n"
    "            'produtor_rural': getattr(emitente_data, 'produtor_rural', False),\n"
    "            'nome_fantasia': emitente_data.nome_fantasia,",
    'adicionar cpf e produtor_rural ao emitente_data_for_template'
)

# ─────────────────────────────────────────────────────────────
# 4. services/nfe_service.py - cnpj_emit para chave de acesso
# ─────────────────────────────────────────────────────────────
print('\n=== 4. services/nfe_service.py - cnpj_emit chave de acesso ===')

patch_str(
    'services/nfe_service.py',
    "        cnpj_emit = emitente_data.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')",
    "        if emitente_data.get('produtor_rural'):\n"
    "            cpf_raw = (emitente_data.get('cpf') or '').replace('.', '').replace('-', '')\n"
    "            cnpj_emit = cpf_raw.zfill(14)  # CPF padded a 14 digitos para chave de acesso\n"
    "        else:\n"
    "            cnpj_emit = emitente_data.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '')",
    'cnpj_emit: CPF padded para produtor rural'
)

# ─────────────────────────────────────────────────────────────
# 5. services/nfe_service.py - XML emit CNPJ -> CPF condicional
# ─────────────────────────────────────────────────────────────
print('\n=== 5. services/nfe_service.py - XML emit CNPJ/CPF ===')

patch_str(
    'services/nfe_service.py',
    '        etree.SubElement(emit, "CNPJ").text = cnpj_emit\n'
    '        etree.SubElement(emit, "xNome")',
    '        if emitente_data.get(\'produtor_rural\'):\n'
    '            cpf_emit = (emitente_data.get(\'cpf\') or \'\').replace(\'.\', \'\').replace(\'-\', \'\')\n'
    '            etree.SubElement(emit, "CPF").text = cpf_emit\n'
    '        else:\n'
    '            etree.SubElement(emit, "CNPJ").text = cnpj_emit\n'
    '        etree.SubElement(emit, "xNome")',
    'XML emit: CPF para produtor rural, CNPJ para empresa'
)

# ─────────────────────────────────────────────────────────────
# 6. admin_routes.py - create_cliente
# ─────────────────────────────────────────────────────────────
print('\n=== 6. admin_routes.py - create_cliente ===')

# 6a. Limpeza CPF - usa regex para nao depender de espacos na linha em branco
patch_re(
    'routes/admin_routes.py',
    r"(            cnpj_limpo = ''.join\(filter\(str\.isdigit, cnpj_raw\)\))\n\s*\n"
    r"(            # Processar upload da logo \(se enviada\)\n"
    r"            logo_path = None)",
    "\\1\n\n"
    "            # Limpar CPF (remover formatacao)\n"
    "            cpf_raw = request.form.get('cpf', '')\n"
    "            cpf_limpo = ''.join(filter(str.isdigit, cpf_raw)) or None\n\n"
    "\\2",
    'create_cliente: limpeza CPF'
)

# 6b. data dict
patch_str(
    'routes/admin_routes.py',
    "                'cnpj': cnpj_limpo,  # Limpo\n"
    "                'inscricao_estadual': request.form.get('inscricao_estadual'),",
    "                'cnpj': cnpj_limpo or None,  # Limpo\n"
    "                'cpf': cpf_limpo,\n"
    "                'produtor_rural': request.form.get('produtor_rural') == 'on',\n"
    "                'inscricao_estadual': request.form.get('inscricao_estadual'),",
    'create_cliente: cpf e produtor_rural no data dict'
)

# 6c. INSERT colunas
patch_str(
    'routes/admin_routes.py',
    "                        razao_social, nome_fantasia, cnpj, inscricao_estadual, inscricao_municipal,\n"
    "                        regime_tributario_id, ambiente, cnae, cep, logradouro, numero, complemento, bairro,\n"
    "                        nome_municipio, codigo_municipio, uf, email_contato, telefone_contato, logo_path, ativo, data_cadastro, created_by_user_id\n"
    "                    ) VALUES (\n"
    "                        :razao_social, :nome_fantasia, :cnpj, :inscricao_estadual, :inscricao_municipal,\n"
    "                        :regime_tributario_id, :ambiente, :cnae, :cep, :logradouro, :numero, :complemento, :bairro,\n"
    "                        :nome_municipio, :codigo_municipio, :uf, :email_contato, :telefone_contato, :logo_path, :ativo, :data_cadastro, :created_by_user_id\n"
    "                    ) RETURNING cliente_id",
    "                        razao_social, nome_fantasia, cnpj, cpf, produtor_rural, inscricao_estadual, inscricao_municipal,\n"
    "                        regime_tributario_id, ambiente, cnae, cep, logradouro, numero, complemento, bairro,\n"
    "                        nome_municipio, codigo_municipio, uf, email_contato, telefone_contato, logo_path, ativo, data_cadastro, created_by_user_id\n"
    "                    ) VALUES (\n"
    "                        :razao_social, :nome_fantasia, :cnpj, :cpf, :produtor_rural, :inscricao_estadual, :inscricao_municipal,\n"
    "                        :regime_tributario_id, :ambiente, :cnae, :cep, :logradouro, :numero, :complemento, :bairro,\n"
    "                        :nome_municipio, :codigo_municipio, :uf, :email_contato, :telefone_contato, :logo_path, :ativo, :data_cadastro, :created_by_user_id\n"
    "                    ) RETURNING cliente_id",
    'create_cliente: INSERT com cpf e produtor_rural'
)

# ─────────────────────────────────────────────────────────────
# 7. admin_routes.py - edit_cliente
# ─────────────────────────────────────────────────────────────
print('\n=== 7. admin_routes.py - edit_cliente ===')

# 7a. Limpeza CPF
patch_re(
    'routes/admin_routes.py',
    r"(                cnpj_limpo = ''.join\(filter\(str\.isdigit, cnpj_raw\)\))\n\s*\n"
    r"(                # Processar upload da logo \(se enviada\)\n"
    r"                logo_path = cliente\.get\('logo_path'\)  # Manter logo existente)",
    "\\1\n\n"
    "                # Limpar CPF (remover formatacao)\n"
    "                cpf_raw = request.form.get('cpf', '')\n"
    "                cpf_limpo = ''.join(filter(str.isdigit, cpf_raw)) or None\n\n"
    "\\2",
    'edit_cliente: limpeza CPF'
)

# 7b. data dict
patch_str(
    'routes/admin_routes.py',
    "                    'cnpj': cnpj_limpo,  # Limpo\n"
    "                    'inscricao_estadual': request.form.get('inscricao_estadual'),",
    "                    'cnpj': cnpj_limpo or None,  # Limpo\n"
    "                    'cpf': cpf_limpo,\n"
    "                    'produtor_rural': request.form.get('produtor_rural') == 'on',\n"
    "                    'inscricao_estadual': request.form.get('inscricao_estadual'),",
    'edit_cliente: cpf e produtor_rural no data dict'
)

# 7c. UPDATE SET
patch_str(
    'routes/admin_routes.py',
    "                    UPDATE clientes SET\n"
    "                        razao_social = :razao_social,\n"
    "                        nome_fantasia = :nome_fantasia,\n"
    "                        cnpj = :cnpj,\n"
    "                        inscricao_estadual = :inscricao_estadual,",
    "                    UPDATE clientes SET\n"
    "                        razao_social = :razao_social,\n"
    "                        nome_fantasia = :nome_fantasia,\n"
    "                        cnpj = :cnpj,\n"
    "                        cpf = :cpf,\n"
    "                        produtor_rural = :produtor_rural,\n"
    "                        inscricao_estadual = :inscricao_estadual,",
    'edit_cliente: UPDATE SET com cpf e produtor_rural'
)

# ─────────────────────────────────────────────────────────────
# 8. templates/admin/clientes/form.html - campo produtor_rural e CPF
# ─────────────────────────────────────────────────────────────
print('\n=== 8. templates/admin/clientes/form.html ===')

CNPJ_INPUT_OLD = (
    '                            <div class="col-md-4 mb-3">\n'
    '                                <label for="cnpj" class="form-label">CNPJ</label>\n'
    '                                <input type="text" class="form-control" id="cnpj" name="cnpj" '
    'value="{{ form_data.cnpj | default(\'\') }}" placeholder="00.000.000/0000-00" required>\n'
    '                            </div>'
)

CNPJ_INPUT_NEW = (
    '                            <!-- Produtor Rural toggle -->\n'
    '                            <div class="col-md-12 mb-2">\n'
    '                                <div class="form-check form-switch">\n'
    '                                    <input class="form-check-input" type="checkbox" id="produtor_rural" name="produtor_rural"\n'
    '                                           {% if form_data.produtor_rural %}checked{% endif %}\n'
    '                                           onchange="toggleProdutorRural()">\n'
    '                                    <label class="form-check-label fw-semibold" for="produtor_rural">\n'
    '                                        \U0001f33e Emitente \u00e9 Produtor Rural (CPF sem CNPJ)\n'
    '                                    </label>\n'
    '                                </div>\n'
    '                            </div>\n'
    '                            <!-- CNPJ (empresa) -->\n'
    '                            <div class="col-md-4 mb-3" id="div_cnpj">\n'
    '                                <label for="cnpj" class="form-label">CNPJ</label>\n'
    '                                <input type="text" class="form-control" id="cnpj" name="cnpj" '
    'value="{{ form_data.cnpj | default(\'\') }}" placeholder="00.000.000/0000-00">\n'
    '                            </div>\n'
    '                            <!-- CPF (produtor rural) -->\n'
    '                            <div class="col-md-4 mb-3" id="div_cpf" style="display:none;">\n'
    '                                <label for="cpf" class="form-label">CPF (Produtor Rural)</label>\n'
    '                                <input type="text" class="form-control" id="cpf" name="cpf" '
    'value="{{ form_data.cpf | default(\'\') }}" placeholder="000.000.000-00">\n'
    '                            </div>'
)

r = patch_str(
    'templates/admin/clientes/form.html',
    CNPJ_INPUT_OLD,
    CNPJ_INPUT_NEW,
    'form.html: campo produtor_rural e CPF'
)

# 8b. Adicionar JS para toggle (antes de // Mascara CNPJ)
JS_OLD = '    // Máscara CNPJ'
JS_NEW = (
    '    // === Toggle Produtor Rural ===\n'
    '    function toggleProdutorRural() {\n'
    '        var isRural = document.getElementById(\'produtor_rural\').checked;\n'
    '        document.getElementById(\'div_cnpj\').style.display = isRural ? \'none\' : \'\';\n'
    '        document.getElementById(\'div_cpf\').style.display = isRural ? \'\' : \'none\';\n'
    '        document.getElementById(\'cnpj\').required = !isRural;\n'
    '        var cpfEl = document.getElementById(\'cpf\');\n'
    '        if (cpfEl) cpfEl.required = isRural;\n'
    '    }\n'
    '    // Restaurar estado inicial\n'
    '    document.addEventListener(\'DOMContentLoaded\', function() {\n'
    '        if (document.getElementById(\'produtor_rural\') &&\n'
    '            document.getElementById(\'produtor_rural\').checked) {\n'
    '            toggleProdutorRural();\n'
    '        }\n'
    '    });\n'
    '\n'
    '    // Máscara CNPJ'
)

patch_str(
    'templates/admin/clientes/form.html',
    JS_OLD,
    JS_NEW,
    'form.html: JS toggle produtor_rural'
)

print('\n=== Patch concluido! ===')
print('PROXIMOS PASSOS:')
print('  sudo systemctl restart api-nfe-principal.service')
print('  sudo systemctl status api-nfe-principal.service')
