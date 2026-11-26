"""
NFC-e Generator - Gerador de Nota Fiscal de Consumidor Eletrônica (Modelo 65)
Adaptado do nfe_service.py para suporte específico de NFC-e
"""

from datetime import datetime
import uuid
import hashlib
import qrcode
from qrcode import constants
import base64
from io import BytesIO
from decimal import Decimal
from typing import Dict, Any, Optional
import xml.etree.ElementTree as ET

from config.settings import HABILITAR_IBS_CBS

def gerar_chave_acesso_nfce(
    uf_codigo: str,
    ano_mes: str,  # AAMM
    cnpj: str,
    modelo: str,  # 65 para NFC-e
    serie: str,
    numero: str,
    tipo_emissao: str,  # 1=Normal, 9=Contingência
    codigo_numerico: str  # 8 dígitos aleatórios
) -> str:
    """
    Gera chave de acesso da NFC-e (44 dígitos)
    Formato: UF+AAMM+CNPJ+MOD+SERIE+NUMERO+TPEMIS+COD_NUMERICO+DV
    """
    # Limpar CNPJ
    cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
    
    # Montar chave sem DV (43 dígitos)
    chave_sem_dv = (
        uf_codigo.zfill(2) +      # 2 dígitos
        ano_mes +                  # 4 dígitos  
        cnpj_limpo.zfill(14) +    # 14 dígitos
        modelo.zfill(2) +          # 2 dígitos
        serie.zfill(3) +           # 3 dígitos
        numero.zfill(9) +          # 9 dígitos
        tipo_emissao +             # 1 dígito
        codigo_numerico.zfill(8)   # 8 dígitos
    )
    
    # Calcular dígito verificador (módulo 11)
    dv = calcular_dv_modulo11(chave_sem_dv)
    
    # Chave completa (44 dígitos)
    chave_acesso = chave_sem_dv + str(dv)
    
    return chave_acesso


def calcular_dv_modulo11(chave: str) -> int:
    """Calcula dígito verificador módulo 11 para chave de acesso"""
    multiplicadores = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    posicao = 0
    
    # Percorrer de trás para frente
    for i in range(len(chave) - 1, -1, -1):
        soma += int(chave[i]) * multiplicadores[posicao % 8]
        posicao += 1
    
    resto = soma % 11
    
    if resto == 0 or resto == 1:
        return 0
    else:
        return 11 - resto


def gerar_qrcode_nfce(
    chave_acesso: str,
    url_consulta: str,
    ambiente: str = 'homologacao'
) -> Dict[str, str]:
    """
    Gera QR Code para consulta da NFC-e pelo consumidor
    
    Returns:
        dict com 'url', 'base64' e 'url_completa'
    """
    # URL de consulta NFC-e varia por UF
    # Exemplo SP: https://www.fazenda.sp.gov.br/nfce/qrcode
    
    # Extrair UF da chave (primeiros 2 dígitos)
    uf_codigo = chave_acesso[:2]
    
    # URLs por UF (ambiente de homologação)
    urls_homologacao = {
        '35': 'https://www.homologacao.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx',
        # Adicionar mais UFs conforme necessário
    }
    
    urls_producao = {
        '35': 'https://www.nfce.fazenda.sp.gov.br/NFCeConsultaPublica/Paginas/ConsultaQRCode.aspx',
    }
    
    # Selecionar URL base
    urls = urls_homologacao if ambiente == 'homologacao' else urls_producao
    url_base = urls.get(uf_codigo, url_consulta)
    
    # Montar URL completa
    url_completa = f"{url_base}?chNFe={chave_acesso}"
    
    # Gerar QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url_completa)
    qr.make(fit=True)
    
    # Gerar imagem
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Converter para base64
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        'url': url_base,
        'url_completa': url_completa,
        'base64': img_base64,
        'chave_acesso': chave_acesso
    }


def _to_decimal(valor: Any) -> Decimal:
    try:
        if valor is None:
            return Decimal('0')
        return Decimal(str(valor).replace(',', '.'))
    except Exception:
        return Decimal('0')


def _montar_ibs_cbs_item(item: Dict[str, Any]) -> Optional[Dict[str, Decimal]]:
    classificacao = item.get('classificacao_ibs_cbs') or {}
    if not classificacao:
        return None

    v_bc = _to_decimal(item.get('valor_total', 0))
    p_ibs_uf = _to_decimal(classificacao.get('aliquota_ibs_uf', 0))
    p_ibs_mun = _to_decimal(classificacao.get('aliquota_ibs_mun', 0))
    p_cbs = _to_decimal(classificacao.get('aliquota_cbs', 0))

    v_ibs_uf = (v_bc * p_ibs_uf / Decimal('100')).quantize(Decimal('0.01'))
    v_ibs_mun = (v_bc * p_ibs_mun / Decimal('100')).quantize(Decimal('0.01'))
    v_ibs = (v_ibs_uf + v_ibs_mun).quantize(Decimal('0.01'))
    v_cbs = (v_bc * p_cbs / Decimal('100')).quantize(Decimal('0.01'))

    return {
        'cClassTrib': str(classificacao.get('codigo', '')).replace('-', '')[-6:].zfill(6),
        'vBC': v_bc.quantize(Decimal('0.01')),
        'pIBSUF': p_ibs_uf.quantize(Decimal('0.01')),
        'vIBSUF': v_ibs_uf,
        'pIBSMun': p_ibs_mun.quantize(Decimal('0.01')),
        'vIBSMun': v_ibs_mun,
        'vIBS': v_ibs,
        'pCBS': p_cbs.quantize(Decimal('0.01')),
        'vCBS': v_cbs,
    }


def _adicionar_bloco_ibscbs(imposto: ET.Element, ibs_cbs_data: Dict[str, Decimal]) -> None:
    ibscbs = ET.SubElement(imposto, 'IBSCBS')
    ET.SubElement(ibscbs, 'CST').text = '000'
    ET.SubElement(ibscbs, 'cClassTrib').text = ibs_cbs_data['cClassTrib']

    g_ibscbs = ET.SubElement(ibscbs, 'gIBSCBS')
    ET.SubElement(g_ibscbs, 'vBC').text = f"{ibs_cbs_data['vBC']:.2f}"

    g_ibs_uf = ET.SubElement(g_ibscbs, 'gIBSUF')
    ET.SubElement(g_ibs_uf, 'pIBSUF').text = f"{ibs_cbs_data['pIBSUF']:.2f}"
    ET.SubElement(g_ibs_uf, 'vIBSUF').text = f"{ibs_cbs_data['vIBSUF']:.2f}"

    g_ibs_mun = ET.SubElement(g_ibscbs, 'gIBSMun')
    ET.SubElement(g_ibs_mun, 'pIBSMun').text = f"{ibs_cbs_data['pIBSMun']:.2f}"
    ET.SubElement(g_ibs_mun, 'vIBSMun').text = f"{ibs_cbs_data['vIBSMun']:.2f}"

    ET.SubElement(g_ibscbs, 'vIBS').text = f"{ibs_cbs_data['vIBS']:.2f}"

    g_cbs = ET.SubElement(g_ibscbs, 'gCBS')
    ET.SubElement(g_cbs, 'pCBS').text = f"{ibs_cbs_data['pCBS']:.2f}"
    ET.SubElement(g_cbs, 'vCBS').text = f"{ibs_cbs_data['vCBS']:.2f}"


def _adicionar_bloco_ibscbstot(total: ET.Element, totais_ibs: Dict[str, Decimal], totais_cbs: Dict[str, Decimal]) -> None:
    ibscbs_tot = ET.SubElement(total, 'IBSCBSTot')
    ET.SubElement(ibscbs_tot, 'vBCIBSCBS').text = f"{totais_ibs['vBCTotal']:.2f}"

    g_ibs = ET.SubElement(ibscbs_tot, 'gIBS')
    g_ibs_uf = ET.SubElement(g_ibs, 'gIBSUF')
    ET.SubElement(g_ibs_uf, 'vDif').text = '0.00'
    ET.SubElement(g_ibs_uf, 'vDevTrib').text = '0.00'
    ET.SubElement(g_ibs_uf, 'vIBSUF').text = f"{totais_ibs['vIBSUF']:.2f}"

    g_ibs_mun = ET.SubElement(g_ibs, 'gIBSMun')
    ET.SubElement(g_ibs_mun, 'vDif').text = '0.00'
    ET.SubElement(g_ibs_mun, 'vDevTrib').text = '0.00'
    ET.SubElement(g_ibs_mun, 'vIBSMun').text = f"{totais_ibs['vIBSMun']:.2f}"

    ET.SubElement(g_ibs, 'vIBS').text = f"{totais_ibs['vIBS']:.2f}"
    ET.SubElement(g_ibs, 'vCredPres').text = '0.00'
    ET.SubElement(g_ibs, 'vCredPresCondSus').text = '0.00'

    g_cbs = ET.SubElement(ibscbs_tot, 'gCBS')
    ET.SubElement(g_cbs, 'vDif').text = '0.00'
    ET.SubElement(g_cbs, 'vDevTrib').text = '0.00'
    ET.SubElement(g_cbs, 'vCBS').text = f"{totais_cbs['vCBS']:.2f}"
    ET.SubElement(g_cbs, 'vCredPres').text = '0.00'
    ET.SubElement(g_cbs, 'vCredPresCondSus').text = '0.00'


def gerar_xml_nfce(dados: Dict[str, Any]) -> str:
    """
    Gera XML da NFC-e (Modelo 65)
    
    Diferenças principais da NF-e:
    - Modelo 65 ao invés de 55
    - Destinatário opcional (apenas CPF se informado)
    - Obrigatório: QR Code e URL de consulta
    - Simplificado para venda ao consumidor final
    """
    
    # Namespace NFe 4.0
    ns = "http://www.portalfiscal.inf.br/nfe"
    ET.register_namespace('', ns)
    
    # Raiz NFe
    nfe_elem = ET.Element('{%s}NFe' % ns, xmlns=ns)
    inf_nfe = ET.SubElement(nfe_elem, 'infNFe', versao="4.00")
    
    # Gerar ID da NFe (chave de acesso)
    emitente = dados['emitente']
    nfce_info = dados['nfce_info']
    
    # Código numérico aleatório (8 dígitos)
    codigo_numerico = str(uuid.uuid4().int)[:8]
    
    # Data/hora de emissão
    dh_emit = datetime.now().strftime('%Y-%m-%dT%H:%M:%S-03:00')
    ano_mes = datetime.now().strftime('%y%m')
    
    chave_acesso = gerar_chave_acesso_nfce(
        uf_codigo=str(emitente['uf_codigo']),
        ano_mes=ano_mes,
        cnpj=emitente['cnpj'],
        modelo='65',  # NFC-e
        serie=str(nfce_info['serie']),
        numero=str(nfce_info['numero']),
        tipo_emissao='1',  # Normal
        codigo_numerico=codigo_numerico
    )
    
    inf_nfe.set('Id', f'NFe{chave_acesso}')
    
    # ===== IDE - Identificação =====
    ide = ET.SubElement(inf_nfe, 'ide')
    ET.SubElement(ide, 'cUF').text = str(emitente['uf_codigo'])
    ET.SubElement(ide, 'cNF').text = codigo_numerico
    ET.SubElement(ide, 'natOp').text = nfce_info.get('natureza_operacao', 'Venda')
    ET.SubElement(ide, 'mod').text = '65'  # Modelo 65 = NFC-e
    ET.SubElement(ide, 'serie').text = str(nfce_info['serie'])
    ET.SubElement(ide, 'nNF').text = str(nfce_info['numero'])
    ET.SubElement(ide, 'dhEmi').text = dh_emit
    ET.SubElement(ide, 'tpNF').text = '1'  # 1=Saída
    ET.SubElement(ide, 'idDest').text = '1'  # 1=Operação interna
    ET.SubElement(ide, 'cMunFG').text = str(emitente['codigo_municipio'])
    ET.SubElement(ide, 'tpImp').text = '4'  # 4=DANFE NFC-e
    ET.SubElement(ide, 'tpEmis').text = '1'  # 1=Normal
    ET.SubElement(ide, 'cDV').text = chave_acesso[-1]  # Dígito verificador
    ET.SubElement(ide, 'tpAmb').text = '1' if nfce_info.get('ambiente') == 'producao' else '2'
    ET.SubElement(ide, 'finNFe').text = '1'  # 1=NF-e normal
    ET.SubElement(ide, 'indFinal').text = '1'  # 1=Consumidor final
    ET.SubElement(ide, 'indPres').text = '1'  # 1=Operação presencial
    ET.SubElement(ide, 'procEmi').text = '0'  # 0=Emissão própria
    ET.SubElement(ide, 'verProc').text = 'API_NFE_v1.0'
    
    # ===== EMIT - Emitente =====
    emit = ET.SubElement(inf_nfe, 'emit')
    ET.SubElement(emit, 'CNPJ').text = ''.join(filter(str.isdigit, emitente['cnpj']))
    ET.SubElement(emit, 'xNome').text = emitente['razao_social']
    ET.SubElement(emit, 'xFant').text = emitente.get('nome_fantasia', emitente['razao_social'])
    
    # Endereço do emitente
    ender_emit = ET.SubElement(emit, 'enderEmit')
    ET.SubElement(ender_emit, 'xLgr').text = emitente['logradouro']
    ET.SubElement(ender_emit, 'nro').text = emitente['numero']
    if emitente.get('complemento'):
        ET.SubElement(ender_emit, 'xCpl').text = emitente['complemento']
    ET.SubElement(ender_emit, 'xBairro').text = emitente['bairro']
    ET.SubElement(ender_emit, 'cMun').text = str(emitente['codigo_municipio'])
    ET.SubElement(ender_emit, 'xMun').text = emitente['municipio']
    ET.SubElement(ender_emit, 'UF').text = emitente['uf']
    ET.SubElement(ender_emit, 'CEP').text = ''.join(filter(str.isdigit, emitente['cep']))
    ET.SubElement(ender_emit, 'cPais').text = '1058'
    ET.SubElement(ender_emit, 'xPais').text = 'Brasil'
    
    ET.SubElement(emit, 'IE').text = ''.join(filter(str.isdigit, emitente['inscricao_estadual']))
    ET.SubElement(emit, 'CRT').text = str(emitente.get('regime_tributario', '1'))
    
    # ===== DEST - Destinatário (OPCIONAL para NFC-e) =====
    destinatario = dados.get('destinatario')
    if destinatario and destinatario.get('cpf_cnpj'):
        dest = ET.SubElement(inf_nfe, 'dest')
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, destinatario['cpf_cnpj']))
        
        if len(cpf_cnpj_limpo) == 11:
            ET.SubElement(dest, 'CPF').text = cpf_cnpj_limpo
        else:
            ET.SubElement(dest, 'CNPJ').text = cpf_cnpj_limpo
        
        if destinatario.get('nome'):
            ET.SubElement(dest, 'xNome').text = destinatario['nome']
        
        ET.SubElement(dest, 'indIEDest').text = '9'  # 9=Não contribuinte
    
    # ===== DET - Itens =====
    itens_ibs_cbs = []
    v_bc_ibs_cbs_total = Decimal('0')
    v_ibs_uf_total = Decimal('0')
    v_ibs_mun_total = Decimal('0')
    v_ibs_total = Decimal('0')
    v_cbs_total = Decimal('0')

    for idx, item in enumerate(dados['itens'], start=1):
        det = ET.SubElement(inf_nfe, 'det', nItem=str(idx))
        
        # Produto
        prod = ET.SubElement(det, 'prod')
        ET.SubElement(prod, 'cProd').text = item['codigo']
        ET.SubElement(prod, 'cEAN').text = 'SEM GTIN'
        ET.SubElement(prod, 'xProd').text = item['descricao']
        ET.SubElement(prod, 'NCM').text = item['ncm']
        ET.SubElement(prod, 'CFOP').text = item['cfop']
        ET.SubElement(prod, 'uCom').text = item['unidade']
        ET.SubElement(prod, 'qCom').text = f"{float(item['quantidade']):.4f}"
        ET.SubElement(prod, 'vUnCom').text = f"{float(item['valor_unitario']):.10f}"
        ET.SubElement(prod, 'vProd').text = f"{float(item['valor_total']):.2f}"
        ET.SubElement(prod, 'cEANTrib').text = 'SEM GTIN'
        ET.SubElement(prod, 'uTrib').text = item['unidade']
        ET.SubElement(prod, 'qTrib').text = f"{float(item['quantidade']):.4f}"
        ET.SubElement(prod, 'vUnTrib').text = f"{float(item['valor_unitario']):.10f}"
        ET.SubElement(prod, 'indTot').text = '1'  # 1=Compõe total da NF-e
        
        # Impostos
        imposto = ET.SubElement(det, 'imposto')
        
        # ICMS
        icms = ET.SubElement(imposto, 'ICMS')
        # Usar CSOSN para Simples Nacional ou CST para outros regimes
        if item.get('csosn'):
            icms_sn = ET.SubElement(icms, f"ICMSSN{item['csosn']}")
            ET.SubElement(icms_sn, 'orig').text = str(item.get('origem', '0'))
            ET.SubElement(icms_sn, 'CSOSN').text = item['csosn']
        elif item.get('cst_icms'):
            icms_normal = ET.SubElement(icms, f"ICMS{item['cst_icms']}")
            ET.SubElement(icms_normal, 'orig').text = str(item.get('origem', '0'))
            ET.SubElement(icms_normal, 'CST').text = item['cst_icms']
        
        # PIS
        pis = ET.SubElement(imposto, 'PIS')
        pis_nt = ET.SubElement(pis, 'PISNT')
        ET.SubElement(pis_nt, 'CST').text = '07'  # Operação isenta
        
        # COFINS
        cofins = ET.SubElement(imposto, 'COFINS')
        cofins_nt = ET.SubElement(cofins, 'COFINSNT')
        ET.SubElement(cofins_nt, 'CST').text = '07'  # Operação isenta

        if HABILITAR_IBS_CBS:
            ibs_cbs_data = _montar_ibs_cbs_item(item)
            if ibs_cbs_data:
                _adicionar_bloco_ibscbs(imposto, ibs_cbs_data)
                itens_ibs_cbs.append(ibs_cbs_data)
                v_bc_ibs_cbs_total += ibs_cbs_data['vBC']
                v_ibs_uf_total += ibs_cbs_data['vIBSUF']
                v_ibs_mun_total += ibs_cbs_data['vIBSMun']
                v_ibs_total += ibs_cbs_data['vIBS']
                v_cbs_total += ibs_cbs_data['vCBS']
    
    # ===== TOTAL - Totais =====
    total = ET.SubElement(inf_nfe, 'total')
    icms_tot = ET.SubElement(total, 'ICMSTot')
    
    totais = dados['totais']
    ET.SubElement(icms_tot, 'vBC').text = f"{float(totais.get('base_calculo', 0)):.2f}"
    ET.SubElement(icms_tot, 'vICMS').text = f"{float(totais.get('valor_icms', 0)):.2f}"
    ET.SubElement(icms_tot, 'vICMSDeson').text = '0.00'
    ET.SubElement(icms_tot, 'vFCP').text = '0.00'
    ET.SubElement(icms_tot, 'vBCST').text = '0.00'
    ET.SubElement(icms_tot, 'vST').text = '0.00'
    ET.SubElement(icms_tot, 'vFCPST').text = '0.00'
    ET.SubElement(icms_tot, 'vFCPSTRet').text = '0.00'
    ET.SubElement(icms_tot, 'vProd').text = f"{float(totais['valor_produtos']):.2f}"
    ET.SubElement(icms_tot, 'vFrete').text = '0.00'
    ET.SubElement(icms_tot, 'vSeg').text = '0.00'
    ET.SubElement(icms_tot, 'vDesc').text = f"{float(totais.get('valor_desconto', 0)):.2f}"
    ET.SubElement(icms_tot, 'vII').text = '0.00'
    ET.SubElement(icms_tot, 'vIPI').text = '0.00'
    ET.SubElement(icms_tot, 'vIPIDevol').text = '0.00'
    ET.SubElement(icms_tot, 'vPIS').text = '0.00'
    ET.SubElement(icms_tot, 'vCOFINS').text = '0.00'
    ET.SubElement(icms_tot, 'vOutro').text = '0.00'
    ET.SubElement(icms_tot, 'vNF').text = f"{float(totais['valor_total']):.2f}"

    if HABILITAR_IBS_CBS and itens_ibs_cbs:
        totais_ibs = {
            'vBCTotal': v_bc_ibs_cbs_total,
            'vIBSUF': v_ibs_uf_total,
            'vIBSMun': v_ibs_mun_total,
            'vIBS': v_ibs_total,
        }
        totais_cbs = {
            'vCBS': v_cbs_total,
        }
        _adicionar_bloco_ibscbstot(total, totais_ibs, totais_cbs)
    
    # ===== TRANSP - Transporte =====
    transp = ET.SubElement(inf_nfe, 'transp')
    ET.SubElement(transp, 'modFrete').text = '9'  # 9=Sem frete
    
    # ===== PAG - Pagamento =====
    pag = ET.SubElement(inf_nfe, 'pag')
    det_pag = ET.SubElement(pag, 'detPag')
    
    pagamento = dados['pagamento']
    ET.SubElement(det_pag, 'tPag').text = pagamento['forma_pagamento']  # 01=Dinheiro, 03=Cartão...
    ET.SubElement(det_pag, 'vPag').text = f"{float(pagamento['valor']):.2f}"
    
    # ===== INF ADIC - Informações Adicionais =====
    inf_adic = ET.SubElement(inf_nfe, 'infAdic')
    if dados.get('informacoes_complementares'):
        ET.SubElement(inf_adic, 'infCpl').text = dados['informacoes_complementares']
    
    # Gerar string XML
    tree = ET.ElementTree(nfe_elem)
    xml_str = ET.tostring(nfe_elem, encoding='unicode', method='xml')
    
    # Adicionar declaração XML
    xml_final = f'<?xml version="1.0" encoding="UTF-8"?>{xml_str}'
    
    return xml_final


def validar_nfce(dados: Dict[str, Any]) -> tuple[bool, list]:
    """
    Valida dados da NFC-e antes de gerar XML
    
    Returns:
        (bool: válido, list: erros)
    """
    erros = []
    
    # Validar emitente
    if not dados.get('emitente'):
        erros.append("Emitente não informado")
    
    # Validar itens
    if not dados.get('itens') or len(dados['itens']) == 0:
        erros.append("Nenhum item informado")
    
    # Validar pagamento
    if not dados.get('pagamento'):
        erros.append("Forma de pagamento não informada")
    
    # Validar totais
    if not dados.get('totais'):
        erros.append("Totais não informados")

    if HABILITAR_IBS_CBS and dados.get('emitente_crt') == 3:
        for idx, item in enumerate(dados.get('itens', []), start=1):
            classificacao = item.get('classificacao_ibs_cbs')
            if classificacao:
                continue
            produto = item.get('produto')
            classificacao_obj = getattr(produto, 'classificacao_ibs_cbs', None) if produto else None
            if classificacao_obj:
                continue
            erros.append(f"Item {idx}: Classificação IBS/CBS obrigatória para CRT=3")
    
    return (len(erros) == 0, erros)
