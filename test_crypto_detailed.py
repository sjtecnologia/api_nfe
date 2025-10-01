from services.certificate_service import _encrypt_password, _decrypt_password, _get_encryption_key
from cryptography.fernet import Fernet
import base64

def test_detailed_crypto():
    """Teste detalhado da criptografia"""
    print("🧪 === TESTE DETALHADO DE CRIPTOGRAFIA ===")
    
    senha_original = "Sj10260583"
    print(f"📝 Senha original: '{senha_original}'")
    
    # 1. Testar chave
    try:
        key = _get_encryption_key()
        print(f"🔑 Chave gerada: {key[:20]}...")
        f = Fernet(key)
        print("✅ Fernet inicializado com sucesso")
    except Exception as e:
        print(f"❌ Erro na chave: {e}")
        return
    
    # 2. Criptografar passo a passo
    try:
        print("\n🔐 === CRIPTOGRAFIA PASSO A PASSO ===")
        
        # Passo 1: String para bytes
        senha_bytes = senha_original.encode('utf-8')
        print(f"1️⃣ String → bytes: {senha_bytes}")
        
        # Passo 2: Criptografar com Fernet
        encrypted_bytes = f.encrypt(senha_bytes)
        print(f"2️⃣ Fernet encrypt: {encrypted_bytes[:30]}... ({len(encrypted_bytes)} bytes)")
        
        # Passo 3: Base64 para string
        encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        print(f"3️⃣ Base64 encode: {encrypted_b64[:50]}... ({len(encrypted_b64)} chars)")
        
        print(f"\n✅ RESULTADO FINAL CRIPTOGRAFIA: {encrypted_b64}")
        
    except Exception as e:
        print(f"❌ Erro na criptografia: {e}")
        return
    
    # 3. Descriptografar passo a passo
    try:
        print("\n🔓 === DESCRIPTOGRAFIA PASSO A PASSO ===")
        
        # Passo 1: Base64 para bytes
        decoded_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
        print(f"1️⃣ Base64 decode: {decoded_bytes[:30]}... ({len(decoded_bytes)} bytes)")
        
        # Passo 2: Descriptografar com Fernet
        decrypted_bytes = f.decrypt(decoded_bytes)
        print(f"2️⃣ Fernet decrypt: {decrypted_bytes}")
        
        # Passo 3: Bytes para string
        decrypted_str = decrypted_bytes.decode('utf-8')
        print(f"3️⃣ Bytes → string: '{decrypted_str}'")
        
        print(f"\n✅ RESULTADO FINAL DESCRIPTOGRAFIA: '{decrypted_str}'")
        
        # Verificar se é igual
        if decrypted_str == senha_original:
            print("🎉 TESTE PASSOU! Criptografia/descriptografia funcionando!")
            return True
        else:
            print(f"❌ TESTE FALHOU! '{decrypted_str}' != '{senha_original}'")
            return False
            
    except Exception as e:
        print(f"❌ Erro na descriptografia: {e}")
        return False
    
    # 4. Testar funções do service
    try:
        print("\n🔧 === TESTANDO FUNÇÕES DO SERVICE ===")
        
        service_encrypted = _encrypt_password(senha_original)
        print(f"📤 Service encrypt: {service_encrypted[:50]}...")
        
        service_decrypted = _decrypt_password(service_encrypted)
        print(f"📥 Service decrypt: '{service_decrypted}'")
        
        if service_decrypted == senha_original:
            print("🎉 SERVICE FUNCTIONS OK!")
            return True
        else:
            print(f"❌ SERVICE FUNCTIONS FAILED!")
            return False
            
    except Exception as e:
        print(f"❌ Erro nas funções do service: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_detailed_crypto()