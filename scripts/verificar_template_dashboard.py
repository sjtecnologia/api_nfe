import os

def verificar_template_dashboard():
    template_path = '/Users/renato/Documents/Developement/api_nfe/templates/cliente/dashboard.html'
    
    if os.path.exists(template_path):
        print("✅ Template dashboard existe")
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"📄 Tamanho: {len(content)} caracteres")
            if len(content) < 100:
                print("⚠️  Template muito pequeno:")
                print(content)
    else:
        print("❌ Template dashboard NÃO existe")
        print(f"📁 Verificando pasta: {os.path.dirname(template_path)}")
        if os.path.exists(os.path.dirname(template_path)):
            files = os.listdir(os.path.dirname(template_path))
            print(f"📄 Arquivos na pasta cliente: {files}")
        else:
            print("❌ Pasta templates/cliente não existe")

if __name__ == "__main__":
    verificar_template_dashboard()