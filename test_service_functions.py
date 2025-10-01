from services.certificate_service import _encrypt_password, _decrypt_password

def test_service_functions():
    """Testa apenas as funções do service"""
    print("🔧 === TESTANDO FUNÇÕES DO SERVICE ===")
    
    senha_original = "Sj10260583"
    print(f"📝 Senha original: '{senha_original}'")
    
    try:
        # Criptografar
        print("\n📤 TESTANDO _encrypt_password...")
        service_encrypted = _encrypt_password(senha_original)
        print(f"✅ Criptografada: {service_encrypted[:50]}...")
        print(f"✅ Tamanho: {len(service_encrypted)} chars")
        
        # Descriptografar
        print("\n📥 TESTANDO _decrypt_password...")
        service_decrypted = _decrypt_password(service_encrypted)
        print(f"✅ Descriptografada: '{service_decrypted}'")
        
        # Verificar
        if service_decrypted == senha_original:
            print("🎉 SERVICE FUNCTIONS OK!")
            return True
        else:
            print(f"❌ SERVICE FUNCTIONS FAILED!")
            print(f"❌ Esperado: '{senha_original}'")
            print(f"❌ Recebido: '{service_decrypted}'")
            return False
            
    except Exception as e:
        print(f"❌ Erro nas funções do service: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_service_functions()