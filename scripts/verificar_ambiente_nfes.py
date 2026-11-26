#!/usr/bin/env python3
"""
Script para verificar o ambiente (Homologação ou Produção) de NFes específicas
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import SessionLocal
from database.models import NFeEmitidas
from sqlalchemy import text
import json

# Chaves a verificar
CHAVES = [
    "35251201517186000113550010000000011514449031",
    "35251201517186000113550010000000011234022356",
    "35251201517186000113550010000000011971179444",
    "35251201517186000113550010000000011369070863",
    "35251201517186000113550010000000051099422435",
    "35251201517186000113550010000000061287746851",
    "35251201517186000113550010000000201083502139",
    "35251201517186000113550010000000071324665250"
]

def extrair_ambiente_xml(xml_content):
    """Extrai o ambiente do XML da NFe"""
    if not xml_content:
        return None
    
    # Procurar tag tpAmb
    import re
    match = re.search(r'<tpAmb>(\d)</tpAmb>', xml_content)
    if match:
        amb = match.group(1)
        return "PRODUÇÃO" if amb == "1" else "HOMOLOGAÇÃO"
    return None

def verificar_nfes():
    """Verifica o ambiente das NFes"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("VERIFICAÇÃO DE AMBIENTE DAS NFEs")
        print("="*80 + "\n")
        
        encontradas = []
        nao_encontradas = []
        
        for chave in CHAVES:
            print(f"🔍 Verificando chave: {chave[:20]}...{chave[-10:]}")
            
            # Buscar NFe pela chave
            nfe = db.query(NFeEmitidas).filter(
                NFeEmitidas.chave_acesso == chave
            ).first()
            
            if nfe:
                # Tentar extrair ambiente do XML
                ambiente = None
                
                if nfe.json_nfe:
                    try:
                        if isinstance(nfe.json_nfe, str):
                            json_data = json.loads(nfe.json_nfe)
                        else:
                            json_data = nfe.json_nfe
                        
                        xml_content = json_data.get('xml_content', '')
                        ambiente = extrair_ambiente_xml(xml_content)
                    except Exception as e:
                        print(f"   ⚠️  Erro ao extrair ambiente do XML: {e}")
                
                # Se não conseguiu extrair do XML, tentar do campo ambiente
                if not ambiente and hasattr(nfe, 'ambiente'):
                    amb_valor = nfe.ambiente
                    ambiente = "PRODUÇÃO" if amb_valor == 1 else "HOMOLOGAÇÃO" if amb_valor == 2 else "DESCONHECIDO"
                
                if not ambiente:
                    ambiente = "NÃO IDENTIFICADO"
                
                encontradas.append({
                    'chave': chave,
                    'numero': nfe.numero,
                    'status': nfe.status,
                    'ambiente': ambiente,
                    'data_emissao': nfe.data_emissao
                })
                
                print(f"   ✅ Encontrada - Número: {nfe.numero} | Status: {nfe.status} | Ambiente: {ambiente}")
            else:
                nao_encontradas.append(chave)
                print(f"   ❌ Não encontrada no banco de dados")
            
            print()
        
        # Resumo
        print("\n" + "="*80)
        print("RESUMO")
        print("="*80 + "\n")
        
        if encontradas:
            print(f"✅ NFes ENCONTRADAS ({len(encontradas)}):\n")
            
            producao = [n for n in encontradas if n['ambiente'] == 'PRODUÇÃO']
            homologacao = [n for n in encontradas if n['ambiente'] == 'HOMOLOGAÇÃO']
            nao_identificado = [n for n in encontradas if n['ambiente'] in ['NÃO IDENTIFICADO', 'DESCONHECIDO']]
            
            if producao:
                print(f"🔴 PRODUÇÃO ({len(producao)}):")
                for nfe in producao:
                    print(f"   • NFe {nfe['numero']} - {nfe['chave'][:20]}...{nfe['chave'][-10:]}")
                    print(f"     Status: {nfe['status']} | Data: {nfe['data_emissao']}")
                print()
            
            if homologacao:
                print(f"🟡 HOMOLOGAÇÃO ({len(homologacao)}):")
                for nfe in homologacao:
                    print(f"   • NFe {nfe['numero']} - {nfe['chave'][:20]}...{nfe['chave'][-10:]}")
                    print(f"     Status: {nfe['status']} | Data: {nfe['data_emissao']}")
                print()
            
            if nao_identificado:
                print(f"⚪ NÃO IDENTIFICADO ({len(nao_identificado)}):")
                for nfe in nao_identificado:
                    print(f"   • NFe {nfe['numero']} - {nfe['chave'][:20]}...{nfe['chave'][-10:]}")
                    print(f"     Status: {nfe['status']} | Data: {nfe['data_emissao']}")
                print()
        
        if nao_encontradas:
            print(f"❌ NFes NÃO ENCONTRADAS ({len(nao_encontradas)}):")
            for chave in nao_encontradas:
                print(f"   • {chave[:20]}...{chave[-10:]}")
            print()
        
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Erro ao verificar NFes: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verificar_nfes()
