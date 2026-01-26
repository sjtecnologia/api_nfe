# Teste local da nfelib
try:
    from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe, InfNFeType, IdeType
    from lxml import etree
    
    nfe_obj = Nfe(
        infNFe=InfNFeType(
            Id="NFe35260143101347000133550010000000011234567890",
            versao="4.00",
            ide=IdeType(
                cUF="35",
                cNF="12345678",
                natOp="VENDA",
                mod="55",
                serie="1",
                nNF="1",
                dhEmi="2026-01-26T10:00:00-03:00",
                tpNF="1",
                idDest="1",
                cMunFG="3549805",
                tpImp="1",
                tpEmis="1",
                cDV="0",
                tpAmb="2",
                finNFe="1",
                indFinal="1",
                indPres="1",
                procEmi="0",
                verProc="EmiteMax_1.0"
            )
        )
    )
    
    xml_elem = nfe_obj.toDOM()
    xml_str = etree.tostring(xml_elem, encoding="unicode", pretty_print=True)
    
    print("✅ nfelib funciona!")
    print(f"\n📄 Tamanho: {len(xml_str)} chars")
    print("\n🔍 XML gerado:")
    print(xml_str[:900])
    
    if 'xmlns="http://www.portalfiscal.inf.br/nfe"' in xml_str:
        print("\n✅ xmlns CORRETO!")
    
except ImportError as e:
    print(f"❌ Erro de import: {e}")
    print("\n💡 Instale: pip install nfelib")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
