import os

def ver_user_completo():
    file_path = '/Users/renato/Documents/Developement/api_nfe/models/user.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("📄 CONTEÚDO COMPLETO - models/user.py")
            print("="*60)
            print(content)
    else:
        print("❌ Arquivo não encontrado")

if __name__ == "__main__":
    ver_user_completo()