#!/usr/bin/env python3
"""
Script de teste para verificar se as correções do DANFE estão funcionando
"""

import sys
sys.path.insert(0, '/Users/renato/Documents/Developement/api_nfe')

print("=" * 80)
print("TESTE DE CORREÇÕES - DANFE E TRANSPORTADORA")
print("=" * 80)

# Teste 1: Imports
print("\n1️⃣ Testando imports...")
try:
    from services.danfe_service import generate_danfe
    print("   [OK] danfe_service.generate_danfe importado")
except Exception as e:
    print(f"   [X] Erro: {e}")
    sys.exit(1)

try:
    from routes.nfe_routes import nfe_bp
    print("   [OK] nfe_routes importado")
except Exception as e:
    print(f"   [X] Erro: {e}")
    sys.exit(1)

# Teste 2: Dependências
print("\n2️⃣ Testando dependências de DANFE...")
try:
    import brazilnum
    print("   [OK] brazilnum instalado")
except:
    print("   [X] brazilnum NÃO instalado")

try:
    import BrazilFiscalReport
    print("   [OK] BrazilFiscalReport instalado")
except:
    print("   [X] BrazilFiscalReport NÃO instalado")

try:
    import erpbrasil.edoc.pdf
    print("   [OK] erpbrasil.edoc.pdf instalado")
except:
    print("   [X] erpbrasil.edoc.pdf NÃO instalado")

try:
    from brazilfiscalreport.danfe import DanfeConfig
    print("   [OK] DanfeConfig disponível")
except Exception as e:
    print(f"   [X] DanfeConfig erro: {e}")

# Teste 3: Verificar assinatura de generate_danfe
print("\n3️⃣ Verificando assinatura de generate_danfe...")
import inspect
sig = inspect.signature(generate_danfe)
print(f"   Parâmetros: {sig}")
params = list(sig.parameters.keys())
if 'cliente_id' in params:
    print("   [OK] Parâmetro cliente_id presente")
else:
    print("   [X] Parâmetro cliente_id AUSENTE")

# Teste 4: Verificar se o diretório de logos existe
print("\n4️⃣ Verificando estrutura de diretórios...")
import os
logos_dir = os.path.join('static', 'logos')
if os.path.exists(logos_dir):
    print(f"   [OK] Diretório {logos_dir} existe")
    logos = [f for f in os.listdir(logos_dir) if f.endswith(('.png', '.jpg', '.jpeg', '.gif'))]
    if logos:
        print(f"   [?] {len(logos)} logo(s) encontrada(s): {', '.join(logos[:3])}")
    else:
        print("   [!] Nenhuma logo encontrada no diretório")
else:
    print(f"   [!] Diretório {logos_dir} NÃO existe")
    print(f"   [?] Criar com: mkdir -p {logos_dir}")

# Teste 5: Verificar banco de dados
print("\n5️⃣ Verificando banco de dados...")
try:
    from database.connection import get_db_connection
    from sqlalchemy import text
    db = get_db_connection()
    
    # Verificar se coluna logo_path existe
    result = db.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'clientes' 
        AND column_name = 'logo_path'
    """)).fetchone()
    
    if result:
        print("   [OK] Coluna logo_path existe na tabela clientes")
        
        # Verificar quantos clientes têm logo
        count = db.execute(text("SELECT COUNT(*) FROM clientes WHERE logo_path IS NOT NULL")).fetchone()
        print(f"   [DATA] {count[0]} cliente(s) com logo cadastrada")
        
        # Listar clientes com logo
        if count[0] > 0:
            clientes = db.execute(text("""
                SELECT cliente_id, razao_social, logo_path 
                FROM clientes 
                WHERE logo_path IS NOT NULL 
                LIMIT 3
            """)).fetchall()
            for c in clientes:
                print(f"      • Cliente #{c[0]} ({c[1]}): {c[2]}")
    else:
        print("   [X] Coluna logo_path NÃO existe")
        print("   [?] Execute: psql -f adicionar_campo_logo_cliente.sql")
    
    db.close()
except Exception as e:
    print(f"   [!] Erro ao verificar banco: {e}")

# Teste 6: Verificar código de nfe_routes
print("\n6️⃣ Verificando código de nfe_routes.py...")
try:
    with open('routes/nfe_routes.py', 'r') as f:
        content = f.read()
        
    # Verificar se usa emitente_cliente_id (correto)
    if 'generate_danfe(xml_assinado, nfe_id, emitente_cliente_id)' in content:
        print("   [OK] Usa emitente_cliente_id (correto)")
    elif 'generate_danfe(xml_assinado, nfe_id, cliente_id)' in content:
        print("   [X] Ainda usa cliente_id (ERRO)")
    else:
        print("   [!] Padrão não encontrado")
    
    # Verificar captura de campos de transportadora
    campos_transport = [
        'transportadoraANTT',
        'volumeMarca',
        'volumeNumeracao'
    ]
    for campo in campos_transport:
        if f"'{campo}'" in content:
            print(f"   [OK] Campo {campo} capturado")
        else:
            print(f"   [X] Campo {campo} NÃO capturado")
            
except Exception as e:
    print(f"   [!] Erro ao ler arquivo: {e}")

print("\n" + "=" * 80)
print("[OK] TESTE COMPLETO")
print("=" * 80)
print("\n[?] PRÓXIMOS PASSOS:")
print("   1. Se todos os testes passaram: Reinicie o servidor")
print("   2. Se há erros: Verifique os itens marcados com [X]")
print("   3. Teste emitindo uma NFe com DANFE automático")
print("=" * 80)
