import smtplib
import os
from dotenv import load_dotenv
load_dotenv()
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, make_msgid


def _build_mime_message(from_addr, from_name, destinatario, assunto, corpo_html, anexos):
    """Monta a mensagem MIME completa com texto plano alternativo e anexos."""
    msg = MIMEMultipart('mixed')
    msg['From'] = formataddr((from_name, from_addr))
    msg['To'] = destinatario
    msg['Subject'] = assunto
    msg['Message-ID'] = make_msgid(domain='emitemax.com.br')
    msg['Reply-To'] = formataddr((from_name, from_addr))

    # Corpo com fallback texto plano (reduz score de spam)
    import re as _re
    texto_plano = _re.sub(r'<[^>]+>', ' ', corpo_html)
    texto_plano = _re.sub(r'\s+', ' ', texto_plano).strip()

    alt = MIMEMultipart('alternative')
    alt.attach(MIMEText(texto_plano, 'plain', 'utf-8'))
    alt.attach(MIMEText(corpo_html, 'html', 'utf-8'))
    msg.attach(alt)

    if anexos:
        for anexo in anexos:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(anexo['conteudo'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{anexo["nome"]}"'
            )
            msg.attach(part)

    return msg


class EmailService:
    def __init__(self):
        self.from_name = (
            os.getenv('SMTP_FROM_NAME')
            or os.getenv('EMAIL_FROM_NAME', 'EmiteMax')
        )
        # AWS SES (preferido)
        self.ses_key = os.getenv('AWS_SES_ACCESS_KEY_ID')
        self.ses_secret = os.getenv('AWS_SES_SECRET_ACCESS_KEY')
        self.ses_region = os.getenv('AWS_SES_REGION', 'us-east-1')
        self.ses_from = os.getenv('SES_FROM_EMAIL', 'nfe@emitemax.com.br')

        # SMTP (fallback)
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')

        if self.ses_key and self.ses_secret:
            print(f"[OK] EmailService: usando AWS SES ({self.ses_region}) — remetente: {self.ses_from}")
        elif self.smtp_user and self.smtp_password:
            print(f"[OK] EmailService: usando SMTP ({self.smtp_server}) — remetente: {self.smtp_user}")
        else:
            print("[AVISO] EmailService: nenhuma credencial de email configurada")

    # ------------------------------------------------------------------
    # Envio via AWS SES (send_raw_email suporta anexos e MIME completo)
    # ------------------------------------------------------------------
    def _enviar_ses(self, from_addr, destinatario, msg):
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client(
            'ses',
            region_name=self.ses_region,
            aws_access_key_id=self.ses_key,
            aws_secret_access_key=self.ses_secret,
        )
        try:
            response = client.send_raw_email(
                Source=msg['From'],
                Destinations=[destinatario],
                RawMessage={'Data': msg.as_bytes()},
            )
            message_id = response['MessageId']
            print(f"[OK] SES: email enviado — MessageId={message_id}")
            return {'success': True, 'message': f'Email enviado via SES para {destinatario}'}
        except ClientError as e:
            code = e.response['Error']['Code']
            detail = e.response['Error']['Message']
            print(f"[ERRO] SES ClientError {code}: {detail}")
            return {'success': False, 'message': f'Erro SES ({code}): {detail}'}

    # ------------------------------------------------------------------
    # Envio via SMTP (fallback)
    # ------------------------------------------------------------------
    def _enviar_smtp(self, destinatario, msg):
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.smtp_user, destinatario, msg.as_string())
            server.quit()
            print(f"[OK] SMTP: email enviado para {destinatario}")
            return {'success': True, 'message': f'Email enviado via SMTP para {destinatario}'}
        except smtplib.SMTPAuthenticationError:
            return {'success': False, 'message': 'Erro de autenticação SMTP'}
        except smtplib.SMTPRecipientsRefused:
            return {'success': False, 'message': f'Destinatário rejeitado: {destinatario}'}
        except smtplib.SMTPException as e:
            return {'success': False, 'message': f'Erro SMTP: {str(e)}'}

    # ------------------------------------------------------------------
    # Interface pública (mantém compatibilidade)
    # ------------------------------------------------------------------
    def enviar_email(self, destinatario, assunto, corpo_html, anexos=None, from_name=None):
        """Enviar email com anexos opcionais. Tenta SES primeiro; se falhar, cai no SMTP Gmail."""
        try:
            nome_remetente = from_name or self.from_name
            use_ses = bool(self.ses_key and self.ses_secret)
            has_smtp = bool(self.smtp_user and self.smtp_password)

            if not use_ses and not has_smtp:
                return {'success': False, 'message': 'Nenhuma credencial de email configurada no .env'}

            print(f"[EMAIL] Para: {destinatario}  Assunto: {assunto}  Anexos: {len(anexos) if anexos else 0}")

            if use_ses:
                print(f"[EMAIL] Transporte primário: SES ({self.ses_from})")
                msg_ses = _build_mime_message(self.ses_from, nome_remetente, destinatario, assunto, corpo_html, anexos)
                resultado = self._enviar_ses(self.ses_from, destinatario, msg_ses)

                if resultado['success']:
                    return resultado

                # SES falhou — tenta SMTP como contingência
                print(f"[AVISO] SES falhou: {resultado['message']}")
                if has_smtp:
                    print(f"[EMAIL] Contingência: tentando SMTP Gmail ({self.smtp_user})")
                    msg_smtp = _build_mime_message(self.smtp_user, nome_remetente, destinatario, assunto, corpo_html, anexos)
                    resultado_smtp = self._enviar_smtp(destinatario, msg_smtp)
                    if resultado_smtp['success']:
                        resultado_smtp['message'] += ' (via contingência SMTP)'
                    return resultado_smtp
                else:
                    return resultado  # retorna erro do SES se não há SMTP configurado

            elif has_smtp:
                print(f"[EMAIL] Transporte: SMTP Gmail ({self.smtp_user})")
                msg_smtp = _build_mime_message(self.smtp_user, nome_remetente, destinatario, assunto, corpo_html, anexos)
                return self._enviar_smtp(destinatario, msg_smtp)

        except Exception as e:
            import traceback
            print(f"[ERRO] Erro geral ao enviar email: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'message': f'Erro interno: {str(e)}'}


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

def gerar_template_email_nfe(nfe_id, numero_nfe, emitente, destinatario, chave_acesso, protocolo, data_autorizacao, valor_total, anexos):
    """Gera template HTML profissional para email de NFe"""
    lista_anexos = '<br>'.join([f'• {anexo["nome"]}' for anexo in anexos])
    if valor_total is not None:
        valor_formatado = f'R$ {float(valor_total):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        valor_formatado = 'R$ 0,00'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body{{font-family:'Segoe UI',sans-serif;line-height:1.6;color:#333;background:#f4f4f4;margin:0;padding:0}}
.container{{max-width:650px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.1)}}
.header{{background:linear-gradient(135deg,#00bcd4,#0097a7);color:#fff;padding:40px 30px;text-align:center}}
.content{{padding:40px 30px}}
.info-box{{background:#f8f9fa;border-left:5px solid #00bcd4;border-radius:8px;padding:25px;margin:30px 0}}
.info-row{{padding:12px 0;border-bottom:1px solid #e0e0e0}}
.info-row:last-child{{border-bottom:none}}
.label{{font-weight:600;color:#555;display:inline-block;min-width:180px}}
.chave{{font-family:monospace;font-size:13px;background:#fff;padding:8px;border-radius:4px;border:1px solid #ddd;word-break:break-all}}
.anexos-box{{background:#e3f2fd;border-radius:8px;padding:20px;margin:25px 0}}
.footer{{background:#f8f9fa;padding:30px;text-align:center;border-top:1px solid #e0e0e0;color:#666;font-size:13px}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h2 style="margin:0">EmiteMax</h2>
    <div style="font-size:14px;opacity:.9;letter-spacing:1px">SISTEMA DE EMISSÃO DE NOTAS FISCAIS</div>
  </div>
  <div class="content">
    <p><strong>Olá, {destinatario}!</strong></p>
    <p>Você recebeu uma <strong style="color:#00bcd4">Nota Fiscal Eletrônica</strong> autorizada pela SEFAZ.</p>
    <div class="info-box">
      <div class="info-row"><span class="label">🔢 Número NFe:</span> <strong>#{numero_nfe}</strong></div>
      <div class="info-row"><span class="label">🏢 Emitente:</span> {emitente}</div>
      <div class="info-row"><span class="label">👤 Destinatário:</span> {destinatario}</div>
      <div class="info-row"><span class="label">💰 Valor Total:</span> <strong style="color:#00bcd4;font-size:18px">{valor_formatado}</strong></div>
      <div class="info-row"><span class="label">🔐 Protocolo:</span> {protocolo}</div>
      <div class="info-row"><span class="label">📅 Autorização:</span> {data_autorizacao}</div>
      <div class="info-row"><span class="label">🔑 Chave de Acesso:</span><br><div class="chave">{chave_acesso}</div></div>
    </div>
    <div class="anexos-box">
      <strong style="color:#0277bd">📎 Arquivos anexados:</strong><br>
      <div style="margin-top:10px">{lista_anexos}</div>
    </div>
    <p style="padding:15px;background:#fff3cd;border-radius:8px;border-left:4px solid #ffc107">
      <strong>⚠️ Importante:</strong> Guarde este email e os arquivos para sua contabilidade e controle fiscal.
    </p>
  </div>
  <div class="footer">
    <div>Este é um email automático. Por favor, não responda.</div>
    <div style="margin-top:10px"><strong>EmiteMax</strong> — Sistema de emissão de notas fiscais eletrônicas</div>
    <div style="color:#999;margin-top:8px">© 2026 EmiteMax. Todos os direitos reservados.</div>
  </div>
</div>
</body>
</html>"""


def enviar_nfe_automaticamente(nfe_id, db_session=None):
    """
    Envia NFe automaticamente após autorização pela SEFAZ.
    Busca email do destinatário no cadastro ou nos dados JSON da NFe.
    """
    from sqlalchemy import text
    import json
    import os
    import re

    fechar_sessao = False
    if db_session is None:
        from database.database import get_db
        db_session = next(get_db())
        fechar_sessao = True

    try:
        print(f"📧 [AUTO-EMAIL] Iniciando envio automático para NFe #{nfe_id}")

        query = text("""
            SELECT
                n.*,
                c.razao_social AS emitente_nome,
                d.email       AS destinatario_email,
                d.nome_razao_social AS destinatario_nome
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

        nfe_data = dict(nfe._mapping) if hasattr(nfe, '_mapping') else nfe._asdict()

        # --- buscar email ---
        email_destino = nfe_data.get('destinatario_email')

        if not email_destino:
            json_nfe = nfe_data.get('json_nfe')
            if json_nfe and isinstance(json_nfe, str):
                try:
                    json_nfe = json.loads(json_nfe)
                except Exception:
                    pass
            if isinstance(json_nfe, dict):
                email_destino = json_nfe.get('destinatario', {}).get('email')

        if not email_destino:
            print(f"⚠️  [AUTO-EMAIL] NFe #{nfe_id} - Destinatário sem email cadastrado")
            return {'success': False, 'message': 'Destinatário sem email cadastrado'}

        email_destino = str(email_destino).strip()
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email_destino):
            print(f"❌ [AUTO-EMAIL] Email inválido: {email_destino}")
            return {'success': False, 'message': 'Email do destinatário inválido'}

        print(f"📧 [AUTO-EMAIL] Enviando para: {email_destino}")

        # --- preparar anexos ---
        anexos = []

        # XML
        json_nfe = nfe_data.get('json_nfe')
        if json_nfe:
            if isinstance(json_nfe, str):
                try:
                    json_nfe = json.loads(json_nfe)
                except Exception:
                    pass
            if isinstance(json_nfe, dict):
                xml_content = json_nfe.get('xml_content')
                if xml_content:
                    anexos.append({
                        'nome': f'NFe_{nfe_data.get("numero", nfe_id)}.xml',
                        'conteudo': xml_content.encode('utf-8') if isinstance(xml_content, str) else xml_content,
                        'tipo': 'application/xml'
                    })
                    print("✅ [AUTO-EMAIL] XML adicionado")

        # DANFE
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        danfe_path = os.path.join(app_root, 'static', 'danfe', f'danfe_{nfe_id}.pdf')

        if not os.path.exists(danfe_path):
            print("📄 [AUTO-EMAIL] DANFE não encontrado, tentando gerar...")
            try:
                from services.danfe_service import generate_danfe
                xml_nfe = nfe_data.get('xml_autorizado') or nfe_data.get('xml_nfe')
                if not xml_nfe:
                    jn = nfe_data.get('json_nfe')
                    if isinstance(jn, str):
                        try:
                            jn = json.loads(jn)
                        except Exception:
                            pass
                    if isinstance(jn, dict):
                        xml_nfe = jn.get('xml_content')
                if xml_nfe:
                    gerado = generate_danfe(xml_nfe, nfe_id, nfe_data.get('cliente_id'))
                    if gerado and os.path.exists(gerado):
                        danfe_path = gerado
                        print(f"✅ [AUTO-EMAIL] DANFE gerado: {danfe_path}")
            except Exception as e_danfe:
                print(f"❌ [AUTO-EMAIL] Erro ao gerar DANFE: {e_danfe}")

        if os.path.exists(danfe_path):
            with open(danfe_path, 'rb') as f:
                anexos.append({
                    'nome': f'DANFE_NFe_{nfe_data.get("numero", nfe_id)}.pdf',
                    'conteudo': f.read(),
                    'tipo': 'application/pdf'
                })
            print("✅ [AUTO-EMAIL] DANFE adicionado")
        else:
            print(f"⚠️  [AUTO-EMAIL] DANFE indisponível: {danfe_path}")

        if not anexos:
            return {'success': False, 'message': 'Nenhum anexo disponível'}

        # --- montar e enviar ---
        numero = nfe_data.get('numero', 'N/A')
        emitente_nome = nfe_data.get('emitente_nome', 'N/A')
        destinatario_nome = (nfe_data.get('destinatario_nome') or
                             nfe_data.get('destinatario_razao_social') or 'Cliente')
        chave = nfe_data.get('chave_acesso', 'N/A')
        protocolo = nfe_data.get('protocolo_sefaz', 'N/A')
        data_aut = nfe_data.get('data_autorizacao')
        data_aut_str = data_aut.strftime('%d/%m/%Y às %H:%M') if data_aut else 'N/A'
        valor = nfe_data.get('valor_total', 0)

        assunto = f'Nota Fiscal Eletrônica #{numero} - {emitente_nome}'
        corpo_html = gerar_template_email_nfe(
            nfe_id=nfe_id,
            numero_nfe=numero,
            emitente=emitente_nome,
            destinatario=destinatario_nome,
            chave_acesso=chave,
            protocolo=protocolo,
            data_autorizacao=data_aut_str,
            valor_total=valor,
            anexos=anexos
        )

        email_svc = EmailService()
        resultado = email_svc.enviar_email(
            destinatario=email_destino,
            assunto=assunto,
            corpo_html=corpo_html,
            anexos=anexos
        )

        if resultado.get('success'):
            print(f"✅ [AUTO-EMAIL] Email enviado para {email_destino}")
        else:
            print(f"❌ [AUTO-EMAIL] Falha: {resultado.get('message')}")

        return resultado

    except Exception as e:
        import traceback
        print(f"❌ [AUTO-EMAIL] Erro inesperado: {e}")
        traceback.print_exc()
        return {'success': False, 'message': f'Erro ao enviar email: {str(e)}'}

    finally:
        if fechar_sessao:
            try:
                db_session.close()
            except Exception:
                pass
