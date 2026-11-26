# Script para testar imports - copiar e executar no Windows Server
import sys
print("Python version:", sys.version)
print("\nTesting imports...\n")

try:
    import flask
    print("✓ Flask:", flask.__version__)
except Exception as e:
    print("✗ Flask:", str(e))

try:
    import sqlalchemy
    print("✓ SQLAlchemy:", sqlalchemy.__version__)
except Exception as e:
    print("✗ SQLAlchemy:", str(e))

try:
    from flask_login import LoginManager
    print("✓ Flask-Login: OK")
except Exception as e:
    print("✗ Flask-Login:", str(e))

try:
    import psycopg2
    print("✓ psycopg2:", psycopg2.__version__)
except Exception as e:
    print("✗ psycopg2:", str(e))

try:
    from PIL import Image
    import PIL
    print("✓ Pillow:", PIL.__version__)
except Exception as e:
    print("✗ Pillow:", str(e))

try:
    import qrcode
    print("✓ qrcode:", qrcode.__version__)
except Exception as e:
    print("✗ qrcode:", str(e))

try:
    import lxml
    from lxml import etree
    print("✓ lxml:", lxml.__version__)
except Exception as e:
    print("✗ lxml:", str(e))

try:
    import pandas
    print("✓ pandas:", pandas.__version__)
except Exception as e:
    print("✗ pandas:", str(e))

try:
    import numpy
    print("✓ numpy:", numpy.__version__)
except Exception as e:
    print("✗ numpy:", str(e))

try:
    import reportlab
    print("✓ reportlab:", reportlab.Version)
except Exception as e:
    print("✗ reportlab:", str(e))

try:
    import waitress
    print("✓ waitress: OK")
except Exception as e:
    print("✗ waitress:", str(e))

print("\n" + "="*50)
print("IMPORTANTE: Execute este script no Windows Server com:")
print("cd C:\\nfe_app")
print(".\\venv\\Scripts\\Activate.ps1")
print("python test_imports_windows.py")
print("="*50)
