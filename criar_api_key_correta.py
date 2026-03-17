#!/usr/bin/env python3
"""
Criar API Key correta (formato emx_live_) para Cliente 13
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Cliente, ApiKey
from auth.api_key_auth import generate_api_key
from datetime import datetime
import json

def main():
    print("\n" + "="*80)
    print("🔑 CRIANDO API KEY CORRETA - CLIENTE 13")
    print("   Formato: emx_live_xxxxx")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        cliente = db.query(Cliente).filter(Cliente.cliente_id == 13).first()
        if not cliente:
            print("❌ Cliente 13 não encontrado!")
            return None
        
        print(f"✅ Cliente: {cliente.razao_social}")
        print(f"   CNPJ: {cliente.cnpj}\n")
        
        # Gerar chave usando a função oficial do sistema
        key_string, key_hash, key_prefix = generate_api_key(
            cliente_id=13,
            nome="API Key TESTE - Emissão com Email"
        )
        
        print(f"📝 Gerando chave no formato correto...")
        
        # Criar objeto ApiKey
        nova_key = ApiKey(
            cliente_id=13,
            key_hash=key_hash,
            key_prefix=key_prefix,
            nome="API Key TESTE - Emissão com Email Automático",
            permissoes=json.dumps([
                "nfe.write",
                "nfe.emit", 
                "nfe.read",
                "nfe.cancel"
            ]),
            ativa=True,
            criada_em=datetime.now(),
            rate_limit=1000,  # 1000 requests/hora
            ip_whitelist=None  # Sem restrição de IP para teste
        )
        
        db.add(nova_key)
        db.commit()
        
        print(f"✅ API Key criada com sucesso!\n")
        print("="*80)
        print("🔑 API KEY COMPLETA (copie para usar no teste):")
        print("="*80)
        print(f"\n{key_string}\n")
        print("="*80)
        print(f"\n📋 Detalhes:")
        print(f"   ID: {nova_key.api_key_id}")
        print(f"   Prefix: {key_prefix}")
        print(f"   Rate Limit: {nova_key.rate_limit} req/hora")
        print(f"   IP Whitelist: Desabilitado (todos IPs permitidos)")
        print(f"   Permissões: {', '.join(json.loads(nova_key.permissoes))}")
        
        # Salvar em arquivo temporário
        with open('/tmp/api_key_teste_cliente13.txt', 'w') as f:
            f.write(key_string)
        
        print(f"\n💾 Chave salva em: /tmp/api_key_teste_cliente13.txt")
        print(f"\n🚀 Execute o teste:")
        print(f"   python3 test_emissao_api_cliente13.py")
        
        return key_string
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == '__main__':
    key = main()
    if key:
        print(f"\n✅ Tudo pronto! A chave está no formato correto: emx_live_...")
