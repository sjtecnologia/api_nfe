#!/usr/bin/env python3
"""
Fix constraint violation - garante mutuamente exclusivo cnpj/cpf por tipo de emitente.
"""
import os

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

# ─────────────────────────────────────────────────────────────────────────────
# create_cliente: substituir as 3 linhas cnpj/cpf/produtor_rural no data dict
# ─────────────────────────────────────────────────────────────────────────────
OLD_CREATE = (
    "                'cnpj': cnpj_limpo or None,  # Limpo\n"
    "                'cpf': cpf_limpo,\n"
    "                'produtor_rural': request.form.get('produtor_rural') == 'on',"
)

NEW_CREATE = (
    "                # Mutuamente exclusivo: produtor rural usa CPF; empresa usa CNPJ\n"
    "                '_is_rural': request.form.get('produtor_rural') == 'on',\n"
    "                'produtor_rural': request.form.get('produtor_rural') == 'on',\n"
    "                'cnpj': None if (request.form.get('produtor_rural') == 'on') else (cnpj_limpo or None),\n"
    "                'cpf': (cpf_limpo or (cnpj_limpo if cnpj_limpo and len(cnpj_limpo) == 11 else None))\n"
    "                       if (request.form.get('produtor_rural') == 'on') else None,"
)

# Abordagem mais limpa com variavel intermediaria inserida ANTES do data dict
# Vamos inserir a logica de separacao antes do 'data = {'

OLD_CREATE_BLOCK = (
    "            # Dados do cliente\n"
    "            data = {\n"
    "                'razao_social': request.form.get('razao_social'),\n"
    "                'nome_fantasia': request.form.get('nome_fantasia'),\n"
    "                'cnpj': cnpj_limpo or None,  # Limpo\n"
    "                'cpf': cpf_limpo,\n"
    "                'produtor_rural': request.form.get('produtor_rural') == 'on',"
)

NEW_CREATE_BLOCK = (
    "            # Dados do cliente\n"
    "            _is_rural = request.form.get('produtor_rural') == 'on'\n"
    "            # Mutualmente exclusivo: produtor rural usa CPF (sem CNPJ); empresa usa CNPJ (sem CPF)\n"
    "            _cnpj_save = None if _is_rural else (cnpj_limpo or None)\n"
    "            # Se rural e CPF nao preenchido, tenta usar cnpj_limpo se tiver 11 digitos\n"
    "            _cpf_save = (cpf_limpo or (cnpj_limpo if cnpj_limpo and len(cnpj_limpo) == 11 else None)) if _is_rural else None\n"
    "            data = {\n"
    "                'razao_social': request.form.get('razao_social'),\n"
    "                'nome_fantasia': request.form.get('nome_fantasia'),\n"
    "                'cnpj': _cnpj_save,\n"
    "                'cpf': _cpf_save,\n"
    "                'produtor_rural': _is_rural,"
)

print('\n=== admin_routes.py - create_cliente ===')
patch_str('routes/admin_routes.py', OLD_CREATE_BLOCK, NEW_CREATE_BLOCK, 'create_cliente: logica cnpj/cpf mutuamente exclusiva')

# ─────────────────────────────────────────────────────────────────────────────
# edit_cliente: mesma logica
# ─────────────────────────────────────────────────────────────────────────────
OLD_EDIT_BLOCK = (
    "                data = {\n"
    "                    'razao_social': request.form.get('razao_social'),\n"
    "                    'nome_fantasia': request.form.get('nome_fantasia'),\n"
    "                    'cnpj': cnpj_limpo or None,  # Limpo\n"
    "                    'cpf': cpf_limpo,\n"
    "                    'produtor_rural': request.form.get('produtor_rural') == 'on',"
)

NEW_EDIT_BLOCK = (
    "                _is_rural = request.form.get('produtor_rural') == 'on'\n"
    "                # Mutualmente exclusivo: produtor rural usa CPF (sem CNPJ); empresa usa CNPJ (sem CPF)\n"
    "                _cnpj_save = None if _is_rural else (cnpj_limpo or None)\n"
    "                # Se rural e CPF nao preenchido, tenta usar cnpj_limpo se tiver 11 digitos\n"
    "                _cpf_save = (cpf_limpo or (cnpj_limpo if cnpj_limpo and len(cnpj_limpo) == 11 else None)) if _is_rural else None\n"
    "                data = {\n"
    "                    'razao_social': request.form.get('razao_social'),\n"
    "                    'nome_fantasia': request.form.get('nome_fantasia'),\n"
    "                    'cnpj': _cnpj_save,\n"
    "                    'cpf': _cpf_save,\n"
    "                    'produtor_rural': _is_rural,"
)

print('\n=== admin_routes.py - edit_cliente ===')
patch_str('routes/admin_routes.py', OLD_EDIT_BLOCK, NEW_EDIT_BLOCK, 'edit_cliente: logica cnpj/cpf mutuamente exclusiva')

# ─────────────────────────────────────────────────────────────────────────────
# templates/form.html: desabilitar input oculto ao submeter
# ─────────────────────────────────────────────────────────────────────────────
print('\n=== templates/admin/clientes/form.html ===')

# Atualizar o JS da funcao toggleProdutorRural para DESABILITAR (disable) o input oculto
OLD_JS = (
    "    function toggleProdutorRural() {\n"
    "        var isRural = document.getElementById('produtor_rural').checked;\n"
    "        document.getElementById('div_cnpj').style.display = isRural ? 'none' : '';\n"
    "        document.getElementById('div_cpf').style.display = isRural ? '' : 'none';\n"
    "        document.getElementById('cnpj').required = !isRural;\n"
    "        var cpfEl = document.getElementById('cpf');\n"
    "        if (cpfEl) cpfEl.required = isRural;\n"
    "    }"
)

NEW_JS = (
    "    function toggleProdutorRural() {\n"
    "        var isRural = document.getElementById('produtor_rural').checked;\n"
    "        var cnpjEl = document.getElementById('cnpj');\n"
    "        var cpfEl = document.getElementById('cpf');\n"
    "        document.getElementById('div_cnpj').style.display = isRural ? 'none' : '';\n"
    "        document.getElementById('div_cpf').style.display = isRural ? '' : 'none';\n"
    "        // Desabilitar campo oculto para nao enviar valor conflitante\n"
    "        cnpjEl.disabled = isRural;\n"
    "        if (cpfEl) cpfEl.disabled = !isRural;\n"
    "        cnpjEl.required = !isRural;\n"
    "        if (cpfEl) cpfEl.required = isRural;\n"
    "    }"
)

patch_str('templates/admin/clientes/form.html', OLD_JS, NEW_JS, 'form.html: disable input oculto ao toggle')

print('\n=== Fix concluido! ===')
print('Execute:')
print('  sudo systemctl restart api-nfe-principal.service')
