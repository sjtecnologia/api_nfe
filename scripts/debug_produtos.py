import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def debug_produtos():
    """Debug da listagem de produtos"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 DEBUG - LISTAGEM DE PRODUTOS")
        print("="*50)
        
        cliente_id = 5  # Cliente SJ TECNOLOGIA
        
        # 1. VERIFICAR PRODUTOS NA TABELA
        print(f"\n📋 PRODUTOS DO CLIENTE {cliente_id}:")
        produtos_result = db.execute(text("""
            SELECT produto_id, codigo_interno, descricao, 
                   unidade_comercial, preco_unitario_padrao,
                   ativo, ncm_id
            FROM produtos 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        produtos = [dict(row._mapping) for row in produtos_result]
        
        print(f"📊 TOTAL: {len(produtos)} produtos encontrados")
        
        for produto in produtos:
            print(f"  • ID: {produto['produto_id']}")
            print(f"    Código: {produto['codigo_interno']}")
            print(f"    Descrição: {produto['descricao']}")
            print(f"    Unidade: {produto['unidade_comercial']}")
            print(f"    Preço: {produto['preco_unitario_padrao']}")
            print(f"    Ativo: {produto['ativo']}")
            print(f"    NCM ID: {produto['ncm_id']}")
            print("-" * 40)
        
        # 2. TESTAR QUERY COM JOIN NCM (como no admin_routes)
        print(f"\n📋 QUERY COM JOIN NCM:")
        produtos_join_result = db.execute(text("""
            SELECT p.produto_id, p.codigo_interno, p.descricao, 
                   p.unidade_comercial, p.preco_unitario_padrao,
                   p.ativo, n.codigo as ncm_codigo
            FROM produtos p
            LEFT JOIN ncms n ON p.ncm_id = n.ncm_id
            WHERE p.cliente_id = :cliente_id
            ORDER BY p.descricao
        """), {"cliente_id": cliente_id})
        
        produtos_join = [dict(row._mapping) for row in produtos_join_result]
        
        print(f"📊 COM JOIN: {len(produtos_join)} produtos encontrados")
        
        for produto in produtos_join:
            print(f"  • {produto['descricao']} | NCM: {produto['ncm_codigo']} | Ativo: {produto['ativo']}")
        
        # 3. VERIFICAR SE TEM NCMs NA TABELA
        print(f"\n📋 NCMs DISPONÍVEIS:")
        ncms_result = db.execute(text("""
            SELECT ncm_id, codigo, descricao FROM ncms LIMIT 5
        """))
        
        ncms = [dict(row._mapping) for row in ncms_result]
        print(f"📊 TOTAL NCMs: {len(ncms)} (mostrando 5)")
        
        for ncm in ncms:
            print(f"  • ID: {ncm['ncm_id']} | Código: {ncm['codigo']} | Desc: {ncm['descricao'][:50]}...")
        
        # 4. VERIFICAR FILTRO ATIVO
        print(f"\n📋 PRODUTOS FILTRADOS POR ATIVO:")
        produtos_ativo_result = db.execute(text("""
            SELECT COUNT(*) as total_todos,
                   COUNT(CASE WHEN ativo = true THEN 1 END) as total_ativos
            FROM produtos 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        stats = produtos_ativo_result.first()
        print(f"📊 Todos: {stats.total_todos} | Ativos: {stats.total_ativos}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    debug_produtos()