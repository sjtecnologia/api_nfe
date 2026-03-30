import subprocess, os

files = [
    'routes/nfe_routes.py',
    'routes/admin_routes.py',
    'routes/cliente_routes.py',
    'routes/home_routes.py',
    'routes/planos_routes.py',
    'services/email_service.py',
    'services/ibs_cbs_service.py',
    'services/nfe_service.py',
    'services/sefaz_service.py',
    'config/settings.py',
    'database/models.py',
    'utils/nfe_validators.py',
    'templates/admin/nfes/emitir.html',
    'templates/admin/produtos/list.html',
    'templates/admin/produtos/list_partial.html',
    'templates/admin/produtos/form.html',
    'templates/admin/destinatarios/list_partial.html',
    'templates/admin/certificados/list_partial.html',
    'templates/admin/classificacoes_ibs_cbs/list.html',
    'templates/admin/users/form.html',
    'templates/admin/users/list.html',
    'templates/base.html',
    'templates/cliente/dashboard.html',
    'templates/home.html',
    'templates/login.html',
    'templates/forgot_password.html',
    'templates/reset_password.html',
    'templates/admin/planos/assinatura_form.html',
    'templates/admin/planos/assinaturas_list.html',
    'templates/admin/regras_tributacao/form_partial.html',
]

for f in files:
    result = subprocess.run(['git', 'show', 'origin/lc214-migration:' + f], capture_output=True)
    if result.returncode == 0:
        dirpath = os.path.dirname(f)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)
        with open(f, 'wb') as fp:
            fp.write(result.stdout)
        print('OK: ' + f)
    else:
        print('ERRO: ' + f + ' - ' + result.stderr.decode('utf-8', errors='replace'))

print('CONCLUIDO')
