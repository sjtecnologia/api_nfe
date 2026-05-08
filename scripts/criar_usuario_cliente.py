import sys
import os

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import get_db
from werkzeug.security import generate_password_hash
from sqlalchemy import text

def criar_usuario_cliente():
    """Script para criar um usuário cliente"""
    
    # Dados do usuário
    username = "sjtec"
    password = "ma0610"
    email = "contato@sjtec.com.br"
    
    try:
        # Conectar ao banco
        db = next(get_db())
        
        # 1. Verificar se já existe usuário com este username
        user_exists = db.execute(text("""
            SELECT id FROM users WHERE username = :username
        """), {"username": username}).first()
        
        if user_exists:
            print(f"❌ Usuário '{username}' já existe no sistema!")
            return False
        
        # 2. Buscar clientes disponíveis para mostrar opções
        clientes = db.execute(text("""
            SELECT cliente_id, razao_social, nome_fantasia, cnpj 
            FROM clientes 
            WHERE ativo = true
            ORDER BY razao_social
        """)).fetchall()
        
        if not clientes:
            print("❌ Nenhum cliente cadastrado no sistema!")
            return False
        
        print("\n📋 CLIENTES DISPONÍVEIS:")
        print("-" * 80)
        for cliente in clientes:
            fantasia = f" ({cliente.nome_fantasia})" if cliente.nome_fantasia and cliente.nome_fantasia != cliente.razao_social else ""
            cnpj_formatado = f"{cliente.cnpj[:2]}.{cliente.cnpj[2:5]}.{cliente.cnpj[5:8]}/{cliente.cnpj[8:12]}-{cliente.cnpj[12:]}"
            print(f"ID: {cliente.cliente_id:3d} | {cliente.razao_social}{fantasia}")
            print(f"      CNPJ: {cnpj_formatado}")
            print("-" * 80)
        
        # 3. Solicitar ID do cliente
        while True:
            try:
                cliente_id = input(f"\n🔹 Digite o ID do cliente para associar ao usuário '{username}': ")
                cliente_id = int(cliente_id)
                
                # Verificar se o cliente existe
                cliente_selecionado = db.execute(text("""
                    SELECT cliente_id, razao_social, nome_fantasia 
                    FROM clientes 
                    WHERE cliente_id = :cliente_id AND ativo = true
                """), {"cliente_id": cliente_id}).first()
                
                if cliente_selecionado:
                    break
                else:
                    print(f"❌ Cliente com ID {cliente_id} não encontrado!")
                    
            except ValueError:
                print("❌ Por favor, digite um número válido!")
        
        # 4. Gerar hash da senha
        password_hash = generate_password_hash(password)
        
        # 5. Inserir usuário (usando a estrutura correta da tabela)
        db.execute(text("""
            INSERT INTO users (username, password_hash, email, _is_active, created_at)
            VALUES (:username, :password_hash, :email, true, NOW())
        """), {
            "username": username,
            "password_hash": password_hash,
            "email": email
        })
        
        # 6. Obter ID do usuário criado
        user_result = db.execute(text("""
            SELECT id FROM users WHERE username = :username
        """), {"username": username}).first()
        
        user_id = user_result.id
        
        # 7. Associar usuário ao cliente na tabela user_clients
        db.execute(text("""
            INSERT INTO user_clients (user_id, client_id)
            VALUES (:user_id, :client_id)
        """), {
            "user_id": user_id,
            "client_id": cliente_id
        })
        
        # 8. Verificar se existe role de cliente e associar
        try:
            # Buscar role de cliente
            client_role = db.execute(text("""
                SELECT id FROM roles WHERE name = 'client' OR name = 'cliente'
            """)).first()
            
            if client_role:
                # Associar role ao usuário
                db.execute(text("""
                    INSERT INTO user_roles (user_id, role_id)
                    VALUES (:user_id, :role_id)
                """), {
                    "user_id": user_id,
                    "role_id": client_role.id
                })
                print(f"✅ Role '{client_role.id}' associada ao usuário")
            else:
                print("⚠️  Nenhuma role de cliente encontrada")
                
        except Exception as e:
            print(f"⚠️  Erro ao associar role: {str(e)} (continuando...)")
        
        # 9. Commit das alterações
        db.commit()
        
        # 10. Confirmar criação
        fantasia = f" ({cliente_selecionado.nome_fantasia})" if cliente_selecionado.nome_fantasia else ""
        
        print("\n" + "="*60)
        print("✅ USUÁRIO CLIENTE CRIADO COM SUCESSO!")
        print("="*60)
        print(f"👤 Username: {username}")
        print(f"🔒 Senha: {password}")
        print(f"📧 Email: {email}")
        print(f"🏢 Cliente: {cliente_selecionado.razao_social}{fantasia}")
        print(f"🆔 Cliente ID: {cliente_id}")
        print(f"🆔 Usuário ID: {user_id}")
        print("="*60)
        print("\n🎉 O usuário já pode fazer login no sistema!")
        print("🔗 URL de login: http://localhost:5000/login")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao criar usuário: {str(e)}")
        try:
            db.rollback()
        except:
            pass
        return False
    
    finally:
        try:
            db.close()
        except:
            pass

if __name__ == "__main__":
    print("🚀 CRIANDO USUÁRIO CLIENTE")
    print("="*40)
    
    success = criar_usuario_cliente()
    
    if success:
        print("\n✅ Script executado com sucesso!")
    else:
        print("\n❌ Falha na execução do script!")