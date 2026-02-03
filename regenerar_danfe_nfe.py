#!/usr/bin/env python3
"""
Script para regenerar DANFE consultando XML completo da SEFAZ
"""
import sys
import os
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.nfe_service import NFeService
from services.sefaz_service import SefazService
from database.connection import SessionLocal
from database.models import NFeEmitidas
from datetime import datetime

def regenerar_danfe_nfe(numero_nfe: int):
    """Regenera DANFE consultando XML completo da SEFAZ"""
    
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
        
        print(f"\n🔍 Consultando XML na SEFAZ...")
        
        # Determinar ambiente - se foi autorizada com protocolo real, é produção
        # A chave não contém tpAmb, mas NFes autorizadas geralmente são produção
        ambiente_nfe = 'producao'
        
        # Tentar pegar do JSON se existir
        if nfe.json_nfe and isinstance(nfe.json_nfe, dict):
            ambiente_json = nfe.json_nfe.get('ambiente', 'producao')
            if ambiente_json in ['homologacao', 'producao']:
                ambiente_nfe = ambiente_json
        
        print(f"   Ambiente: {ambiente_nfe}")
        
        # Buscar certificado do cliente
        from database.models import CertificadoDigital
        certificado = db.query(CertificadoDigital).filter(
            CertificadoDigital.cliente_id == nfe.cliente_id
        ).first()
        
        if not certificado:
            print(f"❌ Certificado digital não encontrado para o cliente")
            return False
        
        # Instanciar serviço SEFAZ com ambiente correto
        sefaz_service = SefazService(
            ambiente=ambiente_nfe,
            cert_path=certificado.caminho_certificado if hasattr(certificado, 'caminho_certificado') else None,
            key_path=certificado.caminho_chave if hasattr(certificado, 'caminho_chave') else None
        )
        
        # Consultar NFe na SEFAZ usando a chave de acesso
        resultado_consulta = sefaz_service.consultar_nfe(nfe.chave_acesso)
        
        if not resultado_consulta.get('success'):
            print(f"❌ Erro ao consultar SEFAZ: {resultado_consulta.get('message')}")
            return False
        
        print(f"✅ XML recuperado da SEFAZ")
        
        # O XML completo com protocolo vem em 'xml_completo' ou 'xml_protocolo'
        xml_completo = resultado_consulta.get('xml_completo') or resultado_consulta.get('xml_protocolo')
        
        if not xml_completo:
            print(f"❌ XML completo não encontrado na resposta da SEFAZ")
            print(f"   Chaves disponíveis: {list(resultado_consulta.keys())}")
            return False
        
        print(f"\n📑 Gerando novo DANFE com XML atualizado...")
        
        # Instanciar serviço NFe
        nfe_service = NFeService()
        
        # Gerar DANFE a partir do XML completo da SEFAZ
        pdf_base64 = nfe_service._gerar_danfe(xml_completo)
        
        if not pdf_base64:
            print("❌ Erro ao gerar DANFE")
            return False
        
        print(f"✅ DANFE gerado com sucesso")
        
        # Atualizar banco com XML e PDF corrigidos
        print(f"\n💾 Atualizando banco de dados...")
        
        # Atualizar json_nfe
        if not nfe.json_nfe:
            nfe.json_nfe = {}
        
        if isinstance(nfe.json_nfe, dict):
            nfe.json_nfe['xml_autorizado'] = xml_completo
            nfe.json_nfe['pdf_danfe'] = pdf_base64
            nfe.json_nfe['danfe_regenerado_em'] = datetime.now().isoformat()
        
        db.commit()
        
        print(f"✅ NFe {nfe.numero} atualizada com sucesso!")
        print(f"\n🎉 DANFE regenerado da SEFAZ - agora sem tarja 'SEM VALOR FISCAL'")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao regenerar DANFE: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python regenerar_danfe_nfe.py <numero_nfe>")
        print("Exemplo: python regenerar_danfe_nfe.py 1155")
        sys.exit(1)
    
    numero = int(sys.argv[1])
    sucesso = regenerar_danfe_nfe(numero)
    
    sys.exit(0 if sucesso else 1)
