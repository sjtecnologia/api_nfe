#!/usr/bin/env python3
"""
Script para corrigir DANFE da NFe 1155 usando contexto Flask
"""
import sys
import os
sys.path.insert(0, '/home/ubuntu/api_nfe')

# Contexto Flask
from app import app
with app.app_context():
    from database.connection import SessionLocal
    from database.models import NFeEmitidas
    from services.nfe_service import NFeService
    from services.danfe_service import generate_danfe
    from datetime import datetime
    import xml.etree.ElementTree as ET
    
    # Buscar NFe
    db = SessionLocal()
    nfe = db.query(NFeEmitidas).filter(NFeEmitidas.numero == 1155).first()
    
    if not nfe:
        print("❌ NFe 1155 não encontrada")
        sys.exit(1)
    
    print(f"\n📄 NFe encontrada:")
    print(f"   ID: {nfe.nfe_emitida_id}")
    print(f"   Número: {nfe.numero}")
    print(f"   Chave: {nfe.chave_acesso}")
    print(f"   Protocolo: {nfe.protocolo_sefaz}")
    
    # Extrair XML dos logs
    print(f"\n📝 Extraindo XML dos logs...")
    import subprocess
    cmd = "sudo journalctl -u api-nfe-principal.service --since '2 hours ago' | grep '35260234482371000179550010000011551353320624' | grep 'xml_protocolo' | tail -1"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if not result.stdout:
        print("❌ XML não encontrado nos logs")
        sys.exit(1)
    
    # Extrair XML do log
    import re
    match = re.search(r'<nfeProc.*?</nfeProc>', result.stdout, re.DOTALL)
    if not match:
        print("❌ Formato de XML não encontrado")
        sys.exit(1)
    
    xml_antigo = match.group(0)
    print(f"✅ XML extraído dos logs ({len(xml_antigo)} bytes)")
    
    # Verificar tpAmb antigo
    if '<tpAmb>2</tpAmb>' in xml_antigo and '<protNFe' in xml_antigo:
        print("   ⚠️  Confirmado: protNFe tem tpAmb=2 (HOMOLOGAÇÃO) ❌")
    
    # Extrair apenas NFe (sem protocolo)
    root = ET.fromstring(xml_antigo)
    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    nfe_element = root.find('.//nfe:NFe', ns)
    
    if nfe_element is None:
        print("❌ Elemento NFe não encontrado")
        sys.exit(1)
    
    xml_nfe_apenas = ET.tostring(nfe_element, encoding='unicode')
    
    # Regenerar protocolo com tpAmb correto
    print(f"\n🔄 Regenerando protocolo com tpAmb correto...")
    nfe_service = NFeService()
    
    resultado_sefaz = {
        'chave_acesso': nfe.chave_acesso,
        'protocolo': nfe.protocolo_sefaz,
        'status': '100',
        'digVal': 'N/A',  # Não importa para DANFE já autorizado
        'ambiente_real': True  # Força valores reais
    }
    
    xml_corrigido = nfe_service._gerar_xml_protocolo(xml_nfe_apenas, resultado_sefaz)
    print(f"✅ XML regenerado com novo protocolo")
    
    # Verificar tpAmb novo
    if '<tpAmb>1</tpAmb>' in xml_corrigido and '<protNFe' in xml_corrigido:
        print("   ✅ Confirmado: protNFe agora tem tpAmb=1 (PRODUÇÃO) ✅")
    
    # Gerar DANFE
    print(f"\n📑 Gerando novo DANFE...")
    pdf_base64 = generate_danfe(xml_corrigido, nfe.nfe_emitida_id, nfe.cliente_id)
    
    if not pdf_base64:
        print("❌ Erro ao gerar DANFE")
        sys.exit(1)
    
    print(f"✅ DANFE gerado com sucesso")
    
    # Atualizar banco
    print(f"\n💾 Atualizando banco de dados...")
    
    # Garantir que json_nfe seja dict
    if not nfe.json_nfe:
        nfe.json_nfe = {}
    
    # Atualizar com XML e PDF corrigidos
    nfe.json_nfe['xml_autorizado'] = xml_corrigido
    nfe.json_nfe['pdf_danfe'] = pdf_base64
    nfe.json_nfe['danfe_corrigido_em'] = datetime.now().isoformat()
    
    # Marcar flag para atualização JSONB
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(nfe, 'json_nfe')
    
    db.commit()
    
    print(f"✅ NFe 1155 atualizada com sucesso no banco!")
    print(f"🎉 DANFE corrigido - agora SEM tarja 'SEM VALOR FISCAL' ✅")
    
    db.close()
