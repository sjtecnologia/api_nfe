import os

def encontrar_arquivos_auth():
    """Encontrar todos os arquivos relacionados à autenticação"""
    
    base_dir = '/Users/renato/Documents/Developement/api_nfe'
    
    # Procurar por arquivos que podem conter autenticação
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'login' in content.lower() and ('route' in content or 'blueprint' in content):
                            rel_path = os.path.relpath(file_path, base_dir)
                            print(f"\n📁 ENCONTRADO: {rel_path}")
                            
                            # Mostrar linhas com login
                            lines = content.split('\n')
                            for i, line in enumerate(lines, 1):
                                if 'def login' in line or '@' in line and 'login' in line:
                                    print(f"  Linha {i}: {line.strip()}")
                                    
                except Exception as e:
                    pass

if __name__ == "__main__":
    print("🔍 PROCURANDO ARQUIVOS DE AUTENTICAÇÃO")
    print("="*50)
    encontrar_arquivos_auth()