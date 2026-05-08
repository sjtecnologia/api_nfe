import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Vamos ver o arquivo de auth atual
print("🔍 CONTEÚDO DO ARQUIVO auth/routes.py:")
print("="*60)

try:
    with open('/Users/renato/Documents/Developement/api_nfe/auth/routes.py', 'r') as f:
        content = f.read()
        print(content)
except Exception as e:
    print(f"❌ Erro ao ler arquivo: {e}")