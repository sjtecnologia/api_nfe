import os

def verificar_cliente_routes():
    """Verificar rotas de cliente"""
    
    file_path = '/Users/renato/Documents/Developement/api_nfe/routes/cliente_routes.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            print("📄 ROTAS DE CLIENTE:")
            print("="*50)
            
            # Procurar pela rota dashboard
            for i, line in enumerate(lines, 1):
                if 'dashboard' in line.lower() and ('@' in line or 'def' in line):
                    print(f"Linha {i:3d}: {line.strip()}")
                    # Mostrar próximas 5 linhas
                    for j in range(1, 6):
                        if i+j-1 < len(lines):
                            print(f"Linha {i+j:3d}: {lines[i+j-1].strip()}")
                    print("-" * 30)
    else:
        print("❌ Arquivo cliente_routes.py não encontrado")

if __name__ == "__main__":
    verificar_cliente_routes()