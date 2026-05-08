import os

def ver_home_completo():
    file_path = '/Users/renato/Documents/Developement/api_nfe/routes/home_routes.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("📄 CONTEÚDO COMPLETO - routes/home_routes.py")
            print("="*60)
            print(content)
    else:
        print("❌ Arquivo não encontrado")

if __name__ == "__main__":
    ver_home_completo()