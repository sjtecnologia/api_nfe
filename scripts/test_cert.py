import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes

# --- HARDCODE SEU CAMINHO DO CERTIFICADO E SUA SENHA AQUI ---
# COLOQUE O CAMINHO COMPLETO DO ARQUIVO PFX NO SEU COMPUTADOR
PFX_PATH = "/Users/renato/Desktop/SJ TECNOLOGIA- Sj10260583.pfx"
# COLOQUE A SENHA EXATA DO SEU CERTIFICADO AQUI, COMO UMA STRING NORMAL
PFX_PASSWORD_STR = "Sj10260583"
# --- FIM DA CONFIGURAÇÃO ---

def test_load_pfx_direct():
    print(f"Tentando carregar PFX de: {PFX_PATH}")
    print(f"Com senha (string): '{PFX_PASSWORD_STR}'")

    if not os.path.exists(PFX_PATH):
        print(f"ERRO: Arquivo PFX não encontrado no caminho: {PFX_PATH}")
        return

    try:
        # Leia o conteúdo do arquivo PFX como bytes
        with open(PFX_PATH, "rb") as f:
            pfx_data = f.read()
        
        # Encode a senha para bytes, que é o que pkcs12.load_key_and_certificates espera
        pfx_password_bytes = PFX_PASSWORD_STR.encode('utf-8')

        # Tente carregar o certificado
        print("\nTentando carregar o certificado PKCS12 usando cryptography.hazmat.primitives.serialization.pkcs12...")
        key, cert, othercerts = pkcs12.load_key_and_certificates(
            data=pfx_data,
            password=pfx_password_bytes,
            backend=default_backend()
        )
        
        print("\nSUCESSO: Certificado carregado diretamente pela biblioteca cryptography!")
        print(f"Assunto do Certificado: {cert.subject}")
        print(f"Emissor do Certificado: {cert.issuer}")
        print(f"Validade de: {cert.not_valid_before_utc} até: {cert.not_valid_after_utc}")
        print(f"Fingerprint (SHA256): {cert.fingerprint(hashes.SHA256()).hex()}")
        
    except ValueError as e:
        print(f"\nERRO: ValueError ao carregar o certificado: {e}")
        print("Isso geralmente indica problema no conteúdo do PFX ou na senha.")
    except Exception as e:
        print(f"\nERRO: Ocorreu um erro inesperado: {e}")
        
if __name__ == "__main__":
    test_load_pfx_direct()