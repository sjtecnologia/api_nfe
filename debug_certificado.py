from database.connection import get_db
from database.models import CertificadoDigital
from services.certificate_service import _decrypt_password
import base64
import binascii

def diagnosticar_certificado(cliente_id=5):
    """
    Diagnostica problemas com certificado do cliente
    """
    print(f"🔍 === DIAGNÓSTICO CERTIFICADO CLIENTE {cliente_id} ===")
    
    db = next(get_db())
    
    try:
        # Buscar certificado
        cert = db.query(CertificadoDigital).filter_by(
            cliente_id=cliente_id,
            ativo=True
        ).first()
        
        if not cert:
            print("❌ Nenhum certificado ativo encontrado")
            return
        
        print(f"✅ Certificado encontrado: ID {cert.certificado_digital_id}")
        print(f"📁 Arquivo original: {cert.nome_arquivo_original}")
        print(f"👆 Fingerprint: {cert.fingerprint}")
        print(f"📅 Válido até: {cert.validade_fim}")
        
        # Diagnóstico do conteúdo
        print(f"\n🔍 === DIAGNÓSTICO CONTEÚDO ===")
        conteudo = cert.conteudo_certificado
        print(f"📏 Tamanho conteúdo: {len(conteudo)} caracteres")
        print(f"🔤 Primeiros 50 chars: {conteudo[:50]}")
        print(f"🔤 Últimos 50 chars: {conteudo[-50:]}")
        
        # Tentar decodificar
        print(f"\n🔓 === TESTANDO DECODIFICAÇÃO ===")
        
        # Método 1: Base64 direto
        try:
            decoded_base64 = base64.b64decode(conteudo)
            print(f"✅ Base64 OK: {len(decoded_base64)} bytes")
            
            # Verificar se é PKCS#12
            if decoded_base64[:4] == b'\x30\x82':
                print("✅ Parece ser formato PKCS#12 válido")
            else:
                print(f"⚠️ Header não reconhecido: {decoded_base64[:10].hex()}")
                
        except Exception as e:
            print(f"❌ Base64 falhou: {e}")
        
        # Diagnóstico da senha
        print(f"\n🔐 === DIAGNÓSTICO SENHA ===")
        senha = cert.senha_certificado
        print(f"📏 Tamanho senha: {len(senha)} caracteres")
        print(f"🔤 Primeiros 20 chars: {senha[:20]}")
        
        # Tentar descriptografar
        try:
            senha_desc = _decrypt_password(senha)
            print(f"✅ Descriptografia OK: {len(senha_desc)} caracteres")
            print(f"🔤 Senha descriptografada: {'*' * len(senha_desc)}")
        except Exception as e:
            print(f"❌ Descriptografia falhou: {e}")
            
            # Tentar base64 simples
            try:
                senha_base64 = base64.b64decode(senha.encode())
                print(f"✅ Base64 simples OK: {len(senha_base64)} bytes")
                senha_desc = senha_base64.decode('utf-8')
                print(f"🔤 Senha base64: {'*' * len(senha_desc)}")
            except Exception as e2:
                print(f"❌ Base64 simples também falhou: {e2}")
        
        # Teste PKCS#12 completo
        print(f"\n🧪 === TESTE PKCS#12 COMPLETO ===")
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            
            # Usar dados decodificados
            cert_data = base64.b64decode(conteudo)
            
            # Tentar várias senhas
            senhas_teste = [
                senha_desc if 'senha_desc' in locals() else None,
                senha,
                '',
                None,
                '123456',
                'password'
            ]
            
            for i, senha_teste in enumerate(senhas_teste):
                if senha_teste is None:
                    continue
                    
                print(f"🧪 Testando senha {i+1}: {type(senha_teste)}")
                
                try:
                    # Preparar senha
                    if isinstance(senha_teste, str):
                        senha_bytes = senha_teste.encode('utf-8')
                    else:
                        senha_bytes = senha_teste
                    
                    # Tentar carregar
                    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
                        cert_data, senha_bytes
                    )
                    
                    print(f"🎉 SUCESSO! Certificado carregado com senha {i+1}")
                    print(f"👤 Subject: {certificate.subject}")
                    print(f"📅 Válido até: {certificate.not_valid_after_utc}")
                    return True
                    
                except Exception as e:
                    print(f"❌ Senha {i+1} falhou: {e}")
            
            print("❌ Nenhuma senha funcionou")
            
        except Exception as e:
            print(f"❌ Erro geral no teste PKCS#12: {e}")
            
    except Exception as e:
        print(f"❌ Erro no diagnóstico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnosticar_certificado()