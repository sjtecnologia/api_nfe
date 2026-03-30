# -*- coding: utf-8 -*-
"""
Wrapper de inicialização do app.py com encoding UTF-8 forçado.
Resolve problemas de emojis no Windows (charmap codec).

Uso no NSSM:
    Application Path: C:\nfe_app\venv\Scripts\python.exe
    Arguments: C:\nfe_app\run_app_utf8.py
"""

import sys
import os

# Forçar encoding UTF-8 em todas as saídas
if sys.platform == 'win32':
    # Windows: forçar UTF-8
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Configurar variável de ambiente
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    print("[INFO] Encoding UTF-8 configurado para Windows")

# Importar e executar o app principal
print("[INFO] Iniciando aplicação NFe...")

from app import app

if __name__ == '__main__':
    # Configurações do servidor
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 8080))
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    print(f"[INFO] Servidor rodando em {HOST}:{PORT}")
    print(f"[INFO] Debug mode: {DEBUG}")
    
    # Iniciar servidor
    app.run(
        host=HOST,
        port=PORT,
        debug=DEBUG,
        use_reloader=False  # Desabilitar reloader em produção
    )
