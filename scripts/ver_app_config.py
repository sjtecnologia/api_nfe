import os

def ver_app_config():
    file_path = '/Users/renato/Documents/Developement/api_nfe/app.py'
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            print("📄 CONFIGURAÇÕES RELEVANTES - app.py")
            print("="*60)
            
            # Procurar por configurações do Flask-Login
            for i, line in enumerate(lines, 1):
                if any(keyword in line.lower() for keyword in ['login_manager', 'flask_login', 'user_loader', 'login_required']):
                    print(f"Linha {i:3d}: {line}")
                    
            # Procurar por registros de blueprints de auth
            print("\n🔗 REGISTROS DE BLUEPRINTS:")
            print("-" * 30)
            for i, line in enumerate(lines, 1):
                if 'register_blueprint' in line and 'auth' in line.lower():
                    print(f"Linha {i:3d}: {line}")
    else:
        print("❌ Arquivo não encontrado")

if __name__ == "__main__":
    ver_app_config()