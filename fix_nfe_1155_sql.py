#!/usr/bin/env python3
"""
Fix NFe 1155 usando SQL direto para garantir que salve
"""
import sys
import os
sys.path.insert(0, '/home/ubuntu/api_nfe')

from app import app
with app.app_context():
    from database.connection import SessionLocal
    from database.models import NFeEmitidas
    from services.nfe_service import NFeService
    from services.danfe_service import generate_danfe
    from sqlalchemy import text
    import xml.etree.ElementTree as ET
    import subprocess
    import re
    
    db = SessionLocal()
    
    try:
        # Buscar NFe
        nfe = db.query(NFeEmitidas).filter(NFeEmitidas.numero == 1155).first()
        
        if not nfe:
            print("❌ NFe 1155 não encontrada")
            sys.exit(1)
        
        print(f"\n📄 NFe {nfe.numero} - ID: {nfe.nfe_emitida_id}")
        
        # Extrair XML dos logs
        print(f"\n📝 Extraindo XML dos logs...")
        cmd = "sudo journalctl -u api-nfe-principal.service --since '3 hours ago' | grep '35260234482371000179550010000011551353320624' | grep 'xml_protocolo' | tail -1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if not result.stdout:
            print("❌ XML não encontrado nos logs")
            sys.exit(1)
        
        # Extrair XML do log
        match = re.search(r'<nfeProc.*?</nfeProc>', result.stdout, re.DOTALL)
        if not match:
            print("❌ Formato de XML inválido")
            sys.exit(1)
        
        xml_antigo = match.group(0)
        print(f"✅ XML extraído: {len(xml_antigo)} bytes")
        
        # Extrair apenas NFe (sem protocolo)
        root = ET.fromstring(xml_antigo)
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        nfe_element = root.find('.//nfe:NFe', ns)
        
        if nfe_element is None:
            print("❌ Elemento NFe não encontrado")
            sys.exit(1)
        
        xml_nfe_apenas = ET.tostring(nfe_element, encoding='unicode')
        
        # Regenerar protocolo
        print(f"\n🔄 Regenerando protocolo...")
        nfe_service = NFeService()
        
        resultado_sefaz = {
            'chave_acesso': nfe.chave_acesso,
            'protocolo': nfe.protocolo_sefaz,
            'status': '100',
            'digVal': 'N/A',
            'ambiente_real': True
        }
        
        xml_corrigido = nfe_service._gerar_xml_protocolo(xml_nfe_apenas, resultado_sefaz)
        print(f"✅ XML corrigido: {len(xml_corrigido)} bytes")
        
        # Verificar tpAmb
        has_tpamb1 = '<tpAmb>1</tpAmb>' in xml_corrigido and '<protNFe' in xml_corrigido
        print(f"   tpAmb=1 no protNFe: {'✅' if has_tpamb1 else '❌'}")
        
        if not has_tpamb1:
            print("❌ XML corrigido ainda não tem tpAmb=1!")
            sys.exit(1)
        
        # Gerar DANFE
        print(f"\n📑 Gerando DANFE...")
        pdf_base64 = generate_danfe(xml_corrigido, nfe.nfe_emitida_id, nfe.cliente_id)
        
        if not pdf_base64:
            print("❌ Erro ao gerar DANFE")
            sys.exit(1)
        
        print(f"✅ DANFE gerado: {len(pdf_base64)} bytes (base64)")
        
        # Atualizar usando SQL DIRETO para garantir que salve
        print(f"\n💾 Atualizando banco com SQL direto...")
        
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        # Usar jsonb_set do PostgreSQL
        update_sql = text("""
            UPDATE nfe_emitidas 
            SET json_nfe = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        COALESCE(json_nfe, '{}'::jsonb),
                        '{xml_autorizado}',
                        to_jsonb(:xml_corrigido::text)
                    ),
                    '{pdf_danfe}',
                    to_jsonb(:pdf_base64::text)
                ),
                '{danfe_corrigido_em}',
                to_jsonb(:timestamp::text)
            )
            WHERE nfe_emitida_id = :nfe_id
        """)
        
        db.execute(update_sql, {
            'xml_corrigido': xml_corrigido,
            'pdf_base64': pdf_base64,
            'timestamp': timestamp,
            'nfe_id': nfe.nfe_emitida_id
        })
        
        db.commit()
        print(f"✅ Banco atualizado com SQL direto")
        
        # Verificar se salvou
        print(f"\n🔍 Verificando se salvou...")
        verify_sql = text("""
            SELECT 
                json_nfe->>'xml_autorizado' IS NOT NULL as tem_xml_autorizado,
                length(json_nfe->>'xml_autorizado') as tamanho_xml,
                json_nfe->>'xml_autorizado' LIKE '%<tpAmb>1</tpAmb>%' as tem_tpamb1
            FROM nfe_emitidas
            WHERE nfe_emitida_id = :nfe_id
        """)
        
        result = db.execute(verify_sql, {'nfe_id': nfe.nfe_emitida_id}).fetchone()
        
        if result:
            print(f"   Tem xml_autorizado: {result[0]}")
            print(f"   Tamanho: {result[1]} bytes")
            print(f"   Tem tpAmb=1: {result[2]}")
            
            if result[0] and result[2]:
                print(f"\n🎉 Sucesso! DANFE agora está SEM tarja")
            else:
                print(f"\n❌ Problema ao salvar no banco")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
