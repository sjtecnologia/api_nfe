import os
from dotenv import load_dotenv
import smtplib

# Carregar variáveis do .env
load_dotenv()

def teste_direto():
    """Teste direto sem nossa classe para debug"""
    
    smtp_server = os.getenv('SMTP_SERVER')
    smtp_port = int(os.getenv('SMTP_PORT', 587))
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    print(f"[?] Configuração:")
    print(f"   Server: {smtp_server}:{smtp_port}")
    print(f"   User: {smtp_user}")
    print(f"   Password: {'*' * (len(smtp_password) if smtp_password else 0)}")
    print(f"   Password length: {len(smtp_password) if smtp_password else 0}")
    
    if not smtp_user or not smtp_password or not smtp_server:
        print("[X] Variáveis não definidas!")
        return
    
    try:
        print("\n[OUT] Testando conexão SMTP...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        print("[OK] Conectado")
        
        server.set_debuglevel(1)  # Debug detalhado
        server.starttls()
        print("[OK] TLS iniciado")
        
        server.login(smtp_user, smtp_password)
        print("[?] Login realizado com sucesso!")
        
        server.quit()
        return True
        
    except Exception as e:
        print(f"[X] Erro: {str(e)}")
        return False

def testar_com_classe():
    """Teste usando nossa classe"""
    from services.email_service import EmailService
    
    email_service = EmailService()
    
    resultado = email_service.enviar_email(
        destinatario="contato@sjtecnologia.com",
        assunto="Teste - Sistema NFe",
        corpo_html="<h1>Teste!</h1><p>Funcionou!</p>"
    )
    
    print(f"\n[?] Resultado da classe: {resultado}")

if __name__ == "__main__":
    print("=== TESTE DIRETO ===")
    if teste_direto():
        print("\n=== TESTE COM CLASSE ===")
        testar_com_classe()