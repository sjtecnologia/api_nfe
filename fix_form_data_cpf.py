#!/usr/bin/env python3
"""
Fix: _cliente_to_form_data sem cpf/produtor_rural + JS toggle melhorado no form.html
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

# ────────────────────────────────────────────────────────────────
# 1. admin_routes.py - _cliente_to_form_data: adicionar cpf e produtor_rural
# ────────────────────────────────────────────────────────────────
print('\n=== admin_routes.py - _cliente_to_form_data ===')

patch_str(
    'routes/admin_routes.py',
    "        'cnpj': cliente_row.get('cnpj', ''),\n"
    "        'inscricao_estadual': cliente_row.get('inscricao_estadual', ''),",
    "        'cnpj': cliente_row.get('cnpj', '') or '',\n"
    "        'cpf': cliente_row.get('cpf', '') or '',\n"
    "        'produtor_rural': bool(cliente_row.get('produtor_rural', False)),\n"
    "        'inscricao_estadual': cliente_row.get('inscricao_estadual', ''),",
    '_cliente_to_form_data: adicionar cpf e produtor_rural'
)

# ────────────────────────────────────────────────────────────────
# 2. form.html - substituir o bloco DOMContentLoaded com toggle melhorado
#    Problema: toggleProdutorRural estava dentro de DOMContentLoaded
#    mas chamava addEventListener(DOMContentLoaded) de novo (nao funciona)
#    Alem disso, adicionar mascara CPF e label dinamico
# ────────────────────────────────────────────────────────────────
print('\n=== templates/admin/clientes/form.html - JS toggle ===')

OLD_JS = (
    "document.addEventListener('DOMContentLoaded', function() {\n"
    "    // === Toggle Produtor Rural ===\n"
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
    "    }\n"
    "    // Restaurar estado inicial\n"
    "    document.addEventListener('DOMContentLoaded', function() {\n"
    "        if (document.getElementById('produtor_rural') &&\n"
    "            document.getElementById('produtor_rural').checked) {\n"
    "            toggleProdutorRural();\n"
    "        }\n"
    "    });\n"
    "\n"
    "    // Máscara CNPJ\n"
    "    var cnpjInput = document.getElementById('cnpj');\n"
    "    if (cnpjInput && window.IMask) {\n"
    "        IMask(cnpjInput, { mask: '00.000.000/0000-00' });\n"
    "    }"
)

NEW_JS = (
    "document.addEventListener('DOMContentLoaded', function() {\n"
    "    // === Toggle Produtor Rural ===\n"
    "    var _cnpjMask = null, _cpfMask = null;\n"
    "\n"
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
    "    }\n"
    "\n"
    "    // Expor globalmente para o atributo onchange\n"
    "    window.toggleProdutorRural = toggleProdutorRural;\n"
    "\n"
    "    // Aplicar mascaras\n"
    "    var cnpjInput = document.getElementById('cnpj');\n"
    "    if (cnpjInput && window.IMask) {\n"
    "        _cnpjMask = IMask(cnpjInput, { mask: '00.000.000/0000-00' });\n"
    "    }\n"
    "    var cpfInput = document.getElementById('cpf');\n"
    "    if (cpfInput && window.IMask) {\n"
    "        _cpfMask = IMask(cpfInput, { mask: '000.000.000-00' });\n"
    "    }\n"
    "\n"
    "    // Restaurar estado inicial ao carregar pagina (modo edicao)\n"
    "    if (document.getElementById('produtor_rural') &&\n"
    "        document.getElementById('produtor_rural').checked) {\n"
    "        toggleProdutorRural();\n"
    "    }"
)

patch_str(
    'templates/admin/clientes/form.html',
    OLD_JS,
    NEW_JS,
    'form.html: JS toggle corrigido com mascara CPF e restore estado'
)

print('\n=== Fix concluido! ===')
print('Execute:')
print('  sudo systemctl restart api-nfe-principal.service')
