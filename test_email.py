import os
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

from services.email_service import EmailService

def testar_email():
    email_service = EmailService()
    
    resultado = email_service.enviar_email(
        destinatario="contato@sjtecnologia.com",  # ✅ Usar um email real seu
        assunto="Teste - Sistema NFe",
        corpo_html="<h1>Teste de email!</h1><p>Se você recebeu este email, a configuração está funcionando.</p>"
    )
    
    print("Resultado do teste:", resultado)

if __name__ == "__main__":
    testar_email()