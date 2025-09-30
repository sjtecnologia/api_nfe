import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verificar_dados_cliente():
    """Verificar todos os dados do cliente 5 (SJ TECNOLOGIA)"""
    try:
        from database.connection import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        cliente_id = 5
        
        print(f"🔍 VERIFICANDO DADOS DO CLIENTE {cliente_id}")
        print("="*60)
        
        # 1. PRODUTOS - Query corrigida
        produtos_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM produtos 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        
        produtos_count = produtos_result.first().total
        print(f"📦 PRODUTOS: {produtos_count} cadastrados")
        
        # Exemplos de produtos (query separada)
        if produtos_count > 0:
            produtos_exemplos = db.execute(text("""
                SELECT descricao 
                FROM produtos 
                WHERE cliente_id = :cliente_id AND ativo = true
                ORDER BY descricao
                LIMIT 3
            """), {"cliente_id": cliente_id})
            
            exemplos = [row.descricao for row in produtos_exemplos]
            print(f"   Exemplos: {', '.join(exemplos)}")
        
        # 2. DESTINATÁRIOS - Query corrigida
        destinatarios_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM destinatarios 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        
        dest_count = destinatarios_result.first().total
        print(f"🏢 DESTINATÁRIOS: {dest_count} cadastrados")
        
        # Exemplos de destinatários
        if dest_count > 0:
            dest_exemplos = db.execute(text("""
                SELECT razao_social 
                FROM destinatarios 
                WHERE cliente_id = :cliente_id AND ativo = true
                ORDER BY razao_social
                LIMIT 3
            """), {"cliente_id": cliente_id})
            
            exemplos = [row.razao_social for row in dest_exemplos]
            print(f"   Exemplos: {', '.join(exemplos)}")
        
        # 3. REGRAS TRIBUTÁRIAS
        regras_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM regras_tributacao 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        
        regras_count = regras_result.first().total
        print(f"📋 REGRAS TRIBUTÁRIAS: {regras_count} cadastradas")
        
        # 4. CERTIFICADOS
        cert_result = db.execute(text("""
            SELECT COUNT(*) as total,
                   MAX(data_upload) as ultimo_upload
            FROM certificados_digitais 
            WHERE cliente_id = :cliente_id AND ativo = true
        """), {"cliente_id": cliente_id})
        
        cert_data = cert_result.first()
        cert_count = cert_data.total or 0
        print(f"🔐 CERTIFICADOS: {cert_count} cadastrados")
        if cert_data.ultimo_upload:
            print(f"   Último upload: {cert_data.ultimo_upload}")
        
        # 5. NFEs (para confirmar que está vazio)
        nfes_result = db.execute(text("""
            SELECT COUNT(*) as total
            FROM nfe_emitidas 
            WHERE cliente_id = :cliente_id
        """), {"cliente_id": cliente_id})
        
        nfes_count = nfes_result.first().total
        print(f"📄 NFEs EMITIDAS: {nfes_count}")
        
        print("\n" + "="*60)
        print("📊 RESUMO GERAL:")
        print(f"   • {produtos_count} produtos cadastrados")
        print(f"   • {dest_count} destinatários cadastrados") 
        print(f"   • {regras_count} regras tributárias")
        print(f"   • {cert_count} certificados digitais")
        print(f"   • {nfes_count} NFes emitidas")
        
        # 6. DETALHES DOS PRIMEIROS PRODUTOS
        if produtos_count > 0:
            print("\n📦 DETALHES DOS PRODUTOS:")
            produtos_detalhes = db.execute(text("""
                SELECT produto_id, descricao, unidade, preco_unitario, ncm_codigo
                FROM produtos 
                WHERE cliente_id = :cliente_id AND ativo = true
                ORDER BY descricao
                LIMIT 5
            """), {"cliente_id": cliente_id})
            
            for produto in produtos_detalhes:
                print(f"   • ID: {produto.produto_id} | {produto.descricao}")
                print(f"     Unidade: {produto.unidade} | Preço: R$ {produto.preco_unitario}")
                print(f"     NCM: {produto.ncm_codigo}")
                print("   " + "-"*40)
        
        # 7. DETALHES DOS PRIMEIROS DESTINATÁRIOS
        if dest_count > 0:
            print("\n🏢 DETALHES DOS DESTINATÁRIOS:")
            dest_detalhes = db.execute(text("""
                SELECT destinatario_id, razao_social, cnpj_cpf, nome_municipio, uf
                FROM destinatarios 
                WHERE cliente_id = :cliente_id AND ativo = true
                ORDER BY razao_social
                LIMIT 5
            """), {"cliente_id": cliente_id})
            
            for dest in dest_detalhes:
                print(f"   • ID: {dest.destinatario_id} | {dest.razao_social}")
                print(f"     CNPJ/CPF: {dest.cnpj_cpf}")
                print(f"     Local: {dest.nome_municipio}/{dest.uf}")
                print("   " + "-"*40)
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    verificar_dados_cliente()