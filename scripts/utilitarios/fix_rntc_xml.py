"""
Script para remover o campo <RNTC> dos XMLs de NFe já salvos no banco de dados.

O campo RNTC não é reconhecido pelo nfelib 2.2.0, causando erro ao gerar DANFE.
Este script move o valor de RNTC para o campo <infAdic><infCpl> e remove a tag <RNTC>.

Uso:
    python fix_rntc_xml.py
"""

import sys
import re
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from lxml import etree

# Importar configurações do banco
sys.path.append('.')
from database.connection import get_db

def fix_rntc_in_xml(xml_str: str) -> tuple[str, bool]:
    """
    Remove o campo <RNTC> do XML e move o valor para <infAdic><infCpl>.
    
    Args:
        xml_str: XML da NFe como string
        
    Returns:
        Tupla (xml_corrigido, foi_modificado)
    """
    if '<RNTC>' not in xml_str:
        return xml_str, False
    
    try:
        # Parse do XML
        root = etree.fromstring(xml_str.encode('utf-8'))
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Buscar o elemento RNTC
        rntc_elem = root.find('.//nfe:transp/nfe:RNTC', ns)
        if rntc_elem is None:
            return xml_str, False
        
        rntc_value = rntc_elem.text
        
        # Remover o elemento RNTC
        transp_elem = root.find('.//nfe:transp', ns)
        if transp_elem is not None:
            transp_elem.remove(rntc_elem)
        
        # Adicionar ao infAdic
        inf_adic = root.find('.//nfe:infAdic', ns)
        if inf_adic is None:
            # Criar infAdic se não existir
            inf_nfe = root.find('.//nfe:infNFe', ns)
            inf_adic = etree.SubElement(inf_nfe, '{http://www.portalfiscal.inf.br/nfe}infAdic')
        
        # Buscar ou criar infCpl
        inf_cpl = inf_adic.find('nfe:infCpl', ns)
        antt_info = f"RNTC/ANTT da Transportadora: {rntc_value}"
        
        if inf_cpl is None:
            # Criar novo infCpl
            inf_cpl = etree.SubElement(inf_adic, '{http://www.portalfiscal.inf.br/nfe}infCpl')
            inf_cpl.text = antt_info
        else:
            # Adicionar ao infCpl existente
            if inf_cpl.text:
                inf_cpl.text = f"{inf_cpl.text}. {antt_info}"
            else:
                inf_cpl.text = antt_info
        
        # Converter de volta para string
        xml_fixed = etree.tostring(root, encoding='unicode', pretty_print=True)
        
        return xml_fixed, True
        
    except Exception as e:
        print(f"[X] Erro ao processar XML: {e}")
        return xml_str, False


def main():
    """
    Função principal para corrigir os XMLs no banco de dados.
    """
    print("\n" + "="*80)
    print("[?] CORREÇÃO DE XMLs - Remover campo <RNTC>")
    print("="*80 + "\n")
    
    try:
        # Conectar ao banco
        db = next(get_db())
        
        # Buscar NFes com RNTC no XML (armazenado em json_nfe->xml_content)
        query = text("""
            SELECT nfe_emitida_id, chave_acesso, json_nfe
            FROM nfe_emitidas
            WHERE json_nfe::text LIKE '%<RNTC>%'
            ORDER BY nfe_emitida_id DESC
        """)
        
        result = db.execute(query)
        nfes = result.fetchall()
        
        if not nfes:
            print("[OK] Nenhuma NFe com campo <RNTC> encontrada. Banco já está correto.")
            return
        
        print(f"[LIST] Encontradas {len(nfes)} NFe(s) com campo <RNTC> para corrigir:\n")
        
        for nfe in nfes:
            nfe_id = nfe.nfe_emitida_id
            chave = nfe.chave_acesso
            json_nfe = nfe.json_nfe
            
            print(f"[SEARCH] NFe ID {nfe_id} - Chave: {chave[:20] if chave else 'N/A'}...")
            
            # Extrair xml_content do JSON
            import json
            if isinstance(json_nfe, str):
                json_data = json.loads(json_nfe)
            else:
                json_data = json_nfe
            
            xml_content = json_data.get('xml_content', '')
            
            if not xml_content or '<RNTC>' not in xml_content:
                print(f"  ℹ️ NFe {nfe_id} não contém campo RNTC")
                print()
                continue
            
            # Corrigir o XML
            xml_fixed, modificado = fix_rntc_in_xml(xml_content)
            
            if modificado:
                print(f"  [OK] XML corrigido (RNTC removido e movido para infAdic)")
                
                # Atualizar o JSON com o XML corrigido
                json_data['xml_content'] = xml_fixed
                
                # Atualizar no banco
                update_query = text("""
                    UPDATE nfe_emitidas
                    SET json_nfe = :json_nfe
                    WHERE nfe_emitida_id = :nfe_id
                """)
                
                db.execute(update_query, {
                    'nfe_id': nfe_id,
                    'json_nfe': json.dumps(json_data)
                })
                
                print(f"  [SAVE] NFe {nfe_id} atualizada no banco")
            else:
                print(f"  [!] NFe {nfe_id} não foi modificada")
            
            print()
        
        # Commit
        db.commit()
        
        print("="*80)
        print(f"[OK] CONCLUÍDO! {len(nfes)} NFe(s) processadas com sucesso.")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n[X] ERRO: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
