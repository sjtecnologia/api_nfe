#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para validar XML da NFS-e contra schemas GISS Online
"""

import sys
from lxml import etree

# Caminhos dos schemas
XSD_DIR = "docs/nfse_sjrp_giss/schemas_modificados_gissv2/Schemas_XSD_Servicos_Prestados/v2_04"
XSD_PRINCIPAL = f"{XSD_DIR}/enviar-lote-rps-envio-v2_04.xsd"

def validar_xml_contra_xsd(xml_path: str, xsd_path: str) -> bool:
    """
    Valida um XML contra um XSD
    
    Args:
        xml_path: Caminho do arquivo XML
        xsd_path: Caminho do arquivo XSD
        
    Returns:
        True se válido, False caso contrário
    """
    try:
        print(f"\n{'='*80}")
        print(f"📋 VALIDANDO XML CONTRA XSD")
        print(f"{'='*80}\n")
        print(f"📄 XML: {xml_path}")
        print(f"📐 XSD: {xsd_path}\n")
        
        # Carregar XSD
        print("⏳ Carregando schema XSD...")
        with open(xsd_path, 'r', encoding='utf-8') as f:
            xsd_doc = etree.parse(f)
            schema = etree.XMLSchema(xsd_doc)
        print("✅ Schema carregado\n")
        
        # Carregar XML
        print("⏳ Carregando XML...")
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_doc = etree.parse(f)
        print("✅ XML carregado\n")
        
        # Validar
        print("⏳ Validando XML contra schema...\n")
        is_valid = schema.validate(xml_doc)
        
        if is_valid:
            print(f"{'='*80}")
            print("✅ XML VÁLIDO! 🎉")
            print(f"{'='*80}\n")
            print("O XML está em conformidade com o schema GISS Online v2.04")
            return True
        else:
            print(f"{'='*80}")
            print("❌ XML INVÁLIDO!")
            print(f"{'='*80}\n")
            print("Erros encontrados:\n")
            for idx, error in enumerate(schema.error_log, 1):
                print(f"[ERRO {idx}]")
                print(f"  Linha: {error.line}")
                print(f"  Coluna: {error.column}")
                print(f"  Mensagem: {error.message}")
                print(f"  Tipo: {error.type_name}")
                print()
            return False
            
    except FileNotFoundError as e:
        print(f"❌ Arquivo não encontrado: {e}")
        return False
    except etree.XMLSyntaxError as e:
        print(f"❌ Erro de sintaxe XML: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro ao validar: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Validar XML de teste
    xml_file = "/tmp/nfse_giss_test.xml"
    
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    
    print(f"\n🔍 Iniciando validação GISS Online")
    print(f"📁 Arquivo: {xml_file}\n")
    
    sucesso = validar_xml_contra_xsd(xml_file, XSD_PRINCIPAL)
    
    sys.exit(0 if sucesso else 1)
