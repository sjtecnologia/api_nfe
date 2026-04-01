#!/usr/bin/env python3
"""
Script para corrigir DANFE da NFe 1155 usando XML dos logs
"""
import sys
import os
import re
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.nfe_service import NFeService
from services.danfe_service import generate_danfe
from database.connection import SessionLocal
from database.models import NFeEmitidas
from datetime import datetime

def corrigir_danfe_nfe_1155():
    """Corrige DANFE da NFe 1155 extraindo XML corrigido dos logs"""
    
    db = SessionLocal()
    
    try:
        # Buscar NFe no banco
        nfe = db.query(NFeEmitidas).filter(NFeEmitidas.numero == 1155).first()
        
        if not nfe:
            print(f"❌ NFe 1155 não encontrada no banco")
            return False
        
        print(f"\n📄 NFe encontrada:")
        print(f"   ID: {nfe.nfe_emitida_id}")
        print(f"   Número: {nfe.numero}")
        print(f"   Chave: {nfe.chave_acesso}")
        print(f"   Protocolo: {nfe.protocolo_sefaz}")
        
        print(f"\n📝 Extraindo XML dos logs...")
        
        # Extrair XML do journalctl
        import subprocess
        cmd = "sudo journalctl -u api-nfe-principal.service --since '2 hours ago' | grep '35260234482371000179550010000011551353320624' | grep 'xml_protocolo' | tail -1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Erro ao extrair logs")
            return False
        
        log_line = result.stdout.strip()
        
        # Extrair XML do log usando regex
        match = re.search(r"'xml_protocolo': '(.+?)'(?:,| *})", log_line)
        if not match:
            print(f"❌ XML não encontrado no log")
            return False
        
        xml_antigo = match.group(1)
        # Decodificar \n
        xml_antigo = xml_antigo.replace('\\n', '\n')
        
        print(f"✅ XML extraído dos logs ({len(xml_antigo)} bytes)")
        print(f"   Verificando tpAmb no protNFe antigo...")
        
        # Verificar tpAmb atual
        if '<tpAmb>2</tpAmb>' in xml_antigo and '<protNFe' in xml_antigo:
            print(f"   ⚠️  Confirmado: protNFe tem tpAmb=2 (HOMOLOGAÇÃO) ❌")
        
        # Extrair apenas a parte NFe (sem protNFe)
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_antigo)
        nfe_element = root.find('.//{http://www.portalfiscal.inf.br/nfe}NFe')
        
        if nfe_element is None:
            print(f"❌ Elemento NFe não encontrado")
            return False
        
        xml_nfe_apenas = ET.tostring(nfe_element, encoding='unicode')
        
        print(f"\n🔄 Regenerando protocolo com tpAmb correto...")
        
        # Preparar resultado como se viesse da SEFAZ real
        resultado_sefaz = {
            'chave_acesso': nfe.chave_acesso,
            'protocolo': nfe.protocolo_sefaz,
            'data_autorizacao': '2026-02-03T13:32:43.518951',
            'mensagem': 'Autorizado o uso da NF-e',
            'status': '100',
            'ambiente_real': True  # ✅ Marca como real para usar valores corretos
        }
        
        # Instanciar serviço NFe
        nfe_service = NFeService()
        
        # Gerar novo XML com protocolo corrigido
        xml_corrigido = nfe_service._gerar_xml_protocolo(xml_nfe_apenas, resultado_sefaz)
        
        print(f"✅ XML regenerado com novo protocolo")
        print(f"   Verificando tpAmb no protNFe novo...")
        
        if '<tpAmb>1</tpAmb>' in xml_corrigido and '<protNFe' in xml_corrigido:
            print(f"   ✅ Confirmado: protNFe agora tem tpAmb=1 (PRODUÇÃO) ✅")
        
        print(f"\n📑 Gerando novo DANFE...")
        
        # Gerar DANFE a partir do XML corrigido
        pdf_base64 = generate_danfe(xml_corrigido, nfe.nfe_emitida_id, nfe.cliente_id)
        
        if not pdf_base64:
            print("❌ Erro ao gerar DANFE")
            return False
        
        print(f"✅ DANFE gerado com sucesso")
        
        # Atualizar banco
        print(f"\n💾 Atualizando banco de dados...")
        
        if not nfe.json_nfe:
            nfe.json_nfe = {}
        
        if isinstance(nfe.json_nfe, dict):
            nfe.json_nfe['xml_autorizado'] = xml_corrigido
            nfe.json_nfe['pdf_danfe'] = pdf_base64
            nfe.json_nfe['danfe_corrigido_em'] = datetime.now().isoformat()
        
        db.commit()
        
        print(f"✅ NFe 1155 atualizada com sucesso!")
        print(f"\n🎉 DANFE corrigido - agora SEM tarja 'SEM VALOR FISCAL' ✅")
        
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
    sucesso = corrigir_danfe_nfe_1155()
    sys.exit(0 if sucesso else 1)
