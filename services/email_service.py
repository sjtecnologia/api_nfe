import smtplib
import os
from dotenv import load_dotenv  # [OK] ADICIONAR ESTA LINHA
# [OK] CARREGAR .env ANTES DE TUDO
load_dotenv()
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr

class EmailService:
    def __init__(self):
        # Carregar variáveis de ambiente com debug
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_name = os.getenv('SMTP_FROM_NAME', 'EmiteMax')
        
        # Debug detalhado
        print(f"[?] EmailService Debug:")
        print(f"   SMTP_SERVER: {self.smtp_server}")
        print(f"   SMTP_PORT: {self.smtp_port}")
        print(f"   SMTP_USER: {self.smtp_user}")
        print(f"   SMTP_PASSWORD definida: {'Sim' if self.smtp_password else 'Não'}")
        print(f"   SMTP_PASSWORD length: {len(self.smtp_password) if self.smtp_password else 0}")
        print(f"   FROM_NAME: {self.from_name}")
        
        # Verificar se todas as variáveis estão definidas
        missing_vars = []
        if not self.smtp_server:
            missing_vars.append('SMTP_SERVER')
        if not self.smtp_user:
            missing_vars.append('SMTP_USER')
        if not self.smtp_password:
            missing_vars.append('SMTP_PASSWORD')
            
        if missing_vars:
            print(f"[ERRO] Variáveis faltando no .env: {', '.join(missing_vars)}")
        else:
            print(f"[OK] Todas as variáveis de email estão configuradas")
    
    def enviar_email(self, destinatario, assunto, corpo_html, anexos=None):
        """Enviar email com anexos opcionais"""
        try:
            # Verificação mais específica
            if not self.smtp_user:
                print(f"[ERRO] SMTP_USER não definido")
                return {
                    'success': False,
                    'message': 'SMTP_USER não definido no arquivo .env'
                }
                
            if not self.smtp_password:
                print(f"[ERRO] SMTP_PASSWORD não definido")
                return {
                    'success': False,
                    'message': 'SMTP_PASSWORD não definido no arquivo .env'
                }
            
            print(f"[?] Preparando email:")
            print(f"   De: {self.smtp_user} ({self.from_name})")
            print(f"   Para: {destinatario}")
            print(f"   Assunto: {assunto}")
            print(f"   Anexos: {len(anexos) if anexos else 0}")
            
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = formataddr((self.from_name, self.smtp_user))
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            # Corpo do email
            msg.attach(MIMEText(corpo_html, 'html', 'utf-8'))
            print(f"[OK] Corpo do email anexado")
            
            # Anexos
            if anexos:
                print(f"[?] Processando {len(anexos)} anexo(s)...")
                for i, anexo in enumerate(anexos):
                    try:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(anexo['conteudo'])
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename="{anexo["nome"]}"'
                        )
                        msg.attach(part)
                        print(f"[OK] Anexo {i+1}: {anexo['nome']} ({len(anexo['conteudo'])} bytes)")
                    except Exception as e:
                        print(f"[ERRO] Erro no anexo {i+1}: {str(e)}")
                        return {
                            'success': False,
                            'message': f'Erro ao processar anexo {anexo["nome"]}: {str(e)}'
                        }
            
            print(f"[OUT] Conectando ao servidor SMTP {self.smtp_server}:{self.smtp_port}...")
            
            # Enviar com tratamento de erro específico
            try:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                print(f"[OK] Conectado ao servidor SMTP")
                
                server.starttls()
                print(f"[OK] TLS iniciado")
                
                server.login(self.smtp_user, self.smtp_password)
                print(f"[OK] Login realizado com sucesso")
                
                texto = msg.as_string()
                server.sendmail(self.smtp_user, destinatario, texto)
                server.quit()
                
                print(f"[?] Email enviado com sucesso!")
                
                return {
                    'success': True,
                    'message': f'Email enviado com sucesso para {destinatario}'
                }
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"[ERRO] Erro de autenticação SMTP: {str(e)}")
                return {
                    'success': False,
                    'message': 'Erro de autenticação: Verifique o email e senha de app do Gmail'
                }
            except smtplib.SMTPRecipientsRefused as e:
                print(f"[ERRO] Destinatário rejeitado: {str(e)}")
                return {
                    'success': False,
                    'message': f'Email destinatário inválido: {destinatario}'
                }
            except smtplib.SMTPException as e:
                print(f"[ERRO] Erro SMTP geral: {str(e)}")
                return {
                    'success': False,
                    'message': f'Erro no servidor de email: {str(e)}'
                }
            
        except Exception as e:
            print(f"[ERRO] Erro geral ao enviar email: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }


def enviar_email_recuperacao_senha(destinatario, usuario, reset_url):
    """
    Envia email com link de recuperação de senha
    """
    assunto = "Recuperação de Senha - EmiteMax"
    
    corpo_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .header {{
                background: linear-gradient(135deg, #00bcd4 0%, #0097a7 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 10px 10px 0 0;
            }}
            .content {{
                background-color: white;
                padding: 30px;
                border-radius: 0 0 10px 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .button {{
                display: inline-block;
                background-color: #00bcd4;
                color: white;
                padding: 15px 30px;
                text-decoration: none;
                border-radius: 5px;
                margin: 20px 0;
                font-weight: bold;
            }}
            .button:hover {{
                background-color: #0097a7;
            }}
            .warning {{
                background-color: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 20px;
                color: #666;
                font-size: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Recuperação de Senha</h1>
                <p>EmiteMax - Sistema de Emissão de Notas Fiscais</p>
            </div>
            
            <div class="content">
                <p>Olá, <strong>{usuario}</strong>!</p>
                
                <p>Recebemos uma solicitação para redefinir a senha da sua conta no EmiteMax.</p>
                
                <p>Clique no botão abaixo para criar uma nova senha:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Redefinir Senha</a>
                </div>
                
                <p>Ou copie e cole este link no seu navegador:</p>
                <p style="word-break: break-all; color: #00bcd4;">{reset_url}</p>
                
                <div class="warning">
                    <strong>⚠️ Importante:</strong>
                    <ul>
                        <li>Este link é válido por <strong>1 hora</strong></li>
                        <li>Por motivos de segurança, o link só pode ser usado uma vez</li>
                        <li>Se você não solicitou esta redefinição, ignore este email</li>
                    </ul>
                </div>
                
                <p>Se você tiver alguma dúvida, entre em contato com nosso suporte.</p>
                
                <p>Atenciosamente,<br>
                <strong>Equipe EmiteMax</strong></p>
            </div>
            
            <div class="footer">
                <p>Este é um email automático, por favor não responda.</p>
                <p>&copy; 2025 EmiteMax - Todos os direitos reservados</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    email_service = EmailService()
    return email_service.enviar_email(destinatario, assunto, corpo_html)