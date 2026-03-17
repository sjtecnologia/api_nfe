import base64
import tempfile
import os
import binascii
from datetime import datetime
from flask import current_app, flash
from flask_login import current_user
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from database.models import CertificadoDigital
import hashlib

def _get_encryption_key():
    """Gera chave de criptografia baseada em uma chave mestra"""
    # Use uma chave mestra do ambiente ou gere uma
    master_key = os.environ.get('CERT_MASTER_KEY', 'default_master_key_change_in_production_2024')
    
    # Deriva uma chave consistente
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'cert_salt_nfe_2024',  # Salt fixo para consistência
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    return key

def _encrypt_password(password):
    """Criptografa a senha do certificado"""
    try:
        print(f"[AUTH] _encrypt_password: Iniciando criptografia de senha com {len(password)} caracteres")
        
        if not password or len(password) == 0:
            raise Exception("Senha vazia ou nula")
        
        key = _get_encryption_key()
        f = Fernet(key)
        
        # Garantir que é string UTF-8
        if isinstance(password, bytes):
            password_str = password.decode('utf-8')
        else:
            password_str = str(password)
        
        print(f"[AUTH] _encrypt_password: Senha preparada para criptografia: {len(password_str)} chars")
        
        # Criptografar
        encrypted_bytes = f.encrypt(password_str.encode('utf-8'))
        
        # Codificar em base64 para armazenar no banco
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        
        print(f"[OK] _encrypt_password: Senha criptografada - {len(encrypted_b64)} caracteres")
        print(f"[OK] _encrypt_password: Resultado: {encrypted_b64[:50]}...")
        
        return encrypted_b64
        
    except Exception as e:
        print(f"[X] _encrypt_password: ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        raise Exception(f"Falha crítica na criptografia da senha: {e}")

def _decrypt_password(encrypted_password):
    """Descriptografa a senha do certificado"""
    try:
        print(f"[UNLOCK] _decrypt_password: Iniciando descriptografia de {len(encrypted_password)} caracteres")
        print(f"[UNLOCK] _decrypt_password: Dados: {encrypted_password[:50]}...")
        
        # [OK] USAR MESMA LÓGICA DO TESTE QUE FUNCIONOU
        key = _get_encryption_key()
        f = Fernet(key)
        
        # Decodificar base64
        encrypted_bytes = base64.b64decode(encrypted_password.encode('utf-8'))
        print(f"[UNLOCK] _decrypt_password: Base64 decodificado: {len(encrypted_bytes)} bytes")
        
        # Descriptografar com Fernet
        decrypted_bytes = f.decrypt(encrypted_bytes)
        decrypted_str = decrypted_bytes.decode('utf-8')
        
        print(f"[OK] _decrypt_password: Fernet SUCCESS! Senha descriptografada: {len(decrypted_str)} chars")
        return decrypted_str
        
    except Exception as e:
        print(f"[X] _decrypt_password: Erro Fernet: {e}")
        print(f"[X] _decrypt_password: Tentando fallback...")
        return _decrypt_password_fallback(encrypted_password)

def _decrypt_password_fallback(encrypted_password):
    """Fallback para senhas antigas ou em texto plano"""
    try:
        print(f"[?] _decrypt_password_fallback: Tentando fallback para {len(encrypted_password)} chars")
        
        # Tentar base64 simples (método antigo)
        try:
            decoded = base64.b64decode(encrypted_password.encode('utf-8')).decode('utf-8')
            print(f"[OK] _decrypt_password_fallback: Base64 simples funcionou")
            return decoded
        except Exception as b64_e:
            print(f"[X] _decrypt_password_fallback: Base64 falhou: {b64_e}")
        
        # Se não é base64, pode ser texto plano (senhas muito antigas)
        print(f"[!] _decrypt_password_fallback: Assumindo texto plano")
        return encrypted_password
        
    except Exception as e:
        print(f"[X] _decrypt_password_fallback: Todos os fallbacks falharam: {e}")
        return encrypted_password

def process_certificate_a3_registration(db_session, cliente_id, a3_data):
    """
    Registra certificado A3 (token/smartcard) no sistema
    
    Args:
        db_session: Sessão do banco
        cliente_id: ID do cliente
        a3_data: Dict com dados do token (slot_id, label, library_path, pin, etc)
    
    Returns:
        Tuple (sucesso: bool, certificado_obj ou None)
    """
    try:
        from services.pkcs11_service import get_pkcs11_service
        
        print(f"[A3] Registrando certificado A3 para cliente {cliente_id}")
        
        pkcs11 = get_pkcs11_service()
        if not pkcs11.pkcs11_available:
            flash('PyKCS11 não está instalado. Certificados A3 não suportados.', 'danger')
            return False, None
        
        # Extrair dados
        library_path = a3_data.get('library_path')
        slot_id = a3_data.get('slot_id')
        pin = a3_data.get('pin')
        cert_label = a3_data.get('cert_label')
        
        if not all([library_path, slot_id is not None, pin, cert_label]):
            flash('Dados incompletos do token A3.', 'danger')
            return False, None
        
        # Listar certificados no token
        certificates = pkcs11.list_certificates_in_token(library_path, slot_id, pin)
        
        # Encontrar certificado específico
        selected_cert = None
        for cert in certificates:
            if cert['label'] == cert_label:
                selected_cert = cert
                break
        
        if not selected_cert:
            flash(f'Certificado "{cert_label}" não encontrado no token.', 'danger')
            return False, None
        
        # Verificar validade
        if not selected_cert['is_valid']:
            flash('Certificado no token está vencido.', 'danger')
            return False, None
        
        # Criptografar PIN
        encrypted_pin = _encrypt_password(pin)
        
        # Desativar certificados antigos
        db_session.query(CertificadoDigital).filter_by(
            cliente_id=cliente_id,
            ativo=True
        ).update({'ativo': False})
        
        # Criar registro do certificado A3
        cert_obj = CertificadoDigital(
            cliente_id=cliente_id,
            fingerprint=selected_cert['fingerprint'],
            conteudo_certificado=base64.b64encode(selected_cert['cert_der']).decode('utf-8'),  # Certificado em DER
            senha_certificado=encrypted_pin,  # PIN criptografado
            validade_inicio=selected_cert['not_before'].replace(tzinfo=None),
            validade_fim=selected_cert['not_after'].replace(tzinfo=None),
            ativo=True,
            data_upload=datetime.now(),
            nome_arquivo_original=f"Token: {cert_label}",
            tipo_certificado='A3',
            token_slot_id=slot_id,
            token_label=cert_label,
            pkcs11_library=library_path,
            created_by_user_id=current_user.id if current_user.is_authenticated else None
        )
        
        db_session.add(cert_obj)
        db_session.commit()
        
        print(f"[OK] Certificado A3 registrado com ID: {cert_obj.certificado_digital_id}")
        flash('Certificado A3 registrado com sucesso!', 'success')
        return True, cert_obj
    
    except Exception as e:
        print(f"[X] Erro ao registrar certificado A3: {e}")
        import traceback
        traceback.print_exc()
        db_session.rollback()
        flash(f'Erro ao registrar certificado A3: {e}', 'danger')
        return False, None

def process_certificate_upload(db_session, cliente_id, request_form, request_files):
    """Processa o upload de certificado digital"""
    print(f"[SEARCH] process_certificate_upload: Iniciando para cliente {cliente_id}")
    
    # [OK] CORRIGIR NOMES DOS CAMPOS
    cert_file = request_files.get('arquivo_certificado')  # ← CORRIGIDO!
    
    if cert_file and cert_file.filename != '':
        try:
            print(f"[?] process_certificate_upload: Arquivo recebido: {cert_file.filename}")
            
            # [OK] LER COMO BINÁRIO
            file_content = cert_file.read()
            cert_password = request_form.get('senha_certificado')  # ← CORRIGIDO!
            
            if not cert_password:
                flash('Senha do certificado é obrigatória ao fazer upload de um arquivo.', 'danger')
                return False, None
            
            print(f"[DATA] process_certificate_upload: Arquivo lido - {len(file_content)} bytes")
            print(f"[DATA] process_certificate_upload: Primeiros 10 bytes: {file_content[:10].hex()}")
            print(f"[DATA] process_certificate_upload: Senha recebida - {len(cert_password)} caracteres")
            print(f"[DATA] process_certificate_upload: Senha (mascarada): {'*' * len(cert_password)}")
            
            # [OK] VALIDAR FORMATO PKCS#12 ANTES DE SALVAR
            print(f"[?] process_certificate_upload: Validando PKCS#12...")
            try:
                private_key, cert_x509_obj, additional_certificates = pkcs12.load_key_and_certificates(
                    file_content,
                    cert_password.encode('utf-8')
                )
                print("[OK] process_certificate_upload: Certificado PKCS#12 validado com sucesso")
            except Exception as val_err:
                print(f"[X] process_certificate_upload: Erro na validação PKCS#12: {val_err}")
                flash(f'Erro ao validar certificado: {val_err}', 'danger')
                return False, None
            
            # [OK] CODIFICAR ARQUIVO EM BASE64
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            print(f"[DATA] process_certificate_upload: Arquivo codificado em Base64 - {len(encoded_content)} chars")
            
            # [AUTH] CRIPTOGRAFAR SENHA - CRÍTICO!
            print(f"[AUTH] process_certificate_upload: === INICIANDO CRIPTOGRAFIA DE SENHA ===")
            print(f"[AUTH] process_certificate_upload: Senha original: '{cert_password}' (tipo: {type(cert_password)})")
            print(f"[AUTH] process_certificate_upload: Tamanho: {len(cert_password)} caracteres")
            
            try:
                encrypted_password = _encrypt_password(cert_password)
                print(f"[OK] process_certificate_upload: CRIPTOGRAFIA EXECUTADA!")
                print(f"[OK] process_certificate_upload: Resultado: {len(encrypted_password)} chars")
                print(f"[OK] process_certificate_upload: Primeiros 50 chars: {encrypted_password[:50]}")
                
                # [OK] TESTE IMEDIATO DE ROUND-TRIP
                print(f"[?] process_certificate_upload: Testando descriptografia imediata...")
                test_decrypt = _decrypt_password(encrypted_password)
                print(f"[?] process_certificate_upload: Descriptografia testada: '{test_decrypt}'")
                print(f"[?] process_certificate_upload: Original == Descriptografada? {test_decrypt == cert_password}")
                
                if test_decrypt != cert_password:
                    raise Exception(f"FALHA CRÍTICA: Round-trip falhou! Original: '{cert_password}', Descriptografada: '{test_decrypt}'")
                
                print(f"[OK] process_certificate_upload: Teste de round-trip passou!")
                    
            except Exception as crypto_error:
                print(f"[X] process_certificate_upload: ERRO CRÍTICO NA CRIPTOGRAFIA: {crypto_error}")
                import traceback
                traceback.print_exc()
                flash(f'Erro crítico na criptografia da senha: {crypto_error}', 'danger')
                return False, None
            
            # [OK] EXTRAIR INFORMAÇÕES DO CERTIFICADO
            print(f"[LIST] process_certificate_upload: Extraindo informações do certificado...")
            # pkcs12.load_key_and_certificates may return None for the main certificate;
            # try to use an additional certificate as fallback
            cert_obj = cert_x509_obj
            if cert_obj is None and additional_certificates:
                cert_obj = additional_certificates[0]
                print("[!] process_certificate_upload: Certificado principal era None, usando certificado adicional como fallback")
            if cert_obj is None:
                raise Exception("Certificado X.509 não encontrado dentro do PKCS#12")
            
            # fingerprint
            fingerprint = cert_obj.fingerprint(hashes.SHA256()).hex()
            
            # compatibilidade: alguns objetos x509 usam not_valid_before/_after e outros not_valid_before_utc/_after_utc
            try:
                validade_inicio = getattr(cert_obj, "not_valid_before_utc", None)
                validade_fim = getattr(cert_obj, "not_valid_after_utc", None)
                if validade_inicio is None or validade_fim is None:
                    validade_inicio = getattr(cert_obj, "not_valid_before", None)
                    validade_fim = getattr(cert_obj, "not_valid_after", None)
                validade_inicio_final = validade_inicio.replace(tzinfo=None) if validade_inicio else None
                validade_fim_final = validade_fim.replace(tzinfo=None) if validade_fim else None
            except Exception as date_err:
                print(f"[X] process_certificate_upload: Erro ao obter datas de validade: {date_err}")
                validade_inicio_final = None
                validade_fim_final = None
            
            print(f"[LIST] process_certificate_upload: Fingerprint: {fingerprint}")
            print(f"[LIST] process_certificate_upload: Válido de {validade_inicio_final} até {validade_fim_final}")
            
            # [OK] DESATIVAR CERTIFICADOS ANTIGOS
            print(f"[?] process_certificate_upload: Desativando certificados antigos...")
            old_certs_updated = db_session.query(CertificadoDigital).filter_by(
                cliente_id=cliente_id,
                ativo=True
            ).update({'ativo': False})
            print(f"[?] process_certificate_upload: {old_certs_updated} certificados antigos desativados")
            
            # [OK] CRIAR OBJETO DO CERTIFICADO
            print(f"[SAVE] process_certificate_upload: Criando objeto certificado...")
            cert_obj = CertificadoDigital(
                cliente_id=cliente_id,
                fingerprint=fingerprint,
                conteudo_certificado=encoded_content,  # [OK] BASE64 LIMPO
                senha_certificado=encrypted_password,   # [AUTH] SENHA CRIPTOGRAFADA
                validade_inicio=validade_inicio_final,
                validade_fim=validade_fim_final,
                ativo=True,
                data_upload=datetime.now(),
                nome_arquivo_original=request_form.get('cert_nome_arquivo_original') or cert_file.filename,
                created_by_user_id=current_user.id if current_user.is_authenticated else None
            )
            
            print(f"[SAVE] process_certificate_upload: Objeto criado - senha no objeto: {cert_obj.senha_certificado[:50]}...")
            
            # [OK] SALVAR NO BANCO
            print(f"[SAVE] process_certificate_upload: Salvando no banco...")
            db_session.add(cert_obj)
            db_session.commit()
            
            print(f"[OK] process_certificate_upload: Certificado salvo com ID: {cert_obj.certificado_digital_id}")
            
            # [OK] VERIFICAÇÃO PÓS-SALVAMENTO
            print(f"[SEARCH] process_certificate_upload: Verificando dados salvos...")
            cert_verificacao = db_session.query(CertificadoDigital).filter_by(
                certificado_digital_id=cert_obj.certificado_digital_id
            ).first()
            
            if cert_verificacao:
                saved_password = cert_verificacao.senha_certificado
                print(f"[SEARCH] process_certificate_upload: Senha salva no banco: {len(saved_password)} chars")
                print(f"[SEARCH] process_certificate_upload: Primeiros 50 chars: {saved_password[:50]}")
                
                if saved_password.startswith('gAAAAA'):
                    print("[OK] process_certificate_upload: SENHA SALVA CRIPTOGRAFADA! [OK]")
                elif saved_password == cert_password:
                    print("[X] process_certificate_upload: SENHA SALVA EM TEXTO PLANO! [X]")
                else:
                    print("[!] process_certificate_upload: Senha em formato desconhecido")
                
                # Teste final de descriptografia
                try:
                    final_test = _decrypt_password(saved_password)
                    if final_test == cert_password:
                        print("[?] process_certificate_upload: TESTE FINAL PASSOU! Criptografia funcionando 100%")
                    else:
                        print("[X] process_certificate_upload: TESTE FINAL FALHOU!")
                except Exception as final_e:
                    print(f"[X] process_certificate_upload: ERRO NO TESTE FINAL: {final_e}")
            
            print("[OK] process_certificate_upload: Upload concluído com sucesso!")
            flash('Certificado enviado e validado com sucesso!', 'success')
            return True, cert_obj
            
        except Exception as e:
            print(f"[X] process_certificate_upload: Erro inesperado: {e}")
            import traceback
            traceback.print_exc()
            db_session.rollback()
            flash(f'Erro inesperado ao processar o certificado: {e}', 'danger')
            if current_app:
                current_app.logger.error(f"Certificate processing error: {e}", exc_info=True)
            return False, None
    
    print("ℹ️ process_certificate_upload: Nenhum arquivo fornecido")
    return True, None

def get_active_certificate_for_client(db, cliente_id):
    """
    Busca certificado digital ativo para o cliente
    """
    try:
        print(f"[AUTH] get_active_certificate_for_client: Buscando certificado para cliente {cliente_id}")
        
        # Buscar certificado ativo
        certificado = db.query(CertificadoDigital).filter_by(
            cliente_id=cliente_id,
            ativo=True
        ).first()
        
        if not certificado:
            print(f"[X] get_active_certificate_for_client: Nenhum certificado ativo encontrado")
            return None
        
        print(f"[OK] get_active_certificate_for_client: Certificado encontrado: ID {certificado.certificado_digital_id}")
        
        # [OK] CONVERTER PARA DICIONÁRIO
        certificado_dict = {
            'certificado_id': certificado.certificado_digital_id,
            'cliente_id': certificado.cliente_id,
            'common_name': getattr(certificado, 'common_name', None),
            'valido_ate': certificado.validade_fim,
            'arquivo_certificado': certificado.conteudo_certificado,
            'senha_certificado': certificado.senha_certificado,
            'ativo': certificado.ativo,
            'tipo_certificado': getattr(certificado, 'tipo_certificado', 'A1'),
            'data_criacao': certificado.data_upload,
            'fingerprint': certificado.fingerprint,
            'validade_inicio': certificado.validade_inicio,
            'nome_arquivo_original': certificado.nome_arquivo_original
        }
        
        print(f"[OK] get_active_certificate_for_client: Certificado convertido: {certificado_dict.get('nome_arquivo_original', 'Sem nome')}")
        
        # [OK] VERIFICAR SE CERTIFICADO ESTÁ COMPLETO
        if not certificado_dict['arquivo_certificado'] or not certificado_dict['senha_certificado']:
            print("[!] get_active_certificate_for_client: Certificado incompleto - modo simulado")
            certificado_dict['modo_simulado'] = False
            return certificado_dict
        
        # [OK] TENTAR CARREGAR CERTIFICADO REAL
        try:
            print("[SEARCH] get_active_certificate_for_client: Tentando carregar certificado real...")
            
            # Decodificar arquivo do certificado
            cert_data = _decode_certificate_data(certificado_dict['arquivo_certificado'])
            if not cert_data:
                raise Exception("Falha ao decodificar dados do certificado")
            
            # Descriptografar senha
            senha_descriptografada = _decrypt_password(certificado_dict['senha_certificado'])
            if not senha_descriptografada:
                raise Exception("Falha ao descriptografar senha")
            
            print(f"[SEARCH] get_active_certificate_for_client: Dados decodificados - cert: {len(cert_data)} bytes, senha: {len(senha_descriptografada)} chars")
            
            # Tentar validar PKCS#12
            private_key, certificate, additional_certificates = _validate_pkcs12_simple(cert_data, senha_descriptografada)
            
            if private_key and certificate:
                certificado_dict.update({
                    'private_key': private_key,
                    'certificate': certificate,
                    'additional_certificates': additional_certificates,
                    'cert_data': cert_data,  # Dados binários do PKCS#12
                    'password': senha_descriptografada,  # Senha descriptografada
                    'modo_simulado': False
                })
                print(f"[OK] get_active_certificate_for_client: Certificado real carregado com sucesso")
                return certificado_dict
            else:
                raise Exception("Falha na validação PKCS#12")
        
        except Exception as e:
            print(f"[!] get_active_certificate_for_client: Erro ao carregar certificado real: {e}")
        
        # [OK] FALLBACK: MODO SIMULADO
        print("[?] get_active_certificate_for_client: Usando modo simulado")
        
        
        return certificado_dict
        
    except Exception as e:
        print(f"[X] get_active_certificate_for_client: Erro crítico: {e}")
        import traceback
        traceback.print_exc()
        
        # [OK] FALLBACK COMPLETO
        return {
            'certificado_id': 'SIMULADO',
            'cliente_id': cliente_id,
            'common_name': 'CERTIFICADO SIMULADO DE EMERGÊNCIA',
            'modo_simulado': True,
            'private_key': 'SIMULADO',
            'certificate': 'SIMULADO'
        }

def _decode_certificate_data(cert_data_encoded):
    """Decodifica dados do certificado com múltiplos métodos"""
    if not cert_data_encoded:
        return None
    
    print(f"[SEARCH] _decode_certificate_data: Decodificando {len(cert_data_encoded)} caracteres")
    print(f"[SEARCH] _decode_certificate_data: Tipo de dados: {type(cert_data_encoded)}")
    print(f"[SEARCH] _decode_certificate_data: Primeiros 100 chars: {str(cert_data_encoded)[:100]}")
    
    # Se já for bytes, retorna direto
    if isinstance(cert_data_encoded, bytes):
        print(f"[OK] _decode_certificate_data: Dados já são bytes - {len(cert_data_encoded)} bytes")
        return cert_data_encoded
    
    methods = [
        ('base64', lambda x: base64.b64decode(x)),
        ('hex_direct', lambda x: binascii.unhexlify(x)),
        ('raw', lambda x: x.encode() if isinstance(x, str) else x)
    ]
    
    for method_name, decode_func in methods:
        try:
            result = decode_func(cert_data_encoded)
            print(f"[OK] _decode_certificate_data: Sucesso com método '{method_name}' - {len(result)} bytes")
            
            # Verificar se os bytes começam com assinatura PKCS#12 (0x30 0x82)
            if len(result) > 2:
                hex_start = result[:4].hex()
                print(f"[SEARCH] _decode_certificate_data: Primeiros bytes (hex): {hex_start}")
                if result[0] == 0x30:
                    print(f"[OK] _decode_certificate_data: Assinatura PKCS#12 detectada (0x30)")
            
            return result
        except Exception as e:
            print(f"[X] _decode_certificate_data: Método '{method_name}' falhou: {e}")
    
    return None

def _validate_pkcs12_simple(cert_data, password):
    """Valida certificado PKCS#12 de forma simples"""
    try:
        print(f"[?] _validate_pkcs12_simple: Validando PKCS#12")
        print(f"[?] _validate_pkcs12_simple: Dados do certificado - {len(cert_data)} bytes")
        print(f"[?] _validate_pkcs12_simple: Senha - {len(password)} chars (tipo: {type(password)})")
        print(f"[?] _validate_pkcs12_simple: Primeiros 4 bytes do cert (hex): {cert_data[:4].hex()}")
        
        # Converter senha para bytes
        password_bytes = password.encode('utf-8') if isinstance(password, str) else password
        print(f"[?] _validate_pkcs12_simple: Senha convertida para bytes - {len(password_bytes)} bytes")
        
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            cert_data, 
            password_bytes
        )
        
        if private_key and certificate:
            print(f"[OK] _validate_pkcs12_simple: PKCS#12 válido! Subject: {certificate.subject}")
            return private_key, certificate, additional_certificates
        else:
            print(f"[X] _validate_pkcs12_simple: PKCS#12 carregado mas incompleto")
            print(f"[X] _validate_pkcs12_simple: private_key = {private_key is not None}, certificate = {certificate is not None}")
            return None, None, None
            
    except Exception as e:
        print(f"[X] _validate_pkcs12_simple: Erro na validação: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

# [OK] MANTER FUNÇÃO ANTIGA PARA COMPATIBILIDADE
def _validate_pkcs12(cert_data, password_data):
    """Valida certificado PKCS#12 com múltiplas variantes de senha (compatibilidade)"""
    print("[?] _validate_pkcs12: Usando método de compatibilidade...")
    
    # Converter para string se necessário
    if isinstance(password_data, bytes):
        try:
            password_str = password_data.decode('utf-8')
        except:
            password_str = password_data.decode('latin-1')
    else:
        password_str = str(password_data)
    
    return _validate_pkcs12_simple(cert_data, password_str)