#!/usr/bin/env python3
"""
Enviar email de teste para verificar layout
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import Cliente, NFeEmitidas, DestinatarioNFe
from services.email_service import enviar_nfe_automaticamente
from datetime import datetime

def enviar_email_teste():
    """
    Envia email de teste usando NFe existente
    """
    print("\n" + "="*80)
    print("📧 ENVIANDO EMAIL DE TESTE - VERIFICAÇÃO DE LAYOUT")
    print("="*80 + "\n")
    
    db = SessionLocal()
    
    try:
        # 1. Buscar cliente 13
        cliente = db.query(Cliente).filter(Cliente.cliente_id == 13).first()
        print(f"✅ Cliente: {cliente.razao_social}")
        print(f"   CNPJ: {cliente.cnpj}\n")
        
        # 2. Buscar destinatário com email
        dest_cnpj = "11562880000106"
        destinatario = db.query(DestinatarioNFe).filter(
            DestinatarioNFe.cpf_cnpj == dest_cnpj
        ).first()
        
        if destinatario and not destinatario.email:
            destinatario.email = "contato@emitemax.com.br"
            db.commit()
            print(f"📝 Email atualizado: contato@emitemax.com.br\n")
        
        # 3. Buscar NFe autorizada
        nfe = db.query(NFeEmitidas).filter(
            NFeEmitidas.cliente_id == 13,
            NFeEmitidas.status == 'AUTORIZADA'
        ).first()
        
        if not nfe:
            print("❌ Nenhuma NFe autorizada encontrada")
            return False
        
        # Atualizar destinatário da NFe
        nfe.destinatario_cnpj_cpf = dest_cnpj
        db.commit()
        
        print(f"✅ NFe selecionada:")
        print(f"   ID: {nfe.nfe_emitida_id}")
        print(f"   Número: {nfe.numero}")
        print(f"   Status: {nfe.status}")
        print(f"   Valor: R$ {nfe.valor_total}")
        if nfe.chave_acesso:
            print(f"   Chave: {nfe.chave_acesso}")
        
        # 4. Enviar email
        print(f"\n📧 ENVIANDO EMAIL PARA: contato@emitemax.com.br")
        print("="*80 + "\n")
        
        resultado = enviar_nfe_automaticamente(nfe.nfe_emitida_id, db)
        
        print("\n" + "="*80)
        print("📊 RESULTADO:")
        print("="*80 + "\n")
        
        if resultado.get('success'):
            print(f"✅ EMAIL ENVIADO COM SUCESSO!")
            print(f"   📧 Destinatário: {resultado.get('email')}")
            print(f"   📄 NFe #: {nfe.numero}")
            print(f"\n🎉 Verifique sua caixa de entrada em: contato@emitemax.com.br")
            print(f"   • Verifique o layout do email")
            print(f"   • Confira a logo EmiteMax")
            print(f"   • Verifique os anexos (XML e DANFE)")
            print(f"   • Teste a visualização em diferentes clientes de email")
            return True
        else:
            print(f"❌ FALHA NO ENVIO")
            print(f"   Motivo: {resultado.get('message')}")
            if 'errors' in resultado:
                for erro in resultado['errors']:
                    print(f"   • {erro}")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == '__main__':
    print("\n" + "📧 "*20)
    print("TESTE DE LAYOUT DE EMAIL - EMITEMAX")
    print("📧 "*20 + "\n")
    
    print("⚠️  Este email será enviado para: contato@emitemax.com.br")
    print("   Com template profissional EmiteMax + anexos (XML e DANFE)\n")
    
    # Aceitar confirmação automática via argumento
    if len(sys.argv) > 1 and sys.argv[1].lower() in ['sim', 's', '--auto']:
        confirma = 's'
        print("   → Enviando automaticamente...\n")
    else:
        confirma = input("❓ Deseja enviar o email de teste? (s/N): ").strip().lower()
    
    if confirma != 's':
        print("\n❌ Teste cancelado")
        sys.exit(0)
    
    sucesso = enviar_email_teste()
    
    if sucesso:
        print("\n" + "🎉 "*20)
        print("EMAIL ENVIADO COM SUCESSO!")
        print("🎉 "*20 + "\n")
    else:
        print("\n❌ Falha no envio. Verifique os logs acima.\n")
