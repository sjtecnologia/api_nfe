#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar por que o menu não aparece
Execute no servidor Windows: python diagnostico_menu.py
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("DIAGNÓSTICO - Menu Planos e Assinaturas")
print("=" * 60)
print()

# 1. Verificar se os módulos necessários existem
print("[1/6] Verificando arquivos necessários...")
files_to_check = [
    'models/user.py',
    'routes/planos_routes.py',
    'auth/decorators.py',
    'templates/base.html'
]

for file in files_to_check:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"  {status} {file}")

print()

# 2. Verificar conteúdo do models/user.py
print("[2/6] Verificando método is_super_admin() em models/user.py...")
try:
    with open('models/user.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if "def is_super_admin(self):" in content:
            print("  ✅ Método is_super_admin() encontrado")
            
            # Verificar se está usando .lower() (ERRADO)
            if ".lower() == 'super_admin'" in content:
                print("  ❌ ERRO: Usando .lower() - está comparando errado!")
                print("     Deve ser: role.get('name', '') == 'Super_Admin'")
            elif "== 'Super_Admin'" in content:
                print("  ✅ Comparação correta: == 'Super_Admin'")
            else:
                print("  ⚠️  AVISO: Método existe mas não encontrei a comparação esperada")
        else:
            print("  ❌ Método is_super_admin() NÃO encontrado!")
except Exception as e:
    print(f"  ❌ Erro ao ler arquivo: {e}")

print()

# 3. Verificar se o blueprint está registrado no app.py
print("[3/6] Verificando registro do blueprint no app.py...")
try:
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if "from routes.planos_routes import planos_bp" in content:
            print("  ✅ Import do planos_bp encontrado")
        else:
            print("  ❌ Import do planos_bp NÃO encontrado!")
            
        if "app.register_blueprint(planos_bp" in content:
            print("  ✅ Registro do planos_bp encontrado")
        else:
            print("  ❌ Registro do planos_bp NÃO encontrado!")
except Exception as e:
    print(f"  ❌ Erro ao ler arquivo: {e}")

print()

# 4. Verificar se o menu está no base.html
print("[4/6] Verificando menu em templates/base.html...")
try:
    with open('templates/base.html', 'r', encoding='utf-8') as f:
        content = f.read()
        if "current_user.is_super_admin()" in content:
            print("  ✅ Verificação is_super_admin() encontrada")
        else:
            print("  ❌ Verificação is_super_admin() NÃO encontrada!")
            
        if "Planos e Assinaturas" in content:
            print("  ✅ Link 'Planos e Assinaturas' encontrado")
        else:
            print("  ❌ Link 'Planos e Assinaturas' NÃO encontrado!")
            
        if "url_for('planos.list_planos')" in content:
            print("  ✅ URL correta: planos.list_planos")
        else:
            print("  ❌ URL incorreta ou não encontrada!")
except Exception as e:
    print(f"  ❌ Erro ao ler arquivo: {e}")

print()

# 5. Verificar cache Python
print("[5/6] Verificando cache Python...")
cache_found = False
for root, dirs, files in os.walk('.'):
    if '__pycache__' in dirs:
        cache_found = True
        print(f"  ⚠️  Cache encontrado em: {root}")
    for file in files:
        if file.endswith('.pyc'):
            cache_found = True
            print(f"  ⚠️  Arquivo .pyc: {os.path.join(root, file)}")

if not cache_found:
    print("  ✅ Nenhum cache Python encontrado")
else:
    print()
    print("  💡 DICA: Execute o script limpar_cache_windows.bat")

print()

# 6. Tentar importar e testar
print("[6/6] Testando importação dos módulos...")
try:
    from models.user import User
    print("  ✅ models.user importado com sucesso")
    
    # Testar método
    test_user = User(
        id=1,
        username='test',
        email='test@test.com',
        _is_active=True,
        roles=[{'name': 'Super_Admin'}]
    )
    
    result = test_user.is_super_admin()
    if result:
        print(f"  ✅ is_super_admin() retorna True para role 'Super_Admin'")
    else:
        print(f"  ❌ is_super_admin() retorna False - PROBLEMA NO MÉTODO!")
        
except Exception as e:
    print(f"  ❌ Erro ao importar/testar: {e}")

print()

# 7. Verificar banco de dados
print("[7/7] Verificando conexão com banco de dados...")
try:
    from database.connection import get_db
    from sqlalchemy import text
    
    db = get_db()
    
    # Verificar tabela roles
    result = db.execute(text("SELECT id, name FROM roles ORDER BY id")).fetchall()
    print("  ✅ Conexão com banco OK")
    print("  📋 Roles cadastradas:")
    for row in result:
        print(f"     - ID {row[0]}: {row[1]}")
    
    # Verificar se existe tabela planos_nfe
    result = db.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'planos_nfe'
        )
    """)).scalar()
    
    if result:
        print("  ✅ Tabela planos_nfe existe")
        
        # Contar planos
        count = db.execute(text("SELECT COUNT(*) FROM planos_nfe")).scalar()
        print(f"  📦 {count} planos cadastrados")
    else:
        print("  ❌ Tabela planos_nfe NÃO existe - execute a migration 006!")
        
except Exception as e:
    print(f"  ❌ Erro ao conectar no banco: {e}")

print()
print("=" * 60)
print("DIAGNÓSTICO CONCLUÍDO")
print("=" * 60)
print()

# Resumo
print("📝 RESUMO:")
print()
print("Se todos os itens acima estão ✅, então:")
print("1. Limpe o cache: scripts\\limpar_cache_windows.bat")
print("2. Reinicie o serviço: net stop api_nfe_principal && net start api_nfe_principal")
print("3. Faça logout e login novamente no sistema")
print("4. Limpe o cache do navegador (Ctrl+Shift+Delete)")
print()
print("Se ainda não funcionar, execute este script NO SERVIDOR e me envie o resultado!")
print()
