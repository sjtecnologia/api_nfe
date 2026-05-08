#!/usr/bin/env python3
"""
Script para regenerar DANFE de NFe já emitida com protocolo correto
"""
import sys
import os

# Carregar variáveis de ambiente
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.nfe_service import NFeService
from database.connection import SessionLocal
from database.models import NFeEmitidas
from datetime import datetime

def corrigir_danfe_nfe(numero_nfe: int):
    """Regenera DANFE de uma NFe já emitida"""
    
    db = SessionLocal()
    
    try:
        # Buscar NFe no banco
        nfe = db.query(NFeEmitidas).filter(NFeEmitidas.numero == numero_nfe).first()
        
        if not nfe:
            print(f"❌ NFe {numero_nfe} não encontrada no banco")
            return False
        
        print(f"\n📄 NFe encontrada:")
        print(f"   ID: {nfe.nfe_emitida_id}")
        print(f"   Número: {nfe.numero}")
        print(f"   Chave: {nfe.chave_acesso}")
        print(f"   Protocolo: {nfe.protocolo_sefaz}")
        print(f"   Status: {nfe.status}")
        
        if nfe.status != 'AUTORIZADA':
            print(f"⚠️  NFe não está autorizada (status: {nfe.status})")
            return False
        
        # Pegar XML autorizado do JSON (xml_autorizado está no json_nfe)
        if not nfe.json_nfe:
            print("❌ JSON da NFe não encontrado")
            return False
        
        xml_para_protocolo = nfe.json_nfe.get('xml_autorizado') if isinstance(nfe.json_nfe, dict) else None
        
        if not xml_para_protocolo:
            print("❌ XML autorizado não encontrado no JSON")
            return False
        
        print(f"\n🔄 Regenerando protocolo com tpAmb correto...")
        
        # Preparar dados do resultado como se viesse da SEFAZ
        resultado_sefaz = {
            'chave_acesso': nfe.chave_acesso,
            'protocolo': nfe.protocolo_sefaz,
            'data_autorizacao': nfe.data_autorizacao.isoformat() if nfe.data_autorizacao else datetime.now().isoformat(),
            'mensagem': nfe.mensagem_sefaz or 'Autorizado o uso da NF-e',
            'status': '100',  # Código numérico
            'ambiente_real': True  # Indica que é autorização real da SEFAZ
        }
        
        # Instanciar serviço NFe
        nfe_service = NFeService()
        
        # Gerar XML com protocolo corrigido
        xml_protocolo_corrigido = nfe_service._gerar_xml_protocolo(
            xml_para_protocolo, 
            resultado_sefaz
        )
        
        print(f"✅ XML com protocolo regenerado")
        
        # Gerar novo DANFE
        print(f"\n📑 Gerando novo DANFE...")
        pdf_base64 = nfe_service._gerar_danfe(xml_protocolo_corrigido)
        
        if not pdf_base64:
            print("❌ Erro ao gerar DANFE")
            return False
        
        print(f"✅ DANFE gerado com sucesso")
        
        # Atualizar banco com XML e PDF corrigidos
        print(f"\n💾 Atualizando banco de dados...")
        
        # Atualizar json_nfe com novo xml e pdf
        if isinstance(nfe.json_nfe, dict):
            nfe.json_nfe['xml_autorizado'] = xml_protocolo_corrigido
            nfe.json_nfe['pdf_danfe'] = pdf_base64
        
        db.commit()
        
        print(f"✅ NFe {nfe.numero} atualizada com sucesso!")
        print(f"\n🎉 DANFE corrigido - agora sem tarja 'SEM VALOR FISCAL'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao corrigir DANFE: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python corrigir_danfe_nfe.py <numero_nfe>")
        print("Exemplo: python corrigir_danfe_nfe.py 1155")
        sys.exit(1)
    
    numero = int(sys.argv[1])
    sucesso = corrigir_danfe_nfe(numero)
    
    sys.exit(0 if sucesso else 1)
