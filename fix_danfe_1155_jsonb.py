#!/usr/bin/env python3
"""
Corrigir DANFE NFe 1155 usando UPDATE SQL direto no JSONB
"""
import sys
import os
sys.path.insert(0, '/home/ubuntu/api_nfe')

from app import app
with app.app_context():
    from database.connection import get_db
    from services.nfe_service import NFeService
    from services.danfe_service import generate_danfe
    from sqlalchemy import text
    import xml.etree.ElementTree as ET
    import subprocess
    import re
    
    db = next(get_db())
    
    try:
        print("\n📄 Buscando NFe 1155...")
        
        # Buscar NFe pelo número
        query = text("SELECT nfe_emitida_id, numero, chave_acesso, protocolo_autorizacao, cliente_id FROM nfe_emitidas WHERE numero = 1155")
        nfe = db.execute(query).fetchone()
        
        if not nfe:
            print("❌ NFe 1155 não encontrada")
            sys.exit(1)
        
        nfe_id = nfe[0]
        numero = nfe[1]
        chave = nfe[2]
        protocolo = nfe[3]
        cliente_id = nfe[4]
        
        print(f"✅ NFe encontrada - ID: {nfe_id}, Número: {numero}")
        
        # Extrair XML dos logs
        print(f"\n📝 Extraindo XML dos logs...")
        cmd = f"sudo journalctl -u api-nfe-principal.service --since '4 hours ago' | grep '{chave}' | grep 'xml_protocolo' | tail -1"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if not result.stdout:
            print("❌ XML não encontrado nos logs")
            sys.exit(1)
        
        # Extrair XML
        match = re.search(r'<nfeProc.*?</nfeProc>', result.stdout, re.DOTALL)
        if not match:
            print("❌ Formato de XML inválido")
            sys.exit(1)
        
        xml_antigo = match.group(0)
        print(f"✅ XML extraído: {len(xml_antigo)} bytes")
        
        # Extrair apenas NFe
        root = ET.fromstring(xml_antigo)
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        nfe_element = root.find('.//nfe:NFe', ns)
        
        if nfe_element is None:
            print("❌ Elemento NFe não encontrado")
            sys.exit(1)
        
        xml_nfe_apenas = ET.tostring(nfe_element, encoding='unicode')
        
        # Regenerar protocolo com tpAmb=1
        print(f"\n🔄 Regenerando protocolo com tpAmb=1...")
        nfe_service = NFeService()
        
        resultado_sefaz = {
            'chave_acesso': chave,
            'protocolo': protocolo,
            'status': '100',
            'digVal': 'N/A',
            'ambiente_real': True
        }
        
        xml_corrigido = nfe_service._gerar_xml_protocolo(xml_nfe_apenas, resultado_sefaz)
        
        # Verificar tpAmb
        has_tpamb1 = '<tpAmb>1</tpAmb>' in xml_corrigido and '<protNFe' in xml_corrigido
        print(f"   tpAmb=1 no protNFe: {'✅' if has_tpamb1 else '❌'}")
        
        if not has_tpamb1:
            print("❌ XML corrigido não tem tpAmb=1!")
            sys.exit(1)
        
        # Gerar DANFE
        print(f"\n📑 Gerando DANFE...")
        pdf_base64 = generate_danfe(xml_corrigido, nfe_id, cliente_id)
        
        if not pdf_base64:
            print("❌ Erro ao gerar DANFE")
            sys.exit(1)
        
        print(f"✅ DANFE gerado: {len(pdf_base64)} bytes (base64)")
        
        # Atualizar usando SQL puro do PostgreSQL
        print(f"\n💾 Atualizando banco com SQL puro...")
        
        from datetime import datetime
        timestamp = datetime.now().isoformat()
        
        # Usar jsonb_set do PostgreSQL para atualizar dentro do JSONB
        update_sql = text("""
            UPDATE nfe_emitidas 
            SET json_nfe = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        COALESCE(json_nfe, '{}'::jsonb),
                        '{xml_autorizado}',
                        to_jsonb(:xml_corrigido::text),
                        true
                    ),
                    '{pdf_danfe}',
                    to_jsonb(:pdf_base64::text),
                    true
                ),
                '{danfe_corrigido_em}',
                to_jsonb(:timestamp::text),
                true
            )
            WHERE nfe_emitida_id = :nfe_id
        """)
        
        db.execute(update_sql, {
            'xml_corrigido': xml_corrigido,
            'pdf_base64': pdf_base64,
            'timestamp': timestamp,
            'nfe_id': nfe_id
        })
        
        db.commit()
        print(f"✅ SQL executado com sucesso")
        
        # Verificar se salvou
        print(f"\n🔍 Verificando se salvou no banco...")
        verify_sql = text("""
            SELECT 
                json_nfe ? 'xml_autorizado' as tem_chave,
                length(json_nfe->>'xml_autorizado') as tamanho,
                (json_nfe->>'xml_autorizado' LIKE '%<tpAmb>1</tpAmb>%') as tem_tpamb1,
                (json_nfe->>'xml_autorizado' LIKE '%<protNFe%') as tem_protnfe
            FROM nfe_emitidas
            WHERE nfe_emitida_id = :nfe_id
        """)
        
        result = db.execute(verify_sql, {'nfe_id': nfe_id}).fetchone()
        
        if result:
            print(f"   Tem chave xml_autorizado no JSONB: {result[0]}")
            print(f"   Tamanho do XML: {result[1]} bytes")
            print(f"   Tem tpAmb=1: {result[2]}")
            print(f"   Tem protNFe: {result[3]}")
            
            if result[0] and result[2] and result[3]:
                print(f"\n🎉 Sucesso! xml_autorizado salvo no JSONB com tpAmb=1")
                print(f"✅ DANFE agora está SEM tarja 'SEM VALOR FISCAL'")
            else:
                print(f"\n❌ Problema: XML não foi salvo corretamente")
        else:
            print(f"\n❌ Erro ao verificar")
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()
