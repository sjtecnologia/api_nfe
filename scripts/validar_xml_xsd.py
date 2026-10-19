# Quando o Portal publicar o pacote com a NT 2026.008, rodar: python scripts/validar_xml_xsd.py --xml <xml_gerado> --schema <xsd_oficial>
import argparse
import sys
from pathlib import Path

from lxml import etree

XS = "{http://www.w3.org/2001/XMLSchema}"
CAMPO_NT_2026_008 = "vProdLiq"
EXIT_OK = 0
EXIT_XML_INVALIDO = 1
EXIT_SCHEMA_ANTIGO = 2


def _schema_declara_campo(xsd_path: Path, campo: str, visitados=None) -> bool:
    visitados = visitados if visitados is not None else set()
    xsd_path = xsd_path.resolve()
    if xsd_path in visitados:
        return False
    visitados.add(xsd_path)

    doc = etree.parse(str(xsd_path))
    if doc.xpath("//xs:element[@name=$n]", namespaces={"xs": XS[1:-1]}, n=campo):
        return True
    for inclusao in doc.getroot().iter(XS + "include", XS + "import"):
        local = inclusao.get("schemaLocation")
        if local and not local.startswith("http"):
            alvo = xsd_path.parent / local
            if alvo.exists() and _schema_declara_campo(alvo, campo, visitados):
                return True
    return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Valida um XML de NF-e contra um XSD.")
    parser.add_argument("--xml", required=True, help="Arquivo XML a validar")
    parser.add_argument("--schema", required=True, help="Arquivo XSD (ex.: leiauteNFe_v4.00.xsd)")
    args = parser.parse_args(argv)

    xsd_path = Path(args.schema)
    if not _schema_declara_campo(xsd_path, CAMPO_NT_2026_008):
        print("SCHEMA_ANTIGO: campos NT 2026.008 ausentes no XSD informado")
        return EXIT_SCHEMA_ANTIGO

    schema = etree.XMLSchema(etree.parse(str(xsd_path)))
    xml_doc = etree.parse(args.xml)
    if schema.validate(xml_doc):
        print("OK: XML válido contra o schema informado")
        return EXIT_OK

    for erro in schema.error_log:
        print(f"linha {erro.line}: {erro.message} | conteúdo: {erro.path}")
    return EXIT_XML_INVALIDO


if __name__ == "__main__":
    sys.exit(main())
