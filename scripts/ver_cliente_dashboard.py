import os

def ver_cliente_dashboard():
    file_path = '/Users/renato/Documents/Developement/api_nfe/routes/cliente_routes.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            print("📄 FUNÇÃO DASHBOARD - cliente_routes.py")
            print("="*60)
            
            # Encontrar a função dashboard
            dashboard_found = False
            for i, line in enumerate(lines):
                if 'def dashboard(' in line:
                    dashboard_found = True
                    # Mostrar a função completa
                    for j in range(i, min(i+50, len(lines))):
                        if j > i and lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t') and 'def ' in lines[j]:
                            break
                        print(f"Linha {j+1:3d}: {lines[j]}")
                    break
            
            if not dashboard_found:
                print("❌ Função dashboard não encontrada")
                
    else:
        print("❌ Arquivo cliente_routes.py não encontrado")

if __name__ == "__main__":
    ver_cliente_dashboard()