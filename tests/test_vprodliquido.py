from lxml import etree

from services.nfe_nfelib_service import _injetar_valores_produto_liquido


NS = "http://www.portalfiscal.inf.br/nfe"


from lxml import etree

from services.nfe_nfelib_service import _injetar_valores_produto_liquido


NS = "http://www.portalfiscal.inf.br/nfe"


def _xml_itens():
    xml = f"""<NFe xmlns="{NS}"><infNFe>
      <det nItem="1"><prod><qCom>2.0000</qCom><vProd>100.00</vProd></prod><imposto>
        <II><vII>1.00</vII></II><IPI><vIPI>2.00</vIPI></IPI>
        <ICMS><vICMS>3.00</vICMS></ICMS><PIS><vPIS>4.00</vPIS></PIS>
        <COFINS><vCOFINS>5.00</vCOFINS></COFINS><ISSQN><vISSQN>6.00</vISSQN></ISSQN>
        <IBSCBS><vIBS>7.00</vIBS><vCBS>8.00</vCBS><vIS>9.00</vIS></IBSCBS>
      </imposto></det>
      <det nItem="2"><prod><qCom>1.0000</qCom><vProd>80.00</vProd></prod><imposto>
        <II><vII>1.00</vII></II><IPI><vIPI>2.00</vIPI></IPI>
        <ICMS><vICMS>3.00</vICMS></ICMS><PIS><vPIS>4.00</vPIS></PIS>
        <COFINS><vCOFINS>5.00</vCOFINS></COFINS><ISSQN><vISSQN>6.00</vISSQN></ISSQN>
        <IBSCBS><vIBS>7.00</vIBS><vCBS>8.00</vCBS><vIS>9.00</vIS></IBSCBS>
      </imposto></det>
      <total><ICMSTot><vProd>180.00</vProd></ICMSTot></total>
    </infNFe></NFe>"""
    return etree.fromstring(xml)


def _resultados(ano_vigencia):
    xml = _xml_itens()
    total = _injetar_valores_produto_liquido(xml, [{}, {}], ano_vigencia)
    itens = xml.xpath("//*[local-name()='det']")
    values = [item.xpath("string(./*[local-name()='prod']/*[local-name()='vProdLiq'])") for item in itens]
    total_value = xml.xpath("string(//*[local-name()='vProdLiqTot'])")
    return values, total, total_value


def test_vprodliquido_em_2026_nao_subtrai_ibs_cbs_is():
    values, total, total_value = _resultados(2026)

    assert values == ["79.00", "59.00"]
    assert total == 138
    assert total_value == "138.00"


def test_vprodliquido_em_2027_subtrai_ibs_cbs_is_e_totaliza_itens():
    values, total, total_value = _resultados(2027)

    assert values == ["55.00", "35.00"]
    assert total == 90
    assert total_value == "90.00"
