#!/usr/bin/env python3
"""
Script de validação de XML NFS-e contra schemas XSD NT007 v1.03.00

Uso:
    python3 validar_xml_com_xsd.py <arquivo_xml> [arquivo_xsd]

Exemplos:
    python3 validar_xml_com_xsd.py test_nfse_nt007_output.xml
    python3 validar_xml_com_xsd.py meu_xml.xml nfse_v1.03.00.xsd
"""

import sys
import os
from lxml import etree
from pathlib import Path


def validar_xml_contra_xsd(xml_path: str, xsd_path: str = None) -> tuple:
    """
    Valida XML da NFS-e contra schema XSD
    
    Args:
        xml_path: Caminho do arquivo XML
        xsd_path: Caminho do arquivo XSD (opcional)
        
    Returns:
        (sucesso: bool, mensagem: str, erros: list)
    """
    # Verificar se arquivo XML existe
    if not os.path.exists(xml_path):
        return False, f"Arquivo XML não encontrado: {xml_path}", []
    
    # Determinar caminho do XSD
    if xsd_path is None:
        # Usar XSD padrão da NT007
        script_dir = Path(__file__).parent
        xsd_path = script_dir / "nfse_v1.03.00.xsd"
    
    # Verificar se arquivo XSD existe
    if not os.path.exists(xsd_path):
        return False, f"Arquivo XSD não encontrado: {xsd_path}\n\n" \
                     f"⚠️  IMPORTANTE: Baixe os schemas XSD oficiais do portal:\n" \
                     f"   https://www.gov.br/nfse/pt-br/biblioteca/documentacao-tecnica/rtc\n\n" \
                     f"   Procure por: 'Esquemas XSD - AnexoVI-LeiautesRN_RTC_IBSCBS-V1.03.00 - NT007'\n" \
                     f"   Extraia os arquivos neste diretório: {script_dir}", []
    
    try:
        # Carregar XSD
        print(f"📄 Carregando schema XSD: {xsd_path}")
        with open(xsd_path, 'r', encoding='utf-8') as xsd_file:
            xsd_doc = etree.parse(xsd_file)
            schema = etree.XMLSchema(xsd_doc)
        
        # Carregar e parsear XML
        print(f"📄 Carregando XML: {xml_path}")
        with open(xml_path, 'r', encoding='utf-8') as xml_file:
            xml_doc = etree.parse(xml_file)
        
        # Validar
        print(f"🔍 Validando XML contra schema...")
        is_valid = schema.validate(xml_doc)
        
        if is_valid:
            return True, "✅ XML válido conforme NT007 v1.03.00", []
        else:
            # Coletar erros
            erros = []
            for error in schema.error_log:
                erros.append({
                    'linha': error.line,
                    'coluna': error.column,
                    'mensagem': error.message,
                    'tipo': error.type_name
                })
            
            mensagem = f"❌ XML inválido - {len(erros)} erro(s) encontrado(s)"
            return False, mensagem, erros
        
    except etree.XMLSyntaxError as e:
        return False, f"❌ Erro de sintaxe XML: {str(e)}", [{'mensagem': str(e)}]
    except Exception as e:
        return False, f"❌ Erro na validação: {str(e)}", [{'mensagem': str(e)}]


def main():
    """Função principal"""
    print("="*80)
    print("VALIDAÇÃO DE XML NFS-e - NT007 v1.03.00")
    print("="*80)
    print()
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("❌ Uso incorreto!")
        print()
        print("Uso:")
        print(f"    python3 {sys.argv[0]} <arquivo_xml> [arquivo_xsd]")
        print()
        print("Exemplos:")
        print(f"    python3 {sys.argv[0]} test_nfse_nt007_output.xml")
        print(f"    python3 {sys.argv[0]} meu_xml.xml nfse_v1.03.00.xsd")
        sys.exit(1)
    
    xml_path = sys.argv[1]
    xsd_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Validar
    sucesso, mensagem, erros = validar_xml_contra_xsd(xml_path, xsd_path)
    
    print()
    print(mensagem)
    
    # Exibir erros se houver
    if erros:
        print()
        print("📋 ERROS ENCONTRADOS:")
        print()
        for i, erro in enumerate(erros, 1):
            print(f"{i}. Erro na linha {erro.get('linha', '?')}")
            print(f"   Mensagem: {erro.get('mensagem', 'Erro desconhecido')}")
            if 'tipo' in erro:
                print(f"   Tipo: {erro['tipo']}")
            print()
    
    print("="*80)
    
    # Retornar código de saída
    sys.exit(0 if sucesso else 1)


if __name__ == "__main__":
    main()
