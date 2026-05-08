import os

def verificar_home_routes():
    """Verificar rotas home"""
    
    file_path = '/Users/renato/Documents/Developement/api_nfe/routes/home_routes.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            print("📄 ROTAS HOME:")
            print("="*50)
            
            # Procurar por rotas principais
            for i, line in enumerate(lines, 1):
                if '@' in line or 'def ' in line:
                    print(f"Linha {i:3d}: {line.strip()}")
    else:
        print("❌ Arquivo home_routes.py não encontrado")

if __name__ == "__main__":
    verificar_home_routes()