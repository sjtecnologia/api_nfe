"""
Serviço de cálculo e geração XML para IBS/CBS - Reforma Tributária
Aplicável apenas para clientes com regime tributário CRT=3 (Lucro Real/Presumido)
"""

from decimal import Decimal
from typing import Dict, Any, List, Tuple


def calcular_ibs_cbs(valor_produto: Decimal, classificacao, db) -> Dict[str, Any]:
    """
    Calcula IBS/CBS com base na classificação tributária
    
    Args:
        valor_produto: Valor do produto (vProd)
        classificacao: Objeto ClassificacaoIBSCBS ou classificacao_id
        db: Sessão do banco de dados
        
    Returns:
        Dict com todos os valores calculados para IBS/CBS
    """
    from database.models import ClassificacaoIBSCBS
    
    # Se receber ID, busca o objeto
    if isinstance(classificacao, int):
        classificacao = db.query(ClassificacaoIBSCBS).filter_by(
            classificacao_id=classificacao
        ).first()
        
        if not classificacao:
            raise ValueError(f"Classificação IBS/CBS {classificacao} não encontrada")
    
    # Cálculos
    vBC = Decimal(str(valor_produto))
    
    # IBS UF
    pIBSUF = Decimal(str(classificacao.aliquota_ibs_uf))
    vIBSUF = round(vBC * (pIBSUF / Decimal('100')), 2)
    
    # IBS Municipal
    pIBSMun = Decimal(str(classificacao.aliquota_ibs_mun))
    vIBSMun = round(vBC * (pIBSMun / Decimal('100')), 2)
    
    # Total IBS
    vIBS = vIBSUF + vIBSMun
    
    # CBS
    pCBS = Decimal(str(classificacao.aliquota_cbs))
    vCBS = round(vBC * (pCBS / Decimal('100')), 2)
    
    return {
        'CST': '000',
        'cClassTrib': classificacao.codigo,
        'vBC': float(vBC),
        'pIBSUF': float(pIBSUF),
        'vIBSUF': float(vIBSUF),
        'pIBSMun': float(pIBSMun),
        'vIBSMun': float(vIBSMun),
        'vIBS': float(vIBS),
        'pCBS': float(pCBS),
        'vCBS': float(vCBS)
    }


def gerar_xml_ibscbs(ibs_cbs_data: Dict[str, Any]) -> str:
    """
    Gera estrutura XML <IBSCBS> para Reforma Tributária
    
    Args:
        ibs_cbs_data: Dict retornado por calcular_ibs_cbs()
        
    Returns:
        String XML formatada
    """
    # Estrutura mínima obrigatória conforme Schema XSD NFe 4.0 + Reforma Tributária
    # Removidas tags opcionais vDif e vDevTrib que podem estar causando rejeição
    xml = f"""<IBSCBS>
<CST>{ibs_cbs_data['CST']}</CST>
<cClassTrib>{ibs_cbs_data['cClassTrib']}</cClassTrib>
<gIBSCBS>
<vBC>{ibs_cbs_data['vBC']:.2f}</vBC>
<pAliq>{ibs_cbs_data['pIBSUF'] + ibs_cbs_data['pCBS']:.2f}</pAliq>
<gIBS>
<gIBSUF>
<pIBS>{ibs_cbs_data['pIBSUF']:.2f}</pIBS>
<vIBS>{ibs_cbs_data['vIBSUF']:.2f}</vIBS>
</gIBSUF>
<gIBSMun>
<pIBS>{ibs_cbs_data['pIBSMun']:.2f}</pIBS>
<vIBS>{ibs_cbs_data['vIBSMun']:.2f}</vIBS>
</gIBSMun>
<vIBS>{ibs_cbs_data['vIBS']:.2f}</vIBS>
</gIBS>
<gCBS>
<pCBS>{ibs_cbs_data['pCBS']:.2f}</pCBS>
<vCBS>{ibs_cbs_data['vCBS']:.2f}</vCBS>
</gCBS>
</gIBSCBS>
</IBSCBS>"""
    return xml


def gerar_xml_icms60(produto_data: Dict[str, Any]) -> str:
    """
    Gera estrutura XML <ICMS60> para Substituição Tributária
    
    Args:
        produto_data: Dict com dados do produto incluindo campos ST
            - origem: Origem da mercadoria (0-8)
            - vBCSTRet: Base de cálculo ICMS ST retido
            - pST: Percentual da substituição tributária
            - vICMSSubstituto: Valor ICMS do substituto
            - vICMSSTRet: Valor ICMS ST retido
        
    Returns:
        String XML formatada
    """
    xml = f"""<ICMS>
        <ICMS60>
            <orig>{produto_data.get('origem', 0)}</orig>
            <CST>60</CST>
            <vBCSTRet>{produto_data.get('vBCSTRet', 0):.2f}</vBCSTRet>
            <pST>{produto_data.get('pST', 0):.2f}</pST>
            <vICMSSubstituto>{produto_data.get('vICMSSubstituto', 0):.2f}</vICMSSubstituto>
            <vICMSSTRet>{produto_data.get('vICMSSTRet', 0):.2f}</vICMSSTRet>
        </ICMS60>
    </ICMS>"""
    return xml


def gerar_xml_totais_ibscbs(totais_ibs: Dict[str, Any], totais_cbs: Dict[str, Any]) -> str:
    """
    Gera seção <IBSCBSTot> dos totais da NFe
    
    Args:
        totais_ibs: Dict com totalizações IBS
            - vBCTotal: Base de cálculo total
            - vIBSUF: Total IBS UF
            - vIBSMun: Total IBS Municipal
            - vIBS: Total IBS
        totais_cbs: Dict com totalizações CBS
            - vCBS: Total CBS
        
    Returns:
        String XML formatada
    """
    # Estrutura mínima obrigatória conforme Schema XSD
    xml = f"""<IBSCBSTot>
<vBCIBSCBS>{totais_ibs['vBCTotal']:.2f}</vBCIBSCBS>
<gIBS>
<gIBSUF>
<vIBS>{totais_ibs['vIBSUF']:.2f}</vIBS>
</gIBSUF>
<gIBSMun>
<vIBS>{totais_ibs['vIBSMun']:.2f}</vIBS>
</gIBSMun>
<vIBS>{totais_ibs['vIBS']:.2f}</vIBS>
</gIBS>
<gCBS>
<vCBS>{totais_cbs['vCBS']:.2f}</vCBS>
</gCBS>
</IBSCBSTot>"""
    return xml


def gerar_xml_autorizacoes(autorizacoes: List[str]) -> str:
    """
    Gera seção <autXML> para cada CPF/CNPJ autorizado a baixar o XML da NFe
    
    Args:
        autorizacoes: Lista de strings com CPF/CNPJ (pode conter formatação)
        
    Returns:
        String XML formatada com todos os <autXML>
    """
    xml_parts = []
    for aut in autorizacoes:
        # Remove caracteres não numéricos
        aut_limpo = ''.join(filter(str.isdigit, aut))
        
        if len(aut_limpo) == 11:  # CPF
            xml_parts.append(f"    <autXML>\n        <CPF>{aut_limpo}</CPF>\n    </autXML>")
        elif len(aut_limpo) == 14:  # CNPJ
            xml_parts.append(f"    <autXML>\n        <CNPJ>{aut_limpo}</CNPJ>\n    </autXML>")
    
    return '\n'.join(xml_parts)


def totalizar_ibs_cbs(itens_ibs_cbs: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Totaliza valores IBS/CBS de todos os itens da NFe
    
    Args:
        itens_ibs_cbs: Lista de dicts retornados por calcular_ibs_cbs()
        
    Returns:
        Tuple (totais_ibs, totais_cbs)
    """
    vBCTotal = Decimal('0')
    vIBSUF_total = Decimal('0')
    vIBSMun_total = Decimal('0')
    vCBS_total = Decimal('0')
    
    for item in itens_ibs_cbs:
        vBCTotal += Decimal(str(item['vBC']))
        vIBSUF_total += Decimal(str(item['vIBSUF']))
        vIBSMun_total += Decimal(str(item['vIBSMun']))
        vCBS_total += Decimal(str(item['vCBS']))
    
    vIBS_total = vIBSUF_total + vIBSMun_total
    
    totais_ibs = {
        'vBCTotal': float(vBCTotal),
        'vIBSUF': float(vIBSUF_total),
        'vIBSMun': float(vIBSMun_total),
        'vIBS': float(vIBS_total)
    }
    
    totais_cbs = {
        'vCBS': float(vCBS_total)
    }
    
    return totais_ibs, totais_cbs


def gerar_xml_pisnt_cst04() -> str:
    """
    Gera estrutura XML <PISNT> com CST 04 (Operação Tributável Monofásica)
    Usado em operações de revenda com alíquota zero
    
    Returns:
        String XML formatada
    """
    return """<PIS>
        <PISNT>
            <CST>04</CST>
        </PISNT>
    </PIS>"""


def gerar_xml_cofinsnt_cst04() -> str:
    """
    Gera estrutura XML <COFINSNT> com CST 04 (Operação Tributável Monofásica)
    Usado em operações de revenda com alíquota zero
    
    Returns:
        String XML formatada
    """
    return """<COFINS>
        <COFINSNT>
            <CST>04</CST>
        </COFINSNT>
    </COFINS>"""


def validar_dados_crt3(dados_nfe: Dict[str, Any]) -> List[str]:
    """
    Valida se todos os campos obrigatórios para CRT=3 estão presentes
    
    Args:
        dados_nfe: Dict com dados da NFe a ser emitida
        
    Returns:
        Lista de erros (vazia se tudo OK)
    """
    erros = []
    
    # Validar classificação IBS/CBS nos produtos
    if 'produtos' in dados_nfe:
        for idx, produto in enumerate(dados_nfe['produtos'], 1):
            if not produto.get('classificacao_ibs_cbs_id'):
                erros.append(f"Produto {idx}: Classificação IBS/CBS obrigatória para CRT=3")
    
    # Validar autorizações XML (se informadas)
    if 'autorizacoes' in dados_nfe and dados_nfe['autorizacoes']:
        for aut in dados_nfe['autorizacoes']:
            aut_limpo = ''.join(filter(str.isdigit, aut))
            if len(aut_limpo) not in [11, 14]:
                erros.append(f"Autorização inválida: {aut} (deve ser CPF com 11 dígitos ou CNPJ com 14)")
    
    return erros
