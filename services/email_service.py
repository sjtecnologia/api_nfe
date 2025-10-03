import smtplib
import os
from dotenv import load_dotenv  # ✅ ADICIONAR ESTA LINHA
# ✅ CARREGAR .env ANTES DE TUDO
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
        self.from_name = os.getenv('SMTP_FROM_NAME', 'Sistema NFe')
        
        # Debug detalhado
        print(f"🔧 EmailService Debug:")
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
            print(f"❌ Variáveis faltando no .env: {', '.join(missing_vars)}")
        else:
            print(f"✅ Todas as variáveis de email estão configuradas")
    
    def enviar_email(self, destinatario, assunto, corpo_html, anexos=None):
        """Enviar email com anexos opcionais"""
        try:
            # Verificação mais específica
            if not self.smtp_user:
                print(f"❌ SMTP_USER não definido")
                return {
                    'success': False,
                    'message': 'SMTP_USER não definido no arquivo .env'
                }
                
            if not self.smtp_password:
                print(f"❌ SMTP_PASSWORD não definido")
                return {
                    'success': False,
                    'message': 'SMTP_PASSWORD não definido no arquivo .env'
                }
            
            print(f"📧 Preparando email:")
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
            print(f"✅ Corpo do email anexado")
            
            # Anexos
            if anexos:
                print(f"📎 Processando {len(anexos)} anexo(s)...")
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
                        print(f"✅ Anexo {i+1}: {anexo['nome']} ({len(anexo['conteudo'])} bytes)")
                    except Exception as e:
                        print(f"❌ Erro no anexo {i+1}: {str(e)}")
                        return {
                            'success': False,
                            'message': f'Erro ao processar anexo {anexo["nome"]}: {str(e)}'
                        }
            
            print(f"📤 Conectando ao servidor SMTP {self.smtp_server}:{self.smtp_port}...")
            
            # Enviar com tratamento de erro específico
            try:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                print(f"✅ Conectado ao servidor SMTP")
                
                server.starttls()
                print(f"✅ TLS iniciado")
                
                server.login(self.smtp_user, self.smtp_password)
                print(f"✅ Login realizado com sucesso")
                
                texto = msg.as_string()
                server.sendmail(self.smtp_user, destinatario, texto)
                server.quit()
                
                print(f"🎉 Email enviado com sucesso!")
                
                return {
                    'success': True,
                    'message': f'Email enviado com sucesso para {destinatario}'
                }
                
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Erro de autenticação SMTP: {str(e)}")
                return {
                    'success': False,
                    'message': 'Erro de autenticação: Verifique o email e senha de app do Gmail'
                }
            except smtplib.SMTPRecipientsRefused as e:
                print(f"❌ Destinatário rejeitado: {str(e)}")
                return {
                    'success': False,
                    'message': f'Email destinatário inválido: {destinatario}'
                }
            except smtplib.SMTPException as e:
                print(f"❌ Erro SMTP geral: {str(e)}")
                return {
                    'success': False,
                    'message': f'Erro no servidor de email: {str(e)}'
                }
            
        except Exception as e:
            print(f"❌ Erro geral ao enviar email: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Erro interno: {str(e)}'
            }