import os

def ver_login_manager():
    file_path = '/Users/renato/Documents/Developement/api_nfe/auth/login_manager.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("📄 CONTEÚDO - auth/login_manager.py")
            print("="*60)
            print(content)
    else:
        print("❌ Arquivo auth/login_manager.py não encontrado")
    
    # Verificar também se existe models/user.py
    user_model_path = '/Users/renato/Documents/Developement/api_nfe/models/user.py'
    if os.path.exists(user_model_path):
        print("\n📄 CONTEÚDO - models/user.py")
        print("="*60)
        with open(user_model_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content[:1500])  # Primeiros 1500 caracteres
            if len(content) > 1500:
                print("\n... (arquivo truncado)")
    else:
        print("\n❌ Arquivo models/user.py não encontrado")

if __name__ == "__main__":
    ver_login_manager()