#!/usr/bin/env python3
"""
Verificar ou criar API Key para cliente 13
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
    print("🔑 VERIFICANDO API KEY DO CLIENTE 13")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        cliente = db.query(Cliente).filter(Cliente.cliente_id == 13).first()
        if not cliente:
            print("❌ Cliente 13 não encontrado!")
            return
        
        print(f"✅ Cliente: {cliente.razao_social}")
        print(f"   CNPJ: {cliente.cnpj}")
        
        # Buscar API Keys ativas
        api_keys = db.query(ApiKey).filter(
            ApiKey.cliente_id == 13,
            ApiKey.ativa == True
        ).all()
        
        if api_keys:
            print(f"\n📋 {len(api_keys)} API Key(s) ativa(s):")
            for key in api_keys:
                perms = json.loads(key.permissoes) if key.permissoes else []
                print(f"\n   🔑 ID: {key.api_key_id}")
                print(f"      Prefix: {key.key_prefix}")
                print(f"      Nome: {key.nome}")
                print(f"      Criada em: {key.criada_em}")
                print(f"      Permissões: {', '.join(perms)}")
        else:
            print("\n⚠️ Nenhuma API Key encontrada!")
            print("\n📝 Criando nova API Key...")
            
            # Gerar key
            api_key = gerar_api_key()
            prefix = api_key[:10]  # pk_xxxxxx
            
            nova_key = ApiKey(
                cliente_id=13,
                key_hash=hash_api_key(api_key),
                key_prefix=prefix,
                nome="API Key de teste - Tributação Automática",
                permissoes=json.dumps(["nfe.write", "nfe.emit", "nfe.read"]),
                ativa=True,
                criada_em=datetime.now(),
                rate_limit=1000
            )
            
            db.add(nova_key)
            db.commit()
            
            print(f"✅ API Key criada com sucesso!")
            print(f"\n   🔑 API Key: {api_key}")
            print(f"      ID: {nova_key.api_key_id}")
            print(f"\n   ⚠️  GUARDE ESSA KEY! Ela não será mostrada novamente.")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    main()
