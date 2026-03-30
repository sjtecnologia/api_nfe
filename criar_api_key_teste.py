#!/usr/bin/env python3
"""
Criar API Key temporária para teste - Cliente 13
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Cliente, ApiKey
from datetime import datetime
import secrets
import hashlib
import json

def gerar_api_key():
    """Gera uma API key segura"""
    return f"pk_{secrets.token_urlsafe(32)}"

def hash_api_key(api_key):
    """Gera hash da API key"""
    return hashlib.sha256(api_key.encode()).hexdigest()

def main():
    print("\n" + "="*80)
    print("🔑 CRIANDO API KEY TEMPORÁRIA PARA TESTE - CLIENTE 13")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        cliente = db.query(Cliente).filter(Cliente.cliente_id == 13).first()
        if not cliente:
            print("❌ Cliente 13 não encontrado!")
            return None
        
        print(f"✅ Cliente: {cliente.razao_social}")
        print(f"   CNPJ: {cliente.cnpj}\n")
        
        # Gerar nova key
        api_key = gerar_api_key()
        prefix = api_key[:10]
        
        nova_key = ApiKey(
            cliente_id=13,
            key_hash=hash_api_key(api_key),
            key_prefix=prefix,
            nome="API Key TESTE - Email Automático",
            permissoes=json.dumps(["nfe.write", "nfe.emit", "nfe.read"]),
            ativa=True,
            criada_em=datetime.now(),
            rate_limit=1000
        )
        
        db.add(nova_key)
        db.commit()
        
        print(f"✅ API Key criada com sucesso!")
        print(f"\n" + "="*80)
        print(f"🔑 API KEY COMPLETA (copie para usar no teste):")
        print(f"="*80)
        print(f"\n{api_key}\n")
        print(f"="*80)
        print(f"\n   ID: {nova_key.api_key_id}")
        print(f"   Prefix: {prefix}")
        print(f"   ⚠️  Esta chave é temporária para teste")
        
        # Salvar em arquivo temporário
        with open('/tmp/api_key_teste_cliente13.txt', 'w') as f:
            f.write(api_key)
        
        print(f"\n💾 Chave salva em: /tmp/api_key_teste_cliente13.txt")
        
        return api_key
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

if __name__ == '__main__':
    key = main()
    if key:
        print(f"\n✅ Use esta chave para executar o teste:")
        print(f"   python3 test_emissao_api_cliente13.py")
