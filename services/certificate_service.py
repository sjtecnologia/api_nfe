import base64
import tempfile
import os
from datetime import datetime
from flask import current_app, flash
from flask_login import current_user
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from database.models import CertificadoDigital

def process_certificate_upload(db_session, cliente_id, request_form, request_files):
    """Processa o upload de certificado digital"""
    cert_file = request_files.get('conteudo_certificado_file')
    
    if cert_file and cert_file.filename != '':
        try:
            file_content = cert_file.read()
            cert_password = request_form.get('cert_senha_certificado')
            if not cert_password:
                flash('Senha do certificado é obrigatória ao fazer upload de um arquivo.', 'danger')
                return False, None
            
            # Codificar em base64 para armazenamento
            encoded_content = base64.b64encode(file_content)
            encoded_password = base64.b64encode(cert_password.encode('utf-8'))
            
            print(f"DEBUG SAVE: Conteúdo original lido (bytes): {len(file_content)} bytes")
            print(f"DEBUG SAVE: Conteúdo codificado Base64 (bytes): {len(encoded_content)} bytes")
            print(f"DEBUG SAVE: Senha original (string): {len(cert_password)} caracteres")
            
            # Validar certificado
            try:
                p12_tuple = pkcs12.load_key_and_certificates( 
                    file_content,
                    cert_password.encode('utf-8'), 
                    default_backend()
                )
                private_key = p12_tuple[0]
                cert_x509_obj = p12_tuple[1]
            except ValueError as val_err:
                flash(f'Erro ao validar certificado: Formato de arquivo ou senha inválidos. Detalhes: {val_err}', 'danger')
                return False, None
            except Exception as other_err:
                flash(f'Erro inesperado na validação do certificado: {other_err}', 'danger')
                return False, None
            
            if not cert_x509_obj:
                flash(f'Não foi possível carregar o certificado do arquivo {cert_file.filename}.', 'danger')
                return False, None
            
            # Extrair informações do certificado
            fingerprint = cert_x509_obj.fingerprint(hashes.SHA256()).hex()
            validade_inicio_final = cert_x509_obj.not_valid_before_utc.replace(tzinfo=None)
            validade_fim_final = cert_x509_obj.not_valid_after_utc.replace(tzinfo=None)
            
            # Criar objeto certificado
            cert_obj = CertificadoDigital(
                cliente_id=cliente_id,
                fingerprint=fingerprint,
                conteudo_certificado=encoded_content,
                senha_certificado=encoded_password,
                validade_inicio=validade_inicio_final,
                validade_fim=validade_fim_final,
                ativo=request_form.get('cert_ativo') == 'on',
                data_upload=datetime.now(),
                nome_arquivo_original=request_form.get('cert_nome_arquivo_original') or cert_file.filename,
                created_by_user_id=current_user.id if current_user.is_authenticated else None
            )
            
            db_session.add(cert_obj)
            return True, cert_obj
            
        except Exception as e:
            flash(f'Erro inesperado ao processar o certificado: {e}', 'danger')
            current_app.logger.error(f"Certificate processing error: {e}", exc_info=True)
            return False, None
    
    return True, None

def get_active_certificate_for_client(db, cliente_id):
    """Busca o certificado ativo para um cliente específico"""
    try:
        cert = db.query(CertificadoDigital).filter(
            CertificadoDigital.cliente_id == cliente_id,
            CertificadoDigital.ativo == True
        ).first()
        
        if not cert:
            raise Exception(f"Nenhum certificado ativo encontrado para o cliente ID {cliente_id}")
        
        print(f"DEBUG RECUPERAR: Certificado ID recuperado: {cert.certificado_digital_id}")
        print(f"DEBUG RECUPERAR: Cliente ID do certificado: {cert.cliente_id}")
        print(f"DEBUG RECUPERAR: Ativo: {cert.ativo}")
        
        if not hasattr(cert, 'conteudo_certificado') or not hasattr(cert, 'senha_certificado'):
            raise Exception("Certificado não possui os campos necessários")
        
        if not cert.conteudo_certificado or not cert.senha_certificado:
            raise Exception("Conteúdo do certificado ou senha está vazio")
        
        # Decodificar dados do certificado
        decoded_content = _decode_certificate_data(cert.conteudo_certificado, "certificado")
        decoded_password = _decode_certificate_data(cert.senha_certificado, "senha")
        
        cert.conteudo_certificado = decoded_content
        cert.senha_certificado = decoded_password
        
        # Tentar validar PKCS#12
        _validate_pkcs12(decoded_content, decoded_password, cert)
        
        return cert
        
    except Exception as e:
        print(f"ERRO GERAL em get_active_certificate_for_client: {e}")
        raise Exception(f"Falha ao recuperar certificado: {e}")

def _decode_certificate_data(raw_data, description="data"):
    """Decodifica dados do certificado que podem estar em diferentes formatos"""
    if isinstance(raw_data, bytes):
        print(f"DEBUG {description}: Já é bytes, usando diretamente")
        return raw_data
    
    if not isinstance(raw_data, str):
        raw_data = str(raw_data)
    
    # Tentar base64 primeiro (formato padrão de armazenamento)
    try:
        decoded_bytes = base64.b64decode(raw_data)
        print(f"DEBUG {description}: Sucesso com método 'base64' - tamanho: {len(decoded_bytes)} bytes")
        return decoded_bytes
    except Exception as e:
        print(f"DEBUG {description}: Método 'base64' falhou: {e}")
    
    # Se começar com \\x, tentar decodificação hex
    if raw_data.startswith('\\x'):
        try:
            hex_string = raw_data.replace('\\x', '')
            decoded_bytes = bytes.fromhex(hex_string)
            print(f"DEBUG {description}: Sucesso com método 'hex_direct' - tamanho: {len(decoded_bytes)} bytes")
            return decoded_bytes
        except Exception as e:
            print(f"DEBUG {description}: Método 'hex_direct' falhou: {e}")
            try:
                decoded_bytes = raw_data.encode('utf-8').decode('unicode_escape').encode('latin1')
                print(f"DEBUG {description}: Sucesso com método 'unicode_escape' - tamanho: {len(decoded_bytes)} bytes")
                return decoded_bytes
            except Exception as e2:
                print(f"DEBUG {description}: Método 'unicode_escape' falhou: {e2}")
    
    # Último recurso: UTF-8
    decoded_bytes = raw_data.encode('utf-8')
    print(f"DEBUG {description}: Usando método 'utf8_fallback' - tamanho: {len(decoded_bytes)} bytes")
    return decoded_bytes

def _validate_pkcs12(decoded_content, decoded_password, cert_obj):
    """Tenta validar o certificado PKCS#12 com diferentes variantes de senha"""
    print("DEBUG: Validando PKCS#12 com diferentes abordagens...")
    
    # Lista de senhas para testar
    password_variants = []
    
    if isinstance(decoded_password, bytes):
        password_variants.append(('bytes_direct', decoded_password))
        
        try:
            password_variants.append(('utf8_decode', decoded_password.decode('utf-8')))
        except:
            pass
        
        try:
            password_variants.append(('latin1_decode', decoded_password.decode('latin1')))
        except:
            pass
    
    # Adicionar senhas vazias e comuns
    password_variants.extend([
        ('empty_string', ''),
        ('empty_bytes', b''),
        ('none', None),
        ('test_123456', '123456'),
        ('test_password', 'password')
    ])
    
    for variant_name, password_to_test in password_variants:
        try:
            print(f"DEBUG: Testando senha variant '{variant_name}': {type(password_to_test)}")
            
            if isinstance(password_to_test, str):
                password_bytes = password_to_test.encode('utf-8')
            elif password_to_test is None:
                password_bytes = b''
            else:
                password_bytes = password_to_test
            
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                decoded_content, 
                password_bytes
            )
            
            print(f"✓ PKCS#12 validado com sucesso usando senha variant '{variant_name}'!")
            
            # Adicionar informações do certificado
            cert_obj.subject = certificate.subject.rfc4514_string()
            cert_obj.issuer = certificate.issuer.rfc4514_string()
            cert_obj.not_valid_before = certificate.not_valid_before
            cert_obj.not_valid_after = certificate.not_valid_after
            
            # Usar a senha que funcionou
            cert_obj.senha_certificado = password_bytes
            return True
            
        except Exception as pkcs_error:
            print(f"DEBUG: Variant '{variant_name}' falhou: {pkcs_error}")
            continue
    
    print(f"⚠️ AVISO: Nenhuma variante de senha funcionou para validar PKCS#12")
    print("Continuando mesmo assim para permitir modo simulado...")
    return False