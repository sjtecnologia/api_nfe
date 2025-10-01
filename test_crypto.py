from services.certificate_service import _encrypt_password, _decrypt_password

def test_encryption():
    """Testa criptografia/descriptografia isoladamente"""
    print("🧪 === TESTE DE CRIPTOGRAFIA ===")
    
    senha_original = "Sj10260583"
    print(f"📝 Senha original: {senha_original}")
    
    try:
        # Criptografar
        senha_criptografada = _encrypt_password(senha_original)
        print(f"✅ Criptografia OK: {len(senha_criptografada)} chars")
        print(f"🔐 Senha criptografada: {senha_criptografada[:50]}...")
        
        # Descriptografar
        senha_descriptografada = _decrypt_password(senha_criptografada)
        print(f"✅ Descriptografia OK: {senha_descriptografada}")
        
        # Verificar se é igual
        if senha_descriptografada == senha_original:
            print("🎉 TESTE PASSOU! Criptografia funcionando")
            return True
        else:
            print("❌ TESTE FALHOU! Senhas não coincidem")
            return False
            
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_encryption()