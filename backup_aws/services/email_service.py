import smtplib
import os
from dotenv import load_dotenv  # [OK] ADICIONAR ESTA LINHA
# [OK] CARREGAR .env ANTES DE TUDO
load_dotenv()
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
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
            
            # Anexar logo inline
            try:
                logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'emitemax.png')
                if os.path.exists(logo_path):
                    with open(logo_path, 'rb') as f:
                        logo_data = f.read()
                        logo_img = MIMEImage(logo_data)
                        logo_img.add_header('Content-ID', '<emitemax>')
                        logo_img.add_header('Content-Disposition', 'inline', filename='emitemax.png')
                        msg.attach(logo_img)
                        print(f"[OK] Logo EmiteMax anexada como inline ({len(logo_data)} bytes)")
            except Exception as e:
                print(f"[AVISO] Não foi possível anexar logo: {str(e)}")
            
            # Anexos
            if anexos:
                print(f"[?] Processando {len(anexos)} anexo(s)...")
                for i, anexo in enumerate(anexos):
                    try:
                        # Checar se é anexo inline (com CID)
                        if anexo.get('cid'):
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(anexo['conteudo'])
                            encoders.encode_base64(part)
                            part.add_header('Content-ID', f"<{anexo['cid']}>")
                            part.add_header('Content-Disposition', 'inline', filename=anexo['nome'])
                        else:
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


def enviar_nfe_automaticamente(nfe_id, db_session=None):
    """
    Envia NFe automaticamente após autorização pela SEFAZ
    Busca o email do destinatário no cadastro ou nos dados da NFe
    """
    from sqlalchemy import text
    import json
    import os
    
    # Se não passar sessão, criar uma nova
    if db_session is None:
        from database.database import get_db
        db_session = next(get_db())
        fechar_sessao = True
    else:
        fechar_sessao = False
    
    try:
        print(f"📧 [AUTO-EMAIL] Iniciando envio automático para NFe #{nfe_id}")
        
        # Buscar NFe com dados do destinatário
        query = text("""
            SELECT 
                n.*,
                c.razao_social as emitente_nome,
                d.email as destinatario_email,
                d.nome_razao_social as destinatario_nome
            FROM nfe_emitidas n
            JOIN clientes c ON n.cliente_id = c.cliente_id
            LEFT JOIN destinatarios_nfe d ON d.cpf_cnpj = n.destinatario_cnpj_cpf
            WHERE n.nfe_emitida_id = :nfe_id
        """)
        result = db_session.execute(query, {'nfe_id': nfe_id})
        nfe = result.first()
        
        if not nfe:
            print(f"❌ [AUTO-EMAIL] NFe #{nfe_id} não encontrada")
            return {'success': False, 'message': 'NFe não encontrada'}
        
        # Converter para dict
        nfe_data = dict(nfe._mapping) if hasattr(nfe, '_mapping') else nfe._asdict()
        
        # Verificar email do destinatário
        email_destino = nfe_data.get('destinatario_email')
        
        # Se não tiver email no cadastro, tentar buscar nos dados JSON da NFe (API)
        if not email_destino:
            json_nfe = nfe_data.get('json_nfe')
            if json_nfe and isinstance(json_nfe, str):
                try:
                    json_nfe = json.loads(json_nfe)
                except:
                    pass
            
            if isinstance(json_nfe, dict):
                # Tentar pegar email dos dados do destinatário na API
                email_destino = json_nfe.get('destinatario', {}).get('email')
        
        if not email_destino:
            print(f"⚠️  [AUTO-EMAIL] NFe #{nfe_id} - Destinatário sem email cadastrado")
            return {'success': False, 'message': 'Destinatário sem email cadastrado'}
        
        # Validar email
        import re
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_destino):
            print(f"❌ [AUTO-EMAIL] NFe #{nfe_id} - Email inválido: {email_destino}")
            return {'success': False, 'message': 'Email do destinatário inválido'}
        
        print(f"📧 [AUTO-EMAIL] Enviando para: {email_destino}")
        
        # Preparar anexos (XML e DANFE)
        anexos = []
        
        # Adicionar XML
        json_nfe = nfe_data.get('json_nfe')
        if json_nfe:
            if isinstance(json_nfe, str):
                try:
                    json_nfe = json.loads(json_nfe)
                except:
                    pass
            
            xml_content = json_nfe.get('xml_content') if isinstance(json_nfe, dict) else None
            if xml_content:
                anexos.append({
                    'nome': f'NFe_{nfe_data.get("numero", nfe_id)}.xml',
                    'conteudo': xml_content.encode('utf-8'),
                    'tipo': 'application/xml'
                })
                print(f"✅ [AUTO-EMAIL] XML adicionado")
        
        # Adicionar DANFE (verificar se existe ou gerar)
        danfe_path = os.path.join('static', 'danfe', f'danfe_{nfe_id}.pdf')
        if not os.path.isabs(danfe_path):
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            danfe_path = os.path.join(app_root, danfe_path)
        
        # Se DANFE não existe, tentar gerar
        if not os.path.exists(danfe_path):
            print(f"📄 [AUTO-EMAIL] DANFE não encontrado, gerando...")
            try:
                from services.danfe_service import generate_danfe
                
                # Buscar XML da NFe (pode estar em xml_autorizado, xml_nfe ou json_nfe)
                xml_nfe = nfe_data.get('xml_autorizado') or nfe_data.get('xml_nfe')
                
                # Se não tiver, tentar buscar do json_nfe
                if not xml_nfe:
                    json_nfe_data = nfe_data.get('json_nfe')
                    if json_nfe_data:
                        if isinstance(json_nfe_data, str):
                            try:
                                json_nfe_data = json.loads(json_nfe_data)
                            except:
                                pass
                        if isinstance(json_nfe_data, dict):
                            xml_nfe = json_nfe_data.get('xml_content')
                
                if xml_nfe:
                    # Gerar DANFE
                    danfe_gerado = generate_danfe(
                        xml_content=xml_nfe,
                        nfe_id=nfe_id,
                        cliente_id=nfe_data.get('cliente_id')
                    )
                    
                    if danfe_gerado and os.path.exists(danfe_gerado):
                        danfe_path = danfe_gerado
                        print(f"✅ [AUTO-EMAIL] DANFE gerado com sucesso: {danfe_path}")
                    else:
                        print(f"⚠️  [AUTO-EMAIL] Não foi possível gerar o DANFE")
                else:
                    print(f"⚠️  [AUTO-EMAIL] XML da NFe não disponível para gerar DANFE")
            except Exception as e:
                print(f"❌ [AUTO-EMAIL] Erro ao gerar DANFE: {str(e)}")
                import traceback
                traceback.print_exc()
        
        if os.path.exists(danfe_path):
            with open(danfe_path, 'rb') as pdf_file:
                pdf_content = pdf_file.read()
                anexos.append({
                    'nome': f'DANFE_NFe_{nfe_data.get("numero", nfe_id)}.pdf',
                    'conteudo': pdf_content,
                    'tipo': 'application/pdf'
                })
                print(f"✅ [AUTO-EMAIL] DANFE adicionado ao email")
        else:
            print(f"⚠️  [AUTO-EMAIL] DANFE não disponível: {danfe_path}")
        
        if not anexos:
            print(f"❌ [AUTO-EMAIL] Nenhum anexo disponível")
            return {'success': False, 'message': 'Nenhum anexo disponível'}
        
        # Montar email com template profissional
        assunto = f'Nota Fiscal Eletrônica #{nfe_data.get("numero")} - {nfe_data.get("emitente_nome", "")}'
        
        data_autorizacao = nfe_data.get('data_autorizacao')
        data_autorizacao_str = data_autorizacao.strftime('%d/%m/%Y às %H:%M') if data_autorizacao else 'N/A'
        
        corpo_html = gerar_template_email_nfe(
            nfe_id=nfe_id,
            numero_nfe=nfe_data.get('numero', 'N/A'),
            emitente=nfe_data.get('emitente_nome', 'N/A'),
            destinatario=nfe_data.get('destinatario_nome') or nfe_data.get('destinatario_razao_social', 'N/A'),
            chave_acesso=nfe_data.get('chave_acesso', 'N/A'),
            protocolo=nfe_data.get('protocolo_sefaz', 'N/A'),
            data_autorizacao=data_autorizacao_str,
            valor_total=nfe_data.get('valor_total', 0),
            anexos=anexos
        )
        
        # Enviar email
        email_service = EmailService()
        resultado = email_service.enviar_email(
            destinatario=email_destino,
            assunto=assunto,
            corpo_html=corpo_html,
            anexos=anexos
        )
        
        if resultado.get('success'):
            print(f"✅ [AUTO-EMAIL] Email enviado com sucesso para {email_destino}")
        else:
            print(f"❌ [AUTO-EMAIL] Erro ao enviar email: {resultado.get('message')}")
        
        return resultado
        
    except Exception as e:
        print(f"❌ [AUTO-EMAIL] Erro ao enviar NFe #{nfe_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': f'Erro ao enviar email: {str(e)}'}
    
    finally:
        if fechar_sessao:
            db_session.close()


def gerar_template_email_nfe(nfe_id, numero_nfe, emitente, destinatario, chave_acesso, protocolo, data_autorizacao, valor_total, anexos):
    """
    Gera template HTML profissional para email de NFe com logo da EmiteMax
    """
    # Lista de anexos para exibir no email
    lista_anexos = '<br>'.join([f'• {anexo["nome"]}' for anexo in anexos])
    
    # Formatar valor (tratar None)
    if valor_total is not None:
        valor_formatado = f'R$ {float(valor_total):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        valor_formatado = 'R$ 0,00'
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 650px;
                margin: 20px auto;
                background-color: #ffffff;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #00bcd4 0%, #0097a7 100%);
                color: white;
                padding: 40px 30px;
                text-align: center;
            }}
            .logo {{
                max-width: 120px;
                height: auto;
                margin: 0 auto 10px;
                display: block;
            }}
            .logo-subtitle {{
                font-size: 14px;
                opacity: 0.9;
                letter-spacing: 1px;
            }}
            .content {{
                padding: 40px 30px;
            }}
            .welcome {{
                font-size: 18px;
                color: #333;
                margin-bottom: 20px;
            }}
            .info-box {{
                background-color: #f8f9fa;
                border-left: 5px solid #00bcd4;
                border-radius: 8px;
                padding: 25px;
                margin: 30px 0;
            }}
            .info-row {{
                display: flex;
                padding: 12px 0;
                border-bottom: 1px solid #e0e0e0;
            }}
            .info-row:last-child {{
                border-bottom: none;
            }}
            .info-label {{
                font-weight: 600;
                color: #555;
                min-width: 180px;
                display: flex;
                align-items: center;
            }}
            .info-value {{
                color: #333;
                flex: 1;
                word-break: break-word;
            }}
            .chave-acesso {{
                font-family: 'Courier New', monospace;
                font-size: 13px;
                background-color: #fff;
                padding: 10px;
                border-radius: 4px;
                border: 1px solid #ddd;
            }}
            .anexos-box {{
                background: linear-gradient(135deg, #e3f2fd 0%, #f1f8ff 100%);
                border-radius: 8px;
                padding: 20px;
                margin: 25px 0;
            }}
            .anexos-title {{
                font-weight: 600;
                color: #0277bd;
                margin-bottom: 12px;
                font-size: 16px;
            }}
            .anexos-list {{
                color: #333;
                line-height: 2;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 30px;
                text-align: center;
                border-top: 1px solid #e0e0e0;
            }}
            .footer-text {{
                color: #666;
                font-size: 13px;
                margin: 5px 0;
            }}
            .highlight {{
                color: #00bcd4;
                font-weight: 600;
            }}
            .icon {{
                display: inline-block;
                margin-right: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="cid:emitemax" alt="EmiteMax" class="logo" />
                <div class="logo-subtitle">SISTEMA DE EMISSÃO DE NOTAS FISCAIS</div>
            </div>
            
            <div class="content">
                <div class="welcome">
                    <strong>Olá, {destinatario}!</strong>
                </div>
                
                <p>Você recebeu uma <span class="highlight">Nota Fiscal Eletrônica</span> autorizada pela SEFAZ.</p>
                <p>Confira os dados abaixo e encontre os arquivos digitais em anexo.</p>
                
                <div class="info-box">
                    <div class="info-row">
                        <div class="info-label"><span class="icon">🔢</span> Número NFe:</div>
                        <div class="info-value"><strong>#{numero_nfe}</strong></div>
                    </div>
                    <div class="info-row">
                        <div class="info-label"><span class="icon">🏢</span> Emitente:</div>
                        <div class="info-value">{emitente}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label"><span class="icon">👤</span> Destinatário:</div>
                        <div class="info-value">{destinatario}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label"><span class="icon">💰</span> Valor Total:</div>
                        <div class="info-value"><strong style="color: #00bcd4; font-size: 18px;">{valor_formatado}</strong></div>
                    </div>
                    <div class="info-row">
                        <div class="info-label"><span class="icon">🔐</span> Protocolo:</div>
                        <div class="info-value">{protocolo}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label"><span class="icon">📅</span> Autorização:</div>
                        <div class="info-value">{data_autorizacao}</div>
                    </div>
                    <div class="info-row">
                        <div class="info-label"><span class="icon">🔑</span> Chave de Acesso:</div>
                        <div class="info-value">
                            <div class="chave-acesso">{chave_acesso}</div>
                        </div>
                    </div>
                </div>
                
                <div class="anexos-box">
                    <div class="anexos-title">📎 Arquivos anexados neste email:</div>
                    <div class="anexos-list">{lista_anexos}</div>
                </div>
                
                <p style="margin-top: 30px; padding: 15px; background-color: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <strong>⚠️ Importante:</strong> Guarde este email e os arquivos anexos para sua contabilidade e controle fiscal.
                </p>
            </div>
            
            <div class="footer">
                <div class="footer-text">Este é um email automático. Por favor, não responda.</div>
                <div class="footer-text" style="margin-top: 15px;">
                    <strong>EmiteMax</strong> - Sistema profissional de emissão de notas fiscais eletrônicas
                </div>
                <div class="footer-text" style="color: #999; margin-top: 10px;">
                    © 2026 EmiteMax. Todos os direitos reservados.
                </div>
            </div>
        </div>
    </body>
    </html>
    """


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
                <p>&copy; 2026 EmiteMax - Todos os direitos reservados</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    email_service = EmailService()
    return email_service.enviar_email(destinatario, assunto, corpo_html)