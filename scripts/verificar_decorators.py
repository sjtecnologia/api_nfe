import os

def verificar_decorators():
    """Verificar o conteúdo dos decorators de autenticação"""
    
    auth_files = [
        'auth/decorators.py',
        'auth/auth_routes.py',
        'auth/__init__.py'
    ]
    
    for file_path in auth_files:
        full_path = os.path.join('/Users/renato/Documents/Developement/api_nfe', file_path)
        
        print(f"\n📁 ARQUIVO: {file_path}")
        print("="*50)
        
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(content[:1000])  # Primeiros 1000 caracteres
                    if len(content) > 1000:
                        print("\n... (arquivo truncado)")
            except Exception as e:
                print(f"❌ Erro ao ler arquivo: {e}")
        else:
            print("❌ Arquivo não encontrado")

if __name__ == "__main__":
    verificar_decorators()