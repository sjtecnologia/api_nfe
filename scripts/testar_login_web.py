import sys
import os
import requests

def testar_login_web():
    """Testar login via web"""
    
    try:
        # Testar se o servidor está rodando
        response = requests.get('http://127.0.0.1:8080/auth/login', timeout=5)
        print(f"✅ Servidor respondendo: {response.status_code}")
        
        # Testar POST do login
        login_data = {
            'username': 'sjtec',
            'password': 'ma0610',
            'remember_me': 'on'
        }
        
        session = requests.Session()
        
        # Fazer login
        response = session.post('http://127.0.0.1:8080/auth/login', data=login_data, timeout=5)
        print(f"📋 Login response: {response.status_code}")
        print(f"📋 Redirect location: {response.headers.get('Location', 'N/A')}")
        
        # Se houve redirecionamento, seguir
        if response.status_code in [302, 301]:
            final_url = response.headers.get('Location')
            if final_url:
                print(f"🔗 Seguindo redirecionamento para: {final_url}")
                
                # Se for URL relativa, fazer absoluta
                if final_url.startswith('/'):
                    final_url = 'http://127.0.0.1:8080' + final_url
                
                final_response = session.get(final_url, timeout=5)
                print(f"✅ Página final: {final_response.status_code}")
                
                if 'dashboard' in final_url:
                    print("🎉 LOGIN FUNCIONOU! Redirecionou para dashboard!")
                    return True
        
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ Servidor não está rodando em http://127.0.0.1:8080")
        return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

if __name__ == "__main__":
    print("🌐 TESTANDO LOGIN VIA WEB")
    print("="*40)
    testar_login_web()