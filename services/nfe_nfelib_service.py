"""
Serviço de geração de NFe usando a biblioteca nfelib
Substitui a geração manual de XML por uma biblioteca validada e homologada
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from decimal import Decimal, InvalidOperation
from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe
from nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 import TenderEmi, Tendereco
from utils.helpers import get_uf_ibge_code, limpar_cnpj_cpf, normalizar_texto as remover_acentos, converter_para_decimal
from utils.reforma_tributaria import vigencia_reforma
from services.ibs_cbs_service import calcular_ibs_cbs, gerar_xml_ibscbs, gerar_xml_totais_ibscbs
from services.cbenef_sp_table import validar_cbenef_para_cst, codigos_para_cst, TABELA_CBENEF_SP
from config.settings import HABILITAR_IBS_CBS
import re


# Regras da tabela cBenef-SP (v20260626)
CBENEF_SP_CSTS_SEM_OBRIGATORIEDADE = {'00', '02', '10', '15', '60', '61'}
CBENEF_SP_CSTS_REDUCAO_ISENCAO = {'20', '30', '40', '41', '50', '51', '53', '70', '90'}
CBENEF_SP_SEM_CBENEF_BLOQUEIO = datetime(2026, 7, 1, tzinfo=timezone.utc)


DECIMAL_FIELD_LABELS = {
    'quantidade': 'Quantidade',
    'valor_unitario': 'Valor unitário',
    'valor_total': 'Valor total',
    'aliquota_icms': 'Alíquota de ICMS',
    'reducao_base_icms': 'Redução da base de ICMS',
    'bc_icms': 'Base de cálculo do ICMS',
    'valor_icms': 'Valor do ICMS',
    'vBCSTRet': 'Base ST retida',
    'pST': 'Alíquota ST',
    'vICMSSubstituto': 'Valor do ICMS substituto',
    'vICMSSTRet': 'Valor do ICMS ST retido',
    'aliquota_pis': 'Alíquota do PIS',
    'aliquota_cofins': 'Alíquota do COFINS',
    'aliquota_ipi': 'Alíquota do IPI',
}


# Mapeamento de códigos IBGE mais comuns → nome do município
# IMPORTANTE: Usar capitalização mista (Primeira Letra Maiúscula) como aceito pela SEFAZ
MUNICIPIOS_IBGE = {
    '3550308': 'Sao Paulo',
    '3549805': 'Sao Jose do Rio Preto',
    '3304557': 'Rio de Janeiro',
    '4106902': 'Curitiba',
    '2927408': 'Salvador',
    '2611606': 'Recife',
    '2304400': 'Fortaleza',
    '1302603': 'Manaus',
    '5300108': 'Brasilia',
    '2613305': 'Sao Joaquim do Monte',  # PE
}


# remover_acentos foi removida: importada de utils.helpers como normalizar_texto (acima).

def normalizar_municipio(codigo_ibge: str, nome_municipio: str) -> str:
    """
    Valida e corrige nome do município baseado no código IBGE
    para evitar Erro 225 - Schema XML
    Usa capitalização mista como aceito pela SEFAZ
    """
    codigo_ibge = str(codigo_ibge).strip()
    
    # Se temos o código no mapeamento, usar o nome correto
    if codigo_ibge in MUNICIPIOS_IBGE:
        nome_correto = MUNICIPIOS_IBGE[codigo_ibge]
        if nome_municipio.upper() != nome_correto.upper():
            print(f"⚠️ [CORREÇÃO] Município '{nome_municipio}' corrigido para '{nome_correto}' (código {codigo_ibge})")
        return nome_correto
    
    # Se não está no mapeamento, usar capitalização mista
    return nome_municipio.title()[:60]


def normalizar_uf(uf_valor: str, fallback: str = 'SP') -> str:
    """Normaliza UF para sigla de 2 letras aceita pela SEFAZ."""
    if not uf_valor:
        return fallback

    uf = str(uf_valor).strip().upper()
    if len(uf) == 2 and uf.isalpha():
        return uf

    mapa_uf = {
        'SAO PAULO': 'SP',
        'SÃO PAULO': 'SP',
        'MINAS GERAIS': 'MG',
        'RIO DE JANEIRO': 'RJ',
        'ESPIRITO SANTO': 'ES',
        'ESPÍRITO SANTO': 'ES',
        'PARANA': 'PR',
        'PARANÁ': 'PR',
        'SANTA CATARINA': 'SC',
        'RIO GRANDE DO SUL': 'RS',
        'MATO GROSSO': 'MT',
        'MATO GROSSO DO SUL': 'MS',
        'DISTRITO FEDERAL': 'DF',
        'GOIAS': 'GO',
        'GOIÁS': 'GO',
        'BAHIA': 'BA',
        'SERGIPE': 'SE',
        'ALAGOAS': 'AL',
        'PERNAMBUCO': 'PE',
        'PARAIBA': 'PB',
        'PARAÍBA': 'PB',
        'RIO GRANDE DO NORTE': 'RN',
        'CEARA': 'CE',
        'CEARÁ': 'CE',
        'PIAUI': 'PI',
        'PIAUÍ': 'PI',
        'MARANHAO': 'MA',
        'MARANHÃO': 'MA',
        'PARA': 'PA',
        'PARÁ': 'PA',
        'AMAPA': 'AP',
        'AMAPÁ': 'AP',
        'AMAZONAS': 'AM',
        'RORAIMA': 'RR',
        'RONDONIA': 'RO',
        'RONDÔNIA': 'RO',
        'ACRE': 'AC',
        'TOCANTINS': 'TO',
    }

    return mapa_uf.get(uf, fallback)


def _normalizar_valor_decimal(valor: Any, default: str) -> str:
    if valor is None:
        return default

    if isinstance(valor, Decimal):
        return str(valor)

    texto = str(valor).strip()
    if not texto:
        return default

    texto = texto.replace('R$', '').replace(' ', '')
    if ',' in texto and '.' in texto:
        if texto.rfind(',') > texto.rfind('.'):
            texto = texto.replace('.', '').replace(',', '.')
        else:
            texto = texto.replace(',', '')
    elif ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')

    return texto or default


def _decimal_from_item(item: Dict[str, Any], campo: str, default: str, idx: int) -> Decimal:
    try:
        return Decimal(_normalizar_valor_decimal(item.get(campo), default))
    except (InvalidOperation, ValueError, TypeError):
        rotulo = DECIMAL_FIELD_LABELS.get(campo, campo)
        valor_original = item.get(campo)
        descricao_item = str(item.get('descricao') or item.get('codigo_produto') or item.get('codigo') or '').strip()
        contexto_item = f"Item {idx}"
        if descricao_item:
            contexto_item += f" ({descricao_item[:60]})"
        raise ValueError(
            f"{contexto_item}: o campo '{rotulo}' está com valor inválido ({repr(valor_original)}). Use apenas números."
        )


def _extrair_cbenef_item(item: Dict[str, Any]) -> str:
    """Extrai cBenef do item aceitando variações de chave."""
    valor = (
        item.get('cbenef')
        or item.get('cBenef')
        or item.get('codigo_beneficio_fiscal')
        or item.get('codigo_beneficio_icms')
        or ''
    )
    return str(valor).strip().upper()


def _resolver_cbenef_sp(
    item: Dict[str, Any],
    idx: int,
    cst_item: str,
    uf_emitente: str,
    data_emissao: datetime
) -> str:
    """
    Resolve e valida cBenef para emissão em SP conforme tabela oficial v20260626.

    Regras:
    - CSTs sem obrigatoriedade (00, 02, 10, 15, 60, 61): não é obrigatório.
    - CSTs de redução/isenção (20, 30, 40, 41, 50, 51, 53, 70, 90): obrigatório.
    - 'SEM CBENEF' não é permitido a partir de 01/07/2026.
    - O código deve existir na tabela SP e ser válido para o CST informado.
    """
    if (uf_emitente or '').strip().upper() != 'SP':
        return _extrair_cbenef_item(item)

    cst_norm = str(cst_item or '').strip().zfill(2)
    cbenef = _extrair_cbenef_item(item)

    if cst_norm in CBENEF_SP_CSTS_SEM_OBRIGATORIEDADE:
        return cbenef

    if cst_norm in CBENEF_SP_CSTS_REDUCAO_ISENCAO and not cbenef:
        sugestoes = codigos_para_cst(cst_norm)
        hint = ''
        if sugestoes:
            hint = f" Exemplos: {', '.join(s['codigo'] for s in sugestoes[:3])}..."
        raise ValueError(
            f"Item {idx}: cBenef obrigatório para CST {cst_norm} em emissor SP "
            f"(redução/isenção de ICMS). Informe o código da tabela cBenef-SP.{hint}"
        )

    if not cbenef:
        return ''

    if cbenef == 'SEM CBENEF':
        data_ref = data_emissao
        if data_ref.tzinfo is None:
            data_ref = data_ref.replace(tzinfo=timezone.utc)
        else:
            data_ref = data_ref.astimezone(timezone.utc)

        if data_ref >= CBENEF_SP_SEM_CBENEF_BLOQUEIO:
            raise ValueError(
                f"Item {idx}: código 'SEM CBENEF' não é permitido desde 01/07/2026 "
                f"na tabela cBenef-SP. Informe código SP válido (ex.: SP099090)."
            )
        return cbenef

    # Validar formato básico
    if not re.match(r'^SP\d{6}$', cbenef):
        raise ValueError(
            f"Item {idx}: cBenef inválido '{cbenef}'. "
            f"Use formato SP + 6 dígitos (ex.: SP099090)."
        )

    # Validar código na tabela oficial e compatibilidade com o CST
    ok, erro = validar_cbenef_para_cst(cbenef, cst_norm)
    if not ok:
        raise ValueError(f"Item {idx}: {erro}")

    return cbenef


def obter_aliquota_maxima_icms_interestadual(uf_origem: str, uf_destino: str, origem_mercadoria: str) -> Decimal:
    """
    Retorna a alíquota máxima permitida para ICMS interestadual.
    Regras aplicadas:
    - 4% para produtos de origem importada (orig 1,2,3,8)
    - 7% quando origem é Sul/Sudeste (exceto ES) e destino é Norte/Nordeste/Centro-Oeste/ES
    - 12% nos demais cenários interestaduais
    """
    uf_origem = (uf_origem or '').strip().upper()
    uf_destino = (uf_destino or '').strip().upper()
    origem_mercadoria = str(origem_mercadoria or '0').strip()

    # Operação interna não usa teto interestadual.
    if not uf_origem or not uf_destino or uf_origem == uf_destino:
        return Decimal('0')

    if origem_mercadoria in {'1', '2', '3', '8'}:
        return Decimal('4')

    sul_sudeste_sem_es = {'SP', 'RJ', 'MG', 'PR', 'SC', 'RS'}
    norte_nordeste_centro_oeste_mais_es = {
        'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
        'MT', 'MS', 'PA', 'PB', 'PE', 'PI', 'RN', 'RO', 'RR', 'SE', 'TO'
    }

    if uf_origem in sul_sudeste_sem_es and uf_destino in norte_nordeste_centro_oeste_mais_es:
        return Decimal('7')

    return Decimal('12')


def obter_aliquota_interna_icms_destino(uf_destino: str) -> Decimal:
    """Alíquota interna de ICMS do estado de destino para cálculo DIFAL (EC 87/2015)."""
    tabela = {
        'AC': Decimal('17'), 'AL': Decimal('17'), 'AM': Decimal('20'),
        'AP': Decimal('18'), 'BA': Decimal('18'), 'CE': Decimal('18'),
        'DF': Decimal('18'), 'ES': Decimal('17'), 'GO': Decimal('17'),
        'MA': Decimal('20'), 'MG': Decimal('18'), 'MS': Decimal('17'),
        'MT': Decimal('17'), 'PA': Decimal('17'), 'PB': Decimal('18'),
        'PE': Decimal('18'), 'PI': Decimal('18'), 'PR': Decimal('18'),
        'RJ': Decimal('20'), 'RN': Decimal('18'), 'RO': Decimal('17'),
        'RR': Decimal('17'), 'RS': Decimal('17'), 'SC': Decimal('17'),
        'SE': Decimal('18'), 'SP': Decimal('18'), 'TO': Decimal('20'),
    }
    return tabela.get((uf_destino or '').strip().upper(), Decimal('17'))


def obter_aliquota_fcp_uf_dest(uf_destino: str) -> Decimal:
    """Alíquota do Fundo de Combate à Pobreza (FCP) do estado de destino."""
    tabela_fcp = {
        'AC': Decimal('0'),  'AL': Decimal('2'),  'AM': Decimal('2'),
        'AP': Decimal('0'),  'BA': Decimal('2'),  'CE': Decimal('2'),
        'DF': Decimal('2'),  'ES': Decimal('2'),  'GO': Decimal('2'),
        'MA': Decimal('2'),  'MG': Decimal('2'),  'MS': Decimal('2'),
        'MT': Decimal('2'),  'PA': Decimal('0'),  'PB': Decimal('2'),
        'PE': Decimal('2'),  'PI': Decimal('2'),  'PR': Decimal('0'),
        'RJ': Decimal('2'),  'RN': Decimal('2'),  'RO': Decimal('0'),
        'RR': Decimal('0'),  'RS': Decimal('0'),  'SC': Decimal('0'),
        'SE': Decimal('2'),  'SP': Decimal('2'),  'TO': Decimal('2'),
    }
    return tabela_fcp.get((uf_destino or '').strip().upper(), Decimal('0'))


def ie_valida_basica_por_uf(ie_digits: str, uf: str) -> bool:
    """Validação básica de IE por UF para evitar envio de valores claramente inválidos."""
    if not ie_digits:
        return False

    # Sequências triviais são inválidas em qualquer UF.
    if len(set(ie_digits)) == 1:
        return False

    tamanho_uf = {
        'AC': 13,
        'AL': 9,
        'AM': 9,
        'AP': 9,
        'BA': (8, 9),
        'CE': 9,
        'DF': 13,
        'ES': 9,
        'GO': 9,
        'MA': 9,
        'MG': 13,
        'MS': 9,
        'MT': (9, 11),  # MT aceita 9 ou 11 dígitos (formatos antigo/novo)
        'PA': 9,
        'PB': 9,
        'PE': 14,
        'PI': 9,
        'PR': 10,
        'RJ': 8,
        'RN': (9, 10),
        'RO': 14,
        'RR': 9,
        'RS': 10,
        'SC': 9,
        'SE': 9,
        'SP': 12,
        'TO': 11,
    }

    esperado = tamanho_uf.get((uf or '').upper())
    if esperado is None:
        return True

    if isinstance(esperado, tuple):
        return len(ie_digits) in esperado

    return len(ie_digits) == esperado


def calcular_dv_chave_acesso(chave_sem_dv: str) -> str:
    """Calcula o dígito verificador da chave de acesso da NFe"""
    multiplicadores = [2, 3, 4, 5, 6, 7, 8, 9]
    soma = 0
    pos = 0
    
    # Percorre a chave de trás para frente
    for i in range(len(chave_sem_dv) - 1, -1, -1):
        soma += int(chave_sem_dv[i]) * multiplicadores[pos % 8]
        pos += 1
    
    resto = soma % 11
    dv = 0 if resto in (0, 1) else (11 - resto)
    
    return str(dv)


def gerar_chave_acesso(emitente_data: Dict[str, Any], form_data: Dict[str, Any], 
                       numero_nfe: int, data_emissao: datetime) -> str:
    """Gera a chave de acesso de 44 dígitos da NFe"""
    
    # 1. cUF (2 dígitos)
    cuf = str(get_uf_ibge_code(emitente_data.get('uf', 'SP'))).zfill(2)
    
    # 2. AAMM (4 dígitos)
    aamm = data_emissao.strftime('%y%m')
    
    # 3. CNPJ (14 dígitos)
    cnpj = limpar_cnpj_cpf(emitente_data.get('cnpj', '')).zfill(14)
    
    # 4. mod (2 dígitos)
    mod = "55"
    
    # 5. serie (3 dígitos)
    serie = str(form_data.get('serie', '1')).zfill(3)
    
    # 6. nNF (9 dígitos)
    nnf = str(numero_nfe).zfill(9)
    
    # 7. tpEmis (1 dígito)
    tp_emis = "1"  # Emissão normal
    
    # 8. cNF (8 dígitos)
    cnf = form_data.get('codigo_numerico', str(abs(hash(str(numero_nfe))) % 100000000)).zfill(8)
    
    # Monta chave sem DV (43 dígitos)
    chave_sem_dv = cuf + aamm + cnpj + mod + serie + nnf + tp_emis + cnf
    
    # 9. Calcula DV (1 dígito)
    dv = calcular_dv_chave_acesso(chave_sem_dv)
    
    # Chave completa (44 dígitos)
    chave_acesso = chave_sem_dv + dv
    
    print(f"✅ [NFELIB] Chave de acesso gerada: {chave_acesso}")
    
    return chave_acesso


def _injetar_valores_produto_liquido(xml_tree, items, ano_vigencia_reforma):
    from lxml import etree

    ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
    det_elements = xml_tree.findall('.//nfe:det', ns)
    v_prod_liq_total = Decimal('0.00')
    tributos_liquidos = (
        ('vII', 'vII'),
        ('vIPI', 'valor_ipi'),
        ('vICMS', 'valor_icms'),
        ('vPIS', 'valor_pis'),
        ('vCOFINS', 'valor_cofins'),
        ('vISSQN', 'valor_issqn'),
    )
    if ano_vigencia_reforma == 2027:
        tributos_liquidos += (
            ('vIBS', 'vIBS'),
            ('vCBS', 'vCBS'),
            ('vIS', 'vIS'),
        )

    for det_elem, item in zip(det_elements, items):
        prod_elem = det_elem.find('nfe:prod', ns)
        if prod_elem is None:
            continue
        valor_prod = Decimal(prod_elem.findtext('nfe:vProd', '0', ns))
        quantidade_prod = Decimal(prod_elem.findtext('nfe:qCom', '0', ns))
        tributos_item = Decimal('0.00')
        for tag_xml, chave_item in tributos_liquidos:
            valores_xml = det_elem.xpath(
                ".//*[local-name()=$nome]/text()",
                nome=tag_xml,
            )
            if valores_xml:
                tributos_item += sum(
                    (Decimal(str(valor).replace(',', '.')) for valor in valores_xml),
                    Decimal('0.00'),
                )
            else:
                valor_item = item.get(chave_item, item.get(tag_xml, '0'))
                try:
                    tributos_item += Decimal(str(valor_item or '0').replace(',', '.'))
                except (InvalidOperation, ValueError):
                    pass

        valor_prod_liq = converter_para_decimal(valor_prod - tributos_item, 2)
        valor_unitario_liq = (
            converter_para_decimal(valor_prod_liq / quantidade_prod, 4)
            if quantidade_prod else Decimal('0.0000')
        )
        vprod_elem = prod_elem.find('nfe:vProd', ns)
        if vprod_elem is None:
            raise ValueError(f"Item {det_elem.get('nItem')}: tag vProd ausente")
        v_un_com_liq_elem = etree.Element('{http://www.portalfiscal.inf.br/nfe}vUnComLiq')
        v_un_com_liq_elem.text = f"{valor_unitario_liq:.4f}"
        v_prod_liq_elem = etree.Element('{http://www.portalfiscal.inf.br/nfe}vProdLiq')
        v_prod_liq_elem.text = f"{valor_prod_liq:.2f}"
        vprod_index = list(prod_elem).index(vprod_elem)
        # TODO: validar posição contra XSD oficial da NT 2026.008 na homologação (tpAmb=2).
        prod_elem.insert(vprod_index + 1, v_un_com_liq_elem)
        prod_elem.insert(vprod_index + 2, v_prod_liq_elem)
        v_prod_liq_total += valor_prod_liq

    icms_tot_elem = xml_tree.find('.//nfe:total/nfe:ICMSTot', ns)
    if icms_tot_elem is not None and icms_tot_elem.find('nfe:vProdLiqTot', ns) is None:
        total_liquido_elem = etree.Element('{http://www.portalfiscal.inf.br/nfe}vProdLiqTot')
        valor_prod_total_elem = icms_tot_elem.find('nfe:vProd', ns)
        posicao_total = (
            list(icms_tot_elem).index(valor_prod_total_elem) + 1
            if valor_prod_total_elem is not None else len(icms_tot_elem)
        )
        total_liquido_elem.text = f"{v_prod_liq_total:.2f}"
        # TODO: validar posição contra XSD oficial da NT 2026.008 na homologação (tpAmb=2).
        icms_tot_elem.insert(posicao_total, total_liquido_elem)

    return v_prod_liq_total


def generate_nfe_xml_nfelib(
    emitente_data: Dict[str, Any],
    destinatario_data: Dict[str, Any],
    items: list,
    form_data: Dict[str, Any],
    numero_nfe: int,
    certificado_data: Dict[str, Any],
    include_resp_tec: bool = True
) -> str:
    """
    Gera XML da NFe usando a biblioteca nfelib
    
    Args:
        emitente_data: Dados do emitente
        destinatario_data: Dados do destinatário
        items: Lista de itens da nota
        form_data: Dados do formulário (série, natureza, etc)
        numero_nfe: Número da NFe
        certificado_data: Dados do certificado (não usado aqui, assinatura feita depois)
        
    Returns:
        str: XML da NFe gerado e validado pelo nfelib
    """
    
    print("🚀 [NFELIB] Iniciando geração de XML com biblioteca nfelib")
    
    # tpAmb padrão SEFAZ: 1=Produção, 2=Homologação
    tp_amb = form_data.get('tpAmb', 2)  # Default: Homologação
    print(f"📋 [DEBUG] Ambiente: {'PRODUÇÃO' if tp_amb == 1 else 'HOMOLOGAÇÃO'} (tpAmb={tp_amb})")
    
    if tp_amb == 2:  # Homologação
        print(f"⚠️  [HOMOLOGAÇÃO] CNPJs reais podem ser rejeitados pela SEFAZ")
        print(f"⚠️  [HOMOLOGAÇÃO] Use CNPJ teste: 99999999000191 se houver rejeição")
    
    print(f"📋 [DEBUG] Emitente CNPJ: {emitente_data.get('cnpj', 'N/A')}")
    print(f"📋 [DEBUG] Emitente Razão: {emitente_data.get('razao_social', 'N/A')}")
    print(f"📋 [DEBUG] Destinatário CPF/CNPJ: {destinatario_data.get('cpf_cnpj', 'N/A')}")
    print(f"📋 [DEBUG] Destinatário Nome: {destinatario_data.get('nome', destinatario_data.get('nome_razao_social', 'N/A'))}")
    print(f"📋 [DEBUG] Número de itens: {len(items)}")
    
    # IMPORTANTE: NÃO substituir CNPJ em homologação - usar CNPJ real para corresponder ao certificado
    # A chave de acesso DEVE conter o CNPJ real do emitente (mesmo que seja homologação)
    emitente_data_copy = emitente_data.copy()
    if tp_amb == 2:
        print(f"⚠️  [HOMOLOGAÇÃO] Usando CNPJ real na chave de acesso: {emitente_data_copy.get('cnpj', '')}")
    
    # 1. Gerar data de emissão (usar timezone brasileiro BRT = UTC-3)
    from datetime import timezone as tz
    brt = tz(timedelta(hours=-3))
    
    # USAR data do form_data se fornecida, senão usar agora
    if form_data.get('dataEmissao'):
        try:
            # Parsear data do formulário (formato: 2026-01-27T16:22)
            data_str = form_data['dataEmissao']
            data_emissao = datetime.fromisoformat(data_str)
            # Adicionar timezone BRT se não tiver
            if data_emissao.tzinfo is None:
                data_emissao = data_emissao.replace(tzinfo=brt)
        except Exception as e:
            print(f"⚠️  Erro ao parsear dataEmissao '{form_data.get('dataEmissao')}': {e}, usando agora")
            data_emissao = datetime.now(brt)
    else:
        data_emissao = datetime.now(brt)
    
    # Remover microsegundos (apenas segundos como no XML aprovado)
    data_emissao = data_emissao.replace(microsecond=0)
    ano_vigencia_reforma = vigencia_reforma(data_emissao)
    print(f"[REFORMA] Vigência da emissão: {ano_vigencia_reforma}")

    # Evita rejeição/alerta por data de emissão futura.
    agora_brt = datetime.now(brt).replace(microsecond=0)
    if data_emissao > agora_brt:
        print(f"⚠️  [NFELIB] dhEmi futura ({data_emissao.isoformat()}); ajustando para horário atual BRT")
        data_emissao = agora_brt
    
    print(f"✅ [NFELIB] Data de emissão: {data_emissao.isoformat()}")
    
    # 2. Gerar chave de acesso (44 dígitos) - USA CNPJ REAL mesmo em homologação
    chave_acesso = gerar_chave_acesso(emitente_data_copy, form_data, numero_nfe, data_emissao)
    
    # 3. Gerar Id do infNFe (formato: "NFe" + chave de 44 dígitos)
    id_nfe = f"NFe{chave_acesso}"
    
    # 4. Criar IDE (identificação)
    # Determinar natureza da operação baseado no CFOP se não informada
    nat_op = (form_data.get('natOp') or '').strip()
    if not nat_op:
        # Mapear CFOP comum para natureza da operação
        cfop_primeiro_item = (items[0].get('cfop') or '') if items else ''
        if cfop_primeiro_item.startswith('5'):
            nat_op = 'VENDA DE MERCADORIA'
        elif cfop_primeiro_item.startswith('6'):
            nat_op = 'VENDA DE MERCADORIA PARA FORA DO ESTADO'
        else:
            nat_op = 'VENDA'
    
    print(f"📋 [DEBUG] Natureza Operação: '{nat_op}'")
    
    # Determinar idDest baseado no CFOP ou UF
    # 1=Operação interna, 2=Operação interestadual, 3=Operação com exterior
    cfop_primeiro_item = (items[0].get('cfop') or '') if items else ''
    uf_emitente = normalizar_uf(emitente_data.get('uf', 'SP'))
    uf_destinatario = normalizar_uf(
        destinatario_data.get('uf')
        or destinatario_data.get('estado')
        or destinatario_data.get('uf_destino')
        or 'SP'
    )

    if cfop_primeiro_item.startswith('7') or cfop_primeiro_item.startswith('3'):
        # CFOP 7xxx/3xxx = operação com exterior
        id_dest = "3"
    elif cfop_primeiro_item.startswith('2') or cfop_primeiro_item.startswith('6'):
        # CFOP 2xxx/6xxx = entrada/saída interestadual (prevalece sobre comparação de UF)
        id_dest = "2"
    elif uf_emitente != uf_destinatario:
        # UFs diferentes = operação interestadual
        id_dest = "2"
    else:
        # UFs iguais = operação interna
        id_dest = "1"
    
    print(f"📋 [DEBUG] idDest: {id_dest} (CFOP: {cfop_primeiro_item}, UF Emit: {uf_emitente}, UF Dest: {uf_destinatario})")

    # Auto-corrigir finNFe: se qualquer item usar CFOP de devolução, finNFe deve ser 4
    import re as _re
    _cfop_devol_pattern = _re.compile(r'^[1256](20[1-9]|21[0-9]|41[0-3]|553)$')
    _tem_cfop_devol = any(
        _cfop_devol_pattern.match((item.get('cfop') or '').strip())
        for item in items
    )
    fin_nfe_raw = str(form_data.get('finNFe', '1'))
    if _tem_cfop_devol and fin_nfe_raw != '4':
        fin_nfe_raw = '4'
        print(f"⚠️  [NFELIB] finNFe auto-corrigido para 4 (devolução) pelo CFOP dos itens")
    elif not _tem_cfop_devol and fin_nfe_raw == '4':
        # finNFe=4 sem CFOP de devolução também seria rejeitado
        fin_nfe_raw = '1'
        print(f"⚠️  [NFELIB] finNFe auto-corrigido para 1 — nenhum CFOP de devolução encontrado")

    # Extrair cDV (dígito verificador) da chave de acesso
    cdv = chave_acesso[-1]  # Último dígito da chave
    
    ide = Nfe.InfNfe.Ide(
        cUF=str(get_uf_ibge_code(emitente_data.get('uf', 'SP'))),
        cNF=form_data.get('codigo_numerico', str(abs(hash(str(numero_nfe))) % 100000000)).zfill(8)[:8],
        natOp=nat_op[:60],
        mod="55",
        serie=str(form_data.get('serie', '1')),
        nNF=str(numero_nfe),
        dhEmi=data_emissao.isoformat(),
        tpNF=str(form_data.get('tpNF', '1')),
        idDest=id_dest,  # Agora dinâmico baseado no CFOP e UF
        cMunFG=str(emitente_data.get('codigo_municipio', '3550308')),
        tpImp="1",
        tpEmis="1",
        cDV=cdv,  # Dígito verificador da chave de acesso
        tpAmb=str(form_data.get('tpAmb', 2)),
        finNFe=fin_nfe_raw,
        indFinal="1",
        indPres=form_data.get('indPres', "1"),
        indIntermed="0",
        procEmi="0",  # MANTIDO 0=Aplicação do contribuinte (correto para aplicação própria)
        verProc="EmiteMax_1.0"
    )

    # NFref: obrigatório para NF-e de devolução (finNFe=4)
    if fin_nfe_raw == '4':
        chave_ref = (form_data.get('chave_nfe_ref') or '').strip().replace(' ', '')
        if chave_ref and len(chave_ref) == 44 and chave_ref.isdigit():
            ide.NFref.append(Nfe.InfNfe.Ide.Nfref(refNFe=chave_ref))
            print(f"✅ [NFELIB] NFref adicionado: {chave_ref}")
        else:
            print(f"⚠️  [NFELIB] finNFe=4 (devolução) mas chave_nfe_ref ausente ou inválida: '{chave_ref}'")

    print("✅ [NFELIB] IDE criado")
    
    # 5. Criar enderEmit
    cod_mun_emit = str(emitente_data.get('codigo_municipio', '3550308'))
    nome_mun_emit = normalizar_municipio(
        cod_mun_emit,
        emitente_data.get('municipio') or emitente_data.get('nome_municipio') or 'SAO PAULO'
    )
    
    # Telefone do emitente: apenas dígitos, 6-14 chars conforme schema NFe
    _fone_emit_raw = (emitente_data.get('telefone') or emitente_data.get('fone') or '').strip()
    _fone_emit = ''.join(ch for ch in _fone_emit_raw if ch.isdigit())[:14]

    ender_emit = TenderEmi(
        xLgr=(emitente_data.get('logradouro') or 'RUA TESTE').strip()[:60],
        nro=str(emitente_data.get('numero') or '0').strip()[:60],
        xCpl=(emitente_data.get('complemento') or '').strip()[:60] if emitente_data.get('complemento') else None,
        xBairro=(emitente_data.get('bairro') or 'CENTRO').strip()[:60],
        cMun=cod_mun_emit,
        xMun=nome_mun_emit,
        UF=uf_emitente,
        CEP=limpar_cnpj_cpf(emitente_data.get('cep') or '00000000'),
        cPais="1058",
        xPais="BRASIL",
        fone=_fone_emit if len(_fone_emit) >= 6 else None
    )
    
    # 6. Criar EMIT (emitente) com endereço
    cnpj_emitente = limpar_cnpj_cpf(emitente_data.get('cnpj', ''))
    if not cnpj_emitente or cnpj_emitente == '0' * 14:
        raise ValueError(f"CNPJ do emitente inválido ou vazio: {emitente_data.get('cnpj', 'N/A')}")
    cnpj_emitente = cnpj_emitente.zfill(14)
    
    # IMPORTANTE: Em homologação, usar o CNPJ REAL para que corresponda ao certificado digital
    # O CNPJ do certificado DEVE corresponder ao CNPJ do emitente no XML
    print(f"✅ [NFELIB] CNPJ Emitente: {cnpj_emitente} ({len(cnpj_emitente)} dígitos)")
    if tp_amb == 2:
        print(f"⚠️  [HOMOLOGAÇÃO] Usando CNPJ real para corresponder ao certificado digital")
    
    # Buscar IE (pode estar como 'ie' ou 'inscricao_estadual')
    ie_emitente = (emitente_data.get('ie') or emitente_data.get('inscricao_estadual') or '').strip()
    if not ie_emitente:
        raise ValueError("Inscrição Estadual do emitente é obrigatória")
    
    # IMPORTANTE: Em homologação, usar IE REAL do emitente!
    # A SEFAZ valida a IE mesmo em ambiente de homologação
    print(f"📋 [NFELIB] IE Emitente: {ie_emitente}")
    
    # Buscar regime tributário (pode estar em diferentes campos)
    crt_emitente = str(emitente_data.get('regime_tributario') or 
                      emitente_data.get('regime_tributario_id') or '1')

    emit = Nfe.InfNfe.Emit(
        CNPJ=cnpj_emitente,
        xNome=(emitente_data.get('razao_social') or '').strip()[:60],
        xFant=emitente_data.get('nome_fantasia', '').strip()[:60] if emitente_data.get('nome_fantasia') else None,
        enderEmit=ender_emit,
        IE=ie_emitente,
        CRT=crt_emitente
    )
    
    print("✅ [NFELIB] EMIT criado")
    
    # 7. Criar enderDest
    cod_mun_dest = str(destinatario_data.get('codigo_municipio', '3550308'))
    nome_mun_dest = normalizar_municipio(
        cod_mun_dest,
        destinatario_data.get('municipio') or destinatario_data.get('nome_municipio') or 'SAO PAULO'
    )
    
    # Telefone do destinatário: apenas dígitos, 6-14 chars conforme schema NFe
    _fone_dest_raw = (destinatario_data.get('telefone') or '').strip()
    _fone_dest = ''.join(ch for ch in _fone_dest_raw if ch.isdigit())[:14]
    
    ender_dest = Tendereco(
        xLgr=(destinatario_data.get('logradouro') or 'RUA TESTE').strip()[:60],
        nro=str(destinatario_data.get('numero') or '0').strip()[:60],
        xCpl=destinatario_data.get('complemento', '').strip()[:60] if destinatario_data.get('complemento') else None,
        xBairro=(destinatario_data.get('bairro') or 'CENTRO').strip()[:60],
        cMun=cod_mun_dest,
        xMun=nome_mun_dest,
        UF=uf_destinatario,
        CEP=limpar_cnpj_cpf(destinatario_data.get('cep', '00000000')),
        cPais="1058",
        xPais="BRASIL",
        fone=_fone_dest if len(_fone_dest) >= 6 else None
    )
    
    # 8. Criar DEST (destinatário) com endereço
    dest_cpf_cnpj = limpar_cnpj_cpf(destinatario_data.get('cpf_cnpj', ''))
    if not dest_cpf_cnpj or dest_cpf_cnpj == '0' * 11:
        raise ValueError(f"CPF/CNPJ do destinatário inválido ou vazio: {destinatario_data.get('cpf_cnpj', 'N/A')}")
    
    # Garantir 14 dígitos para CNPJ ou 11 para CPF
    if len(dest_cpf_cnpj) <= 11:
        dest_cpf_cnpj = dest_cpf_cnpj.zfill(11)
    else:
        dest_cpf_cnpj = dest_cpf_cnpj.zfill(14)
    
    # IMPORTANTE: Em homologação, usar CPF/CNPJ REAIS
    print(f"✅ [NFELIB] CPF/CNPJ Destinatário: {dest_cpf_cnpj} ({len(dest_cpf_cnpj)} dígitos)")
    if tp_amb == 2:
        print(f"⚠️  [HOMOLOGAÇÃO] Usando CPF/CNPJ real do destinatário")
    
    # Nome pode estar em 'nome' ou 'nome_razao_social'
    nome_dest = (destinatario_data.get('nome') or 
                destinatario_data.get('nome_razao_social') or '').strip()
    if not nome_dest:
        raise ValueError("Nome do destinatário é obrigatório")
    
    # Remover acentos e caracteres especiais (ASSOCIAÇÃO → ASSOCIACAO)
    nome_dest = remover_acentos(nome_dest).strip()
    
    # HOMOLOGAÇÃO: Nome do destinatário deve ser padronizado pela SEFAZ
    if tp_amb == 2:
        nome_dest_original = nome_dest
        nome_dest = "NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL"
        print(f"⚠️  [HOMOLOGAÇÃO] Nome Destinatário substituído: {nome_dest_original} → {nome_dest}")
    
    # Determinar indIEDest baseado em IE e tipo de documento
    # 1=Contribuinte ICMS, 2=Contribuinte isento, 9=Não contribuinte
    ie_dest = (destinatario_data.get('ie') or destinatario_data.get('inscricao_estadual', '') or '').strip()
    # Ler indicador NF-e do destinatário: C=contribuinte, E=isento, N=não contribuinte
    ie_indicador_nfe = (destinatario_data.get('ie_indicador_nfe') or '').strip().upper()
    # Normalizar IE para evitar rejeicao por mascara/texto nao numerico
    ie_dest_digits = ''.join(ch for ch in ie_dest if ch.isdigit())
    ie_dest_upper = ie_dest.upper()
    ie_placeholder = ie_dest_digits in {'', '0', '00', '000', '0000', '00000', '000000', '0000000', '00000000', '000000000', '0000000000', '00000000000', '000000000000', '0000000000000', '00000000000000'}

    if ie_dest_upper in {'ISENTO', 'ISENTA'}:
        ie_dest_norm = 'ISENTO'
    elif ie_dest_digits and not ie_placeholder:
        ie_dest_norm = ie_dest_digits
    else:
        ie_dest_norm = ''

    # Validação básica de tamanho: descartar IE inválida para evitar Rejeição 210.
    if ie_dest_norm not in {'', 'ISENTO'} and not ie_valida_basica_por_uf(ie_dest_norm, uf_destinatario):
        print(
            f"⚠️  [NFELIB] IE do destinatario com tamanho inválido para UF {uf_destinatario}: "
            f"'{ie_dest_norm}' — descartando para evitar Rejeição 210 (indIEDest→9)."
        )
        ie_dest_norm = ''  # descarta: indIEDest será 9 (não contribuinte)

    if len(dest_cpf_cnpj) == 11:  # CPF = pessoa física = não contribuinte
        ind_ie_dest = "9"
    elif ie_indicador_nfe == 'N':
        # CNPJ explicitamente marcado como não contribuinte no cadastro
        ind_ie_dest = "9"
        ie_dest_norm = ''
        print(f"⚠️  [NFELIB] CNPJ com ie_indicador=N → indIEDest=9 (não contribuinte)")
    elif ie_dest_norm and ie_dest_norm != 'ISENTO':
        ind_ie_dest = "1"  # Contribuinte ICMS com IE válida
    else:
        # IE ausente ou "ISENTO": não contribuinte (9), sem tag <IE>
        ind_ie_dest = "9"
        ie_dest_norm = ''
        print(f"⚠️  [NFELIB] IE='{ie_dest_norm}' / indicador='{ie_indicador_nfe}' → indIEDest=9 (não contribuinte)")
    
    print(f"✅ [NFELIB] Nome Destinatário: {nome_dest}, indIEDest: {ind_ie_dest}")
    
    dest_kwargs = {
        'xNome': nome_dest[:60],
        'enderDest': ender_dest,
        'indIEDest': ind_ie_dest
    }
    
    # Adicionar IE: obrigatória para contribuinte (1) e isento (2="ISENTO")
    if ind_ie_dest == "1":  # NT 2024/007: omitir <IE> para isento e nao-contribuinte
        dest_kwargs['IE'] = ie_dest_norm
    
    if len(dest_cpf_cnpj) == 11:
        dest_kwargs['CPF'] = dest_cpf_cnpj
    elif len(dest_cpf_cnpj) == 14:
        dest_kwargs['CNPJ'] = dest_cpf_cnpj
        
    dest = Nfe.InfNfe.Dest(**dest_kwargs)
    
    print("✅ [NFELIB] DEST criado")
    
    # 9. Criar DET (itens)
    det_list = []
    v_prod_total = Decimal('0')
    v_nf_total = Decimal('0')
    v_bc_icms_total = Decimal('0')
    v_icms_total = Decimal('0')
    v_pis_total = Decimal('0')
    v_cofins_total = Decimal('0')
    v_ipi_total = Decimal('0')  # Totalizador IPI
    
    # Totalizadores IBS/CBS
    v_bc_ibs_cbs_total = Decimal('0')
    v_ibs_uf_total = Decimal('0')
    v_ibs_mun_total = Decimal('0')
    v_ibs_total = Decimal('0')
    v_cbs_total = Decimal('0')
    itens_ibs_cbs = []  # Para armazenar dados IBS/CBS de cada item

    # Totalizadores DIFAL (EC 87/2015)
    v_fcp_uf_dest_total = Decimal('0')
    v_icms_uf_dest_total = Decimal('0')
    v_icms_uf_remet_total = Decimal('0')

    # Conexão única para IBS/CBS (evita esgotar o pool com uma query por item)
    _db_ibs_cbs = None
    _ibs_cbs_cache = {}  # cache: classificacao_id_int -> ibs_cbs_data (alíquotas fixas por classificação)
    try:
        from database.connection import get_db as _get_db_ibs
        _db_ibs_cbs = next(_get_db_ibs())
    except Exception as _e:
        print(f"  [AVISO] Não foi possível abrir conexão para IBS/CBS: {_e}")

    for idx, item in enumerate(items, start=1):
        print(f"📦 [ITEM {idx}] Dados recebidos:")
        print(f"   - codigo_produto: {item.get('codigo_produto')}")
        print(f"   - codigo: {item.get('codigo')}")
        print(f"   - descricao: {item.get('descricao')}")
        print(f"   - Keys disponíveis: {list(item.keys())}")
        
        # Formatar valores com casas decimais corretas
        quantidade = _decimal_from_item(item, 'quantidade', '1', idx)
        valor_unitario = _decimal_from_item(item, 'valor_unitario', '0', idx)
        valor_total = _decimal_from_item(item, 'valor_total', '0', idx)
        
        # Quantidade: até 4 casas decimais (padrão NFe)
        qcom_str = f"{quantidade:.4f}"
        # Valor unitário: até 10 casas decimais (padrão NFe)
        vuncom_str = f"{valor_unitario:.4f}"
        # Valor total: 2 casas decimais
        vprod_str = f"{valor_total:.2f}"
        
        # Produto
        # ✅ CORREÇÃO: Aceitar 'codigo_produto' ou 'codigo' para compatibilidade
        codigo_prod = item.get('codigo_produto') or item.get('codigo') or str(idx)
        descricao_prod = item.get('descricao') or 'PRODUTO SEM DESCRIÇÃO'
        
        cfop_item = str(item.get('cfop') or '5102').strip()
        if uf_emitente == uf_destinatario and cfop_item.startswith('6'):
            cfop_corrigido = f"5{cfop_item[1:]}"
            print(f"⚠️  [NFELIB] CFOP {cfop_item} corrigido para {cfop_corrigido} (UFs iguais)")
            cfop_item = cfop_corrigido
        elif uf_emitente != uf_destinatario and cfop_item.startswith('5'):
            cfop_corrigido = f"6{cfop_item[1:]}"
            print(f"⚠️  [NFELIB] CFOP {cfop_item} corrigido para {cfop_corrigido} (UFs diferentes)")
            cfop_item = cfop_corrigido

        prod = Nfe.InfNfe.Det.Prod(
            cProd=str(codigo_prod).strip()[:60],
            cEAN=(item.get('ean') or 'SEM GTIN').strip(),
            xProd=descricao_prod.strip()[:120],
            NCM=(item.get('ncm') or '00000000').strip(),
            CFOP=cfop_item,
            uCom=(item.get('unidade') or 'UN').strip()[:6],
            qCom=qcom_str,
            vUnCom=vuncom_str,
            vProd=vprod_str,
            cEANTrib=item.get('ean', 'SEM GTIN'),
            uTrib=item.get('unidade', 'UN')[:6],
            qTrib=qcom_str,
            vUnTrib=vuncom_str,
            indTot="1"
        )
        
        v_prod_total += _decimal_from_item(item, 'valor_total', '0.00', idx)
        
        # VERIFICAR CRT DO EMITENTE para usar CST ou CSOSN
        crt_int = int(crt_emitente) if crt_emitente.isdigit() else 1
        usar_csosn = crt_int in [1, 2]  # 1=Simples Nacional, 2=SN Sublimite
        
        print(f"  [NFELIB] Item {idx} - CRT: {crt_int}, Usar CSOSN: {usar_csosn}")
        
        # Buscar CST ou CSOSN do item
        cst_item = item.get('cst_icms') or item.get('cst')
        csosn_item = item.get('csosn_icms') or item.get('csosn')
        cfop = cfop_item
        
        # DECISÃO: CST ou CSOSN baseado no CRT
        icms_uf_dest = None  # DIFAL (EC 87/2015) – definido no bloco regime normal se aplicável
        cbenef_resolvido = ''
        if usar_csosn:
            # SIMPLES NACIONAL - usar CSOSN
            if not csosn_item:
                # Determinar CSOSN automaticamente baseado no CFOP
                if cfop in ('5102', '6102', '5405', '6405'):
                    csosn_item = '102'  # SN sem crédito
                elif cfop in ('5103', '6103', '5403', '6403'):
                    csosn_item = '500'  # ICMS ST
                else:
                    csosn_item = '102'  # Padrão
            
            print(f"  [NFELIB] Item {idx} - CFOP {cfop} → CSOSN {csosn_item}")
            
            # Buscar dados de ICMS para Simples Nacional
            sn_origem = str(item.get('origem', '0'))
            sn_aliq = _decimal_from_item(item, 'aliquota_icms', '0', idx)
            sn_bc_raw = item.get('bc_icms', valor_total)
            try:
                sn_bc = Decimal(_normalizar_valor_decimal(sn_bc_raw, str(valor_total)))
            except Exception:
                sn_bc = valor_total
            if sn_bc <= 0 and csosn_item not in ('500',):
                sn_bc = valor_total
            sn_vICMS = (sn_bc * sn_aliq / Decimal('100')).quantize(Decimal('0.01')) if sn_aliq > 0 else Decimal('0')
            sn_modal_bc = str(item.get('modalidade_bc_icms') or '3').strip() or '3'
            if sn_modal_bc not in {'0', '1', '2', '3'}:
                sn_modal_bc = '3'

            # Criar ICMS com CSOSN
            if csosn_item == '500':
                # Pegar campos ICMS ST do formulário
                v_bc_st_ret = _decimal_from_item(item, 'vBCSTRet', '0', idx)
                p_st = _decimal_from_item(item, 'pST', '0', idx)
                v_icms_substituto = _decimal_from_item(item, 'vICMSSubstituto', '0', idx)
                v_icms_st_ret = _decimal_from_item(item, 'vICMSSTRet', '0', idx)
                
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn500(
                    orig=sn_origem,
                    CSOSN="500",
                    vBCSTRet=f"{v_bc_st_ret:.2f}",
                    pST=f"{p_st:.2f}",
                    vICMSSubstituto=f"{v_icms_substituto:.2f}",
                    vICMSSTRet=f"{v_icms_st_ret:.2f}"
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN500=icms_sn)
            elif csosn_item == '900':
                # CSOSN 900 = Outros — usado em devolução SN com ICMS a recuperar
                # Suporta modBC/vBC/pICMS/vICMS + pCredSN/vCredICMSSN
                sn900_params = {
                    'orig': sn_origem,
                    'CSOSN': '900',
                    'modBC': sn_modal_bc,
                    'vBC': f"{sn_bc:.2f}",
                    'pICMS': f"{sn_aliq:.2f}",
                    'vICMS': f"{sn_vICMS:.2f}",
                }
                if sn_aliq > 0:
                    sn900_params['pCredSN'] = f"{sn_aliq:.2f}"
                    sn900_params['vCredICMSSN'] = f"{sn_vICMS:.2f}"
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn900(**sn900_params)
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN900=icms_sn)
                v_bc_icms_total += sn_bc
                v_icms_total += sn_vICMS
                print(f"  [NFELIB] CSOSN 900 vBC={sn_bc:.2f} pICMS={sn_aliq:.2f} vICMS={sn_vICMS:.2f}")
            elif csosn_item == '103':
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn102(
                    orig=sn_origem,
                    CSOSN="103"
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN102=icms_sn)
            elif csosn_item == '101':
                sn101_params = {'orig': sn_origem, 'CSOSN': '101'}
                if sn_aliq > 0:
                    sn101_params['pCredSN'] = f"{sn_aliq:.2f}"
                    sn101_params['vCredICMSSN'] = f"{sn_vICMS:.2f}"
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn101(**sn101_params)
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN101=icms_sn)
            else:  # 102, 400, outros sem valor de ICMS
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn102(
                    orig=sn_origem,
                    CSOSN=csosn_item if csosn_item in ('102', '103', '300', '400') else '102'
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN102=icms_sn)
            
            # PIS/COFINS não tributado para SN
            pis_nt = Nfe.InfNfe.Det.Imposto.Pis.Pisnt(CST="07")
            pis = Nfe.InfNfe.Det.Imposto.Pis(PISNT=pis_nt)
            cofins_nt = Nfe.InfNfe.Det.Imposto.Cofins.Cofinsnt(CST="07")
            cofins = Nfe.InfNfe.Det.Imposto.Cofins(COFINSNT=cofins_nt)
            
        else:
            # REGIME NORMAL - usar CST
            if not cst_item:
                cst_item = '20'  # CST 20 = Redução de BC (padrão seguro)
            
            print(f"  [NFELIB] Item {idx} - CFOP {cfop} → CST {cst_item}")

            # Regras cBenef-SP para CSTs com redução/isenção
            cbenef_resolvido = _resolver_cbenef_sp(
                item=item,
                idx=idx,
                cst_item=cst_item,
                uf_emitente=uf_emitente,
                data_emissao=data_emissao,
            )
            if cbenef_resolvido:
                item['_cbenef_resolvido'] = cbenef_resolvido
            
            # Buscar dados tributários do item
            origem = item.get('origem', '0')
            aliquota_icms = _decimal_from_item(item, 'aliquota_icms', '7', idx)
            reducao_bc = _decimal_from_item(item, 'reducao_base_icms', '0', idx)
            bc_icms_raw = item.get('bc_icms', valor_total)
            try:
                bc_icms = Decimal(_normalizar_valor_decimal(bc_icms_raw, str(valor_total)))
            except Exception:
                bc_icms = valor_total
            valor_icms = _decimal_from_item(item, 'valor_icms', '0', idx)
            modalidade_bc = str(item.get('modalidade_bc_icms') or '3').strip() or '3'
            modalidade_bc_st = str(item.get('modalidade_bc_st') or '4').strip() or '4'

            # Evita gerar tags vazias como <modBC/>, que quebram o schema da SEFAZ.
            if modalidade_bc not in {'0', '1', '2', '3'}:
                print(f"⚠️  [NFELIB] modalidade_bc_icms inválida '{modalidade_bc}' no item {idx}; usando padrão 3")
                modalidade_bc = '3'
            if modalidade_bc_st not in {'0', '1', '2', '3', '4', '5'}:
                print(f"⚠️  [NFELIB] modalidade_bc_st inválida '{modalidade_bc_st}' no item {idx}; usando padrão 4")
                modalidade_bc_st = '4'

            # Evita rejeição SEFAZ por alíquota de ICMS acima do permitido em operação interestadual.
            if id_dest == '2':
                aliq_max = obter_aliquota_maxima_icms_interestadual(uf_emitente, uf_destinatario, origem)
                if aliq_max > 0 and aliquota_icms > aliq_max:
                    print(
                        f"⚠️  [NFELIB] Item {idx} pICMS {aliquota_icms:.2f}% acima do permitido "
                        f"para interestadual ({aliq_max:.2f}%). Ajustando automaticamente."
                    )
                    aliquota_icms = aliq_max
                    # Recalcular vICMS com a alíquota corrigida para evitar inconsistência
                    if bc_icms > 0:
                        valor_icms = (bc_icms * aliquota_icms / Decimal('100')).quantize(Decimal('0.01'))
            
            # Criar ICMS com CST apropriado
            if cst_item == '00':
                # Tributada integralmente
                if bc_icms <= 0 and valor_total > 0:
                    print(f"⚠️  [NFELIB] Item {idx} CST 00 com vBC<=0; ajustando vBC para valor do item")
                    bc_icms = valor_total

                if valor_icms <= 0 and bc_icms > 0 and aliquota_icms > 0:
                    valor_icms = (bc_icms * aliquota_icms / Decimal('100')).quantize(Decimal('0.01'))

                icms_obj = Nfe.InfNfe.Det.Imposto.Icms.Icms00(
                    orig=origem,
                    CST="00",
                    modBC=modalidade_bc,
                    vBC=f"{bc_icms:.2f}",
                    pICMS=f"{aliquota_icms:.2f}",
                    vICMS=f"{valor_icms:.2f}"
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMS00=icms_obj)
                v_bc_icms_total += bc_icms
                v_icms_total += valor_icms
            elif cst_item == '20':
                # Redução de base de cálculo
                motivo_deson = item.get('motivo_desoneracao_icms')
                # cBenef será adicionado manualmente ao XML (nfelib não suporta)
                icms20_params = {
                    'orig': origem,
                    'CST': "20",
                    'modBC': modalidade_bc,
                    'pRedBC': f"{reducao_bc:.2f}",
                    'vBC': f"{bc_icms:.2f}",
                    'pICMS': f"{aliquota_icms:.2f}",
                    'vICMS': f"{valor_icms:.2f}"
                }
                # NÃO adicionar cBenef aqui - nfelib não suporta
                # if cbenef:
                #     icms20_params['cBenef'] = cbenef
                # Adicionar motDesICMS se houver desoneração
                if motivo_deson:
                    icms20_params['motDesICMS'] = motivo_deson
                
                icms_obj = Nfe.InfNfe.Det.Imposto.Icms.Icms20(**icms20_params)
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMS20=icms_obj)
                v_bc_icms_total += bc_icms
                v_icms_total += valor_icms
            elif cst_item in ['40', '41', '50']:
                # Isenta, não tributada ou suspensão
                motivo_deson = item.get('motivo_desoneracao_icms')
                icms40_params = {
                    'orig': origem,
                    'CST': cst_item
                }
                # NÃO adicionar cBenef aqui - nfelib não suporta
                # if cbenef:
                #     icms40_params['cBenef'] = cbenef
                # Adicionar motDesICMS se houver desoneração (obrigatório para alguns casos)
                if motivo_deson:
                    icms40_params['motDesICMS'] = motivo_deson
                
                icms_obj = Nfe.InfNfe.Det.Imposto.Icms.Icms40(**icms40_params)
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMS40=icms_obj)
            else:
                # Fallback: usar CST 20
                icms_obj = Nfe.InfNfe.Det.Imposto.Icms.Icms20(
                    orig=origem,
                    CST="20",
                    modBC=modalidade_bc,
                    pRedBC=f"{reducao_bc:.2f}",
                    vBC=f"{bc_icms:.2f}",
                    pICMS=f"{aliquota_icms:.2f}",
                    vICMS=f"{valor_icms:.2f}"
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMS20=icms_obj)
                v_bc_icms_total += bc_icms
                v_icms_total += valor_icms
            
            # DIFAL (EC 87/2015): grupo ICMSUFDest obrigatório SOMENTE para:
            # interestadual + consumidor final NÃO contribuinte (indIEDest=9) + regime normal
            # Para contribuinte (indIEDest=1) ou isento (indIEDest=2) NÃO se aplica.
            if id_dest == '2' and crt_int != 1 and ind_ie_dest == "9":
                aliq_interna_dest = obter_aliquota_interna_icms_destino(uf_destinatario)
                aliq_fcp_dest = obter_aliquota_fcp_uf_dest(uf_destinatario)
                aliq_inter = aliquota_icms  # já ajustada para o máximo interestadual
                aliq_partilha = Decimal('100')
                v_bc_difal = bc_icms if bc_icms > 0 else valor_total
                v_fcp_item = (v_bc_difal * aliq_fcp_dest / Decimal('100')).quantize(Decimal('0.01'))
                v_icms_uf_dest_item = (
                    (v_bc_difal * aliq_interna_dest / Decimal('100') - v_bc_difal * aliq_inter / Decimal('100'))
                    * aliq_partilha / Decimal('100')
                ).quantize(Decimal('0.01'))
                v_icms_uf_remet_item = Decimal('0.00')
                icms_uf_dest = Nfe.InfNfe.Det.Imposto.Icmsufdest(
                    vBCUFDest=f"{v_bc_difal:.2f}",
                    vBCFCPUFDest=f"{v_bc_difal:.2f}",
                    pFCPUFDest=f"{aliq_fcp_dest:.2f}",
                    pICMSUFDest=f"{aliq_interna_dest:.2f}",
                    pICMSInter=f"{aliq_inter:.2f}",
                    pICMSInterPart=f"{aliq_partilha:.2f}",
                    vFCPUFDest=f"{v_fcp_item:.2f}",
                    vICMSUFDest=f"{v_icms_uf_dest_item:.2f}",
                    vICMSUFRemet=f"{v_icms_uf_remet_item:.2f}"
                )
                v_fcp_uf_dest_total += v_fcp_item
                v_icms_uf_dest_total += v_icms_uf_dest_item
                v_icms_uf_remet_total += v_icms_uf_remet_item
                print(
                    f"  [DIFAL] Item {idx}: UF={uf_destinatario}, pICMSUFDest={aliq_interna_dest:.2f}%,"
                    f" pICMSInter={aliq_inter:.2f}%, vICMSUFDest={v_icms_uf_dest_item:.2f},"
                    f" vFCPUFDest={v_fcp_item:.2f}"
                )

            # PIS/COFINS para regime normal
            cst_pis = item.get('cst_pis') or '01'
            cst_cofins = item.get('cst_cofins') or '01'
            print(f"[DEBUG-PIS] Item {idx}: cst_pis recebido='{item.get('cst_pis')}', final='{cst_pis}'")
            print(f"[DEBUG-COFINS] Item {idx}: cst_cofins recebido='{item.get('cst_cofins')}', final='{cst_cofins}'")
            # Garantir que CST nunca seja vazio
            if not cst_pis or cst_pis == '':
                cst_pis = '01'
            if not cst_cofins or cst_cofins == '':
                cst_cofins = '01'
            aliq_pis = _decimal_from_item(item, 'aliquota_pis', '1.65', idx)
            aliq_cofins = _decimal_from_item(item, 'aliquota_cofins', '7.6', idx)
            
            # PIS
            if cst_pis in ['01', '02']:
                pis_aliq = Nfe.InfNfe.Det.Imposto.Pis.Pisaliq(
                    CST=cst_pis,
                    vBC=f"{valor_total:.2f}",
                    pPIS=f"{aliq_pis:.2f}",
                    vPIS=f"{(valor_total * aliq_pis / 100):.2f}"
                )
                pis = Nfe.InfNfe.Det.Imposto.Pis(PISAliq=pis_aliq)
                v_pis_total += (valor_total * aliq_pis / 100)
            else:
                pis_nt = Nfe.InfNfe.Det.Imposto.Pis.Pisnt(CST=cst_pis)
                pis = Nfe.InfNfe.Det.Imposto.Pis(PISNT=pis_nt)
            
            # COFINS
            if cst_cofins in ['01', '02']:
                cofins_aliq = Nfe.InfNfe.Det.Imposto.Cofins.Cofinsaliq(
                    CST=cst_cofins,
                    vBC=f"{valor_total:.2f}",
                    pCOFINS=f"{aliq_cofins:.2f}",
                    vCOFINS=f"{(valor_total * aliq_cofins / 100):.2f}"
                )
                cofins = Nfe.InfNfe.Det.Imposto.Cofins(COFINSAliq=cofins_aliq)
                v_cofins_total += (valor_total * aliq_cofins / 100)
            else:
                cofins_nt = Nfe.InfNfe.Det.Imposto.Cofins.Cofinsnt(CST=cst_cofins)
                cofins = Nfe.InfNfe.Det.Imposto.Cofins(COFINSNT=cofins_nt)
        
        # IPI - Imposto sobre Produtos Industrializados
        ipi = None
        cst_ipi = item.get('cst_ipi')
        aliq_ipi = _decimal_from_item(item, 'aliquota_ipi', '0', idx)
        
        if cst_ipi:
            if cst_ipi in ['00', '49', '50', '99'] and aliq_ipi > 0:
                # IPI Tributado
                v_ipi = valor_total * aliq_ipi / 100
                ipi_trib = Nfe.InfNfe.Det.Imposto.Ipi.Ipitrib(
                    CST=cst_ipi,
                    vBC=f"{valor_total:.2f}",
                    pIPI=f"{aliq_ipi:.2f}",
                    vIPI=f"{v_ipi:.2f}"
                )
                ipi = Nfe.InfNfe.Det.Imposto.Ipi(IPITrib=ipi_trib)
                v_ipi_total += v_ipi
                print(f"  [IPI] Item {idx} - CST {cst_ipi}: BC R$ {valor_total:.2f}, Aliq {aliq_ipi:.2f}%, Valor R$ {v_ipi:.2f}")
            else:
                # IPI Não Tributado
                ipi_nt = Nfe.InfNfe.Det.Imposto.Ipi.Ipint(CST=cst_ipi)
                ipi = Nfe.InfNfe.Det.Imposto.Ipi(IPINT=ipi_nt)
                print(f"  [IPI] Item {idx} - CST {cst_ipi}: Não tributado")
        
        # IBS/CBS - Reforma Tributaria (obrigatorio quando classificacao_ibs_cbs_id presente)
        ibs_cbs_xml = None
        classificacao_ibs_cbs_id = item.get('classificacao_ibs_cbs_id')
        
        # DEBUG: Sempre mostrar se campo IBS/CBS foi recebido
        print(f"  [IBS/CBS] Item {idx} - CRT={crt_int}, classificacao_ibs_cbs_id='{classificacao_ibs_cbs_id}' (tipo: {type(classificacao_ibs_cbs_id).__name__})")
        
        # CRT=3 exige classificação IBS/CBS explícita no item.
        if crt_int == 3 and not classificacao_ibs_cbs_id:
            raise ValueError(f"Item {idx}: Classificação IBS/CBS obrigatória para CRT=3")
        if crt_int == 3 and classificacao_ibs_cbs_id and _db_ibs_cbs is not None:
            try:
                classificacao_id_int = int(classificacao_ibs_cbs_id)
                print(f"  [IBS/CBS] Item {idx} - Convertido para int: {classificacao_id_int}")

                # Calcular IBS/CBS usando conexão compartilhada
                ibs_cbs_data = calcular_ibs_cbs(
                    valor_total,
                    classificacao_id_int,
                    _db_ibs_cbs,
                    dhEmi=data_emissao,
                )

                # Gerar XML IBS/CBS
                ibs_cbs_xml = gerar_xml_ibscbs(ibs_cbs_data)

                # Acumular totais
                v_bc_ibs_cbs_total += Decimal(str(ibs_cbs_data['vBC']))
                v_ibs_uf_total += Decimal(str(ibs_cbs_data['vIBSUF']))
                v_ibs_mun_total += Decimal(str(ibs_cbs_data['vIBSMun']))
                v_ibs_total += Decimal(str(ibs_cbs_data['vIBS']))
                v_cbs_total += Decimal(str(ibs_cbs_data['vCBS']))

                itens_ibs_cbs.append(ibs_cbs_data)

                print(f"  [IBS/CBS] Item {idx} - Classificação {ibs_cbs_data['cClassTrib']}: "
                      f"IBS R$ {ibs_cbs_data['vIBS']:.2f}, CBS R$ {ibs_cbs_data['vCBS']:.2f}")

            except Exception as e:
                print(f"  [AVISO] Erro ao calcular IBS/CBS para item {idx}: {e}")
                # Continuar sem IBS/CBS se houver erro
        
        # vTotTrib - Valor aproximado dos tributos (Lei da Transparência)
        # Para Simples Nacional geralmente é 0.00
        v_tot_trib = "0.00"
        
        # Montar objeto Imposto com IPI se houver
        imposto_params = {
            'vTotTrib': v_tot_trib,
            'ICMS': icms,
            'PIS': pis,
            'COFINS': cofins
        }
        if ipi is not None:
            imposto_params['IPI'] = ipi
        if icms_uf_dest is not None:
            imposto_params['ICMSUFDest'] = icms_uf_dest
        
        imposto = Nfe.InfNfe.Det.Imposto(**imposto_params)
        
        det = Nfe.InfNfe.Det(
            nItem=str(idx),
            prod=prod,
            imposto=imposto
        )
        
        det_list.append(det)

    # Fechar conexão IBS/CBS após processar todos os itens
    if _db_ibs_cbs is not None:
        try:
            _db_ibs_cbs.close()
        except Exception:
            pass

    # Calcular valor total da NFe conforme composição fiscal
    # vNF = vProd - vDesc + vFrete + vSeg + vOutro + vII + vIPI + vST + vFCPST + vFCPSTRet + vIPIDevol
    def _to_decimal(value, default='0.00'):
        """Converte valor para Decimal tratando vírgula, None e strings inválidas."""
        try:
            v = str(value).strip().replace(',', '.') if value is not None else default
            return Decimal(v if v else default)
        except Exception:
            return Decimal(default)

    v_frete = _to_decimal(form_data.get('vFrete'), '0.00')
    v_seg   = _to_decimal(form_data.get('vSeg'),   '0.00')
    v_desc  = _to_decimal(form_data.get('vDesc'),  '0.00')
    v_outro = _to_decimal(form_data.get('vOutro'), '0.00')
    v_ii    = _to_decimal(form_data.get('vII'),    '0.00')
    v_st = Decimal('0.00')
    v_fcpst = Decimal('0.00')
    v_fcpst_ret = Decimal('0.00')
    v_ipi_devol = Decimal('0.00')
    v_nf_total = (
        v_prod_total
        - v_desc
        + v_frete
        + v_seg
        + v_outro
        + v_ii
        + v_ipi_total
        + v_st
        + v_fcpst
        + v_fcpst_ret
        + v_ipi_devol
    )
    
    print(f"✅ [NFELIB] {len(det_list)} itens criados")
    print(f"💰 [NFELIB] Valores: Produtos={v_prod_total:.2f} + Frete={v_frete:.2f} + Seguro={v_seg:.2f} - Desconto={v_desc:.2f} = Total NFe={v_nf_total:.2f}")
    
    # 10. Criar TOTAL
    icms_tot = Nfe.InfNfe.Total.Icmstot(
        vBC=f"{v_bc_icms_total:.2f}",
        vICMS=f"{v_icms_total:.2f}",
        vICMSDeson="0.00",
        vFCPUFDest=f"{v_fcp_uf_dest_total:.2f}",
        vICMSUFDest=f"{v_icms_uf_dest_total:.2f}",
        vICMSUFRemet=f"{v_icms_uf_remet_total:.2f}",
        vFCP="0.00",
        vBCST="0.00",
        vST=f"{v_st:.2f}",
        vFCPST=f"{v_fcpst:.2f}",
        vFCPSTRet=f"{v_fcpst_ret:.2f}",
        vProd=f"{v_prod_total:.2f}",
        vFrete=f"{v_frete:.2f}",
        vSeg=f"{v_seg:.2f}",
        vDesc=f"{v_desc:.2f}",
        vII=f"{v_ii:.2f}",
        vIPI=f"{v_ipi_total:.2f}",
        vIPIDevol=f"{v_ipi_devol:.2f}",
        vPIS=f"{v_pis_total:.2f}",
        vCOFINS=f"{v_cofins_total:.2f}",
        vOutro=f"{v_outro:.2f}",
        vNF=f"{v_nf_total:.2f}",
        vTotTrib="0.00"  # Valor total aproximado dos tributos
    )
    
    total = Nfe.InfNfe.Total(ICMSTot=icms_tot)
    
    print("✅ [NFELIB] TOTAL criado")
    
    # 11. Criar TRANSP
    mod_frete = form_data.get('modFrete', '9')  # Modalidade do frete
    transp_dict = {'modFrete': mod_frete}
    
    # Adicionar transportadora se informada
    transportadora_nome = form_data.get('transportadoraNome', '').strip()
    print(f"[DEBUG-TRANSP] transportadoraNome: '{transportadora_nome}'")
    print(f"[DEBUG-TRANSP] modFrete: '{mod_frete}'")
    if transportadora_nome and mod_frete != '9':  # Se não for "sem frete"
        transporta_dict = {}
        
        # CNPJ ou CPF
        cnpj_cpf = form_data.get('transportadoraCnpjCpf', '').strip()
        print(f"[DEBUG-TRANSP] CNPJ/CPF: '{cnpj_cpf}'")
        if cnpj_cpf:
            if len(cnpj_cpf) == 14:
                transporta_dict['CNPJ'] = cnpj_cpf
            elif len(cnpj_cpf) == 11:
                transporta_dict['CPF'] = cnpj_cpf
        
        # Nome/Razão Social
        transporta_dict['xNome'] = transportadora_nome
        
        # Inscrição Estadual
        ie = form_data.get('transportadoraIE', '').strip()
        print(f"[DEBUG-TRANSP] IE: '{ie}'")
        if ie:
            transporta_dict['IE'] = ie
        
        # Endereço
        endereco = form_data.get('transportadoraEndereco', '').strip()
        print(f"[DEBUG-TRANSP] Endereço: '{endereco}'")
        if endereco:
            transporta_dict['xEnder'] = endereco
        
        # Município
        municipio = form_data.get('transportadoraMunicipio', '').strip()
        print(f"[DEBUG-TRANSP] Município: '{municipio}'")
        if municipio:
            transporta_dict['xMun'] = municipio
        
        # UF
        uf = form_data.get('transportadoraUF', '').strip()
        print(f"[DEBUG-TRANSP] UF: '{uf}'")
        if uf:
            transporta_dict['UF'] = uf
        
        print(f"[DEBUG-TRANSP] Dict final: {transporta_dict}")
        if transporta_dict:
            transp_dict['transporta'] = Nfe.InfNfe.Transp.Transporta(**transporta_dict)
    
    # Veículo
    placa = form_data.get('veiculoPlaca', '').strip()
    if placa:
        veiculo_dict = {'placa': placa}
        uf_veiculo = form_data.get('veiculoUF', '').strip()
        if uf_veiculo:
            veiculo_dict['UF'] = uf_veiculo
        transp_dict['veicTransp'] = Nfe.InfNfe.Transp.VeicTransp(**veiculo_dict)
    
    # Volumes
    qtd_vol = form_data.get('volumeQuantidade', '').strip()
    if qtd_vol:
        vol_dict = {}
        if qtd_vol:
            vol_dict['qVol'] = qtd_vol
        especie = form_data.get('volumeEspecie', '').strip()[:60]  # Limite de 60 caracteres
        print(f"[DEBUG-VOL] Espécie recebida do form: '{especie}' ({len(especie)} chars)")
        if especie:
            vol_dict['esp'] = especie
            print(f"[DEBUG-VOL] Espécie adicionada ao dict: '{vol_dict['esp']}'")
        marca = form_data.get('volumeMarca', '').strip()
        if marca:
            vol_dict['marca'] = marca
        numeracao = form_data.get('volumeNumeracao', '').strip()
        if numeracao:
            vol_dict['nVol'] = numeracao
        peso_bruto = form_data.get('volumePesoBruto', '').strip()
        if peso_bruto:
            vol_dict['pesoB'] = peso_bruto
        peso_liquido = form_data.get('volumePesoLiquido', '').strip()
        if peso_liquido:
            vol_dict['pesoL'] = peso_liquido
        
        if vol_dict:
            transp_dict['vol'] = [Nfe.InfNfe.Transp.Vol(**vol_dict)]
    
    transp = Nfe.InfNfe.Transp(**transp_dict)
    print("✅ [NFELIB] TRANSP criado com dados do formulário")
    
    # 12. Criar PAG
    forma_pag = str(form_data.get('formaPagamento') or '01').strip().zfill(2)
    # Para finNFe=4 (devolução) ou forma "Sem Pagamento", usar tPag=90 e vPag=0.00
    if fin_nfe_raw == '4' or forma_pag == '90':
        det_pag = Nfe.InfNfe.Pag.DetPag(
            indPag="0",
            tPag="90",
            vPag="0.00"
        )
    else:
        det_pag = Nfe.InfNfe.Pag.DetPag(
            indPag="0",
            tPag=forma_pag,
            vPag=f"{v_nf_total:.2f}"
        )
    
    pag = Nfe.InfNfe.Pag(detPag=[det_pag])
    
    print("✅ [NFELIB] PAG criado")
    
    # 13. Criar InfNFe completo com atributo Id
    inf_nfe = Nfe.InfNfe(
        versao="4.00",
        Id=id_nfe,
        ide=ide,
        emit=emit,
        dest=dest,
        det=det_list,
        total=total,
        transp=transp,
        pag=pag
    )
    
    print(f"✅ [NFELIB] InfNFe criado com Id={id_nfe}")
    
    # 14. Criar NFe
    nfe = Nfe(infNFe=inf_nfe)
    
    # 15. Gerar XML com namespace correto
    try:
        xml_string = nfe.to_xml(
            indent="",
            ns_map={None: "http://www.portalfiscal.inf.br/nfe"}
        )
        print(f"✅ [NFELIB] XML gerado: {len(xml_string)} caracteres")
        
        # CRÍTICO: Adicionar infRespTec e infAdic manualmente (nfelib não tem suporte nativo)
        from lxml import etree
        xml_tree = etree.fromstring(xml_string.encode('utf-8'))
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        
        # Localizar infNFe
        inf_nfe_elem = xml_tree.find('.//nfe:infNFe', ns)
        if inf_nfe_elem is not None:
            
            # REFORMA TRIBUTÁRIA: Adicionar IBS/CBS aos itens e totalizadores
            # Controlado pela flag HABILITAR_IBS_CBS em config/settings.py
            habilitar_ibs_cbs_emissao = HABILITAR_IBS_CBS
            if itens_ibs_cbs and habilitar_ibs_cbs_emissao:
                print(f"🏛️ [IBS/CBS] Adicionando tags aos {len(itens_ibs_cbs)} itens com classificação")
                print(f"⚠️  [IBS/CBS] Flag HABILITAR_IBS_CBS = {HABILITAR_IBS_CBS}")
                
                # Adicionar <IBSCBS> a cada <imposto> dos itens
                det_elements = xml_tree.findall('.//nfe:det', ns)
                for idx, (det_elem, ibs_cbs_data) in enumerate(zip(det_elements, itens_ibs_cbs), 1):
                    imposto_elem = det_elem.find('.//nfe:imposto', ns)
                    if imposto_elem is not None:
                        # Gerar XML IBS/CBS e parsear
                        ibs_cbs_xml_str = gerar_xml_ibscbs(ibs_cbs_data)
                        ibs_cbs_fragment = etree.fromstring(f'<root xmlns="http://www.portalfiscal.inf.br/nfe">{ibs_cbs_xml_str}</root>')
                        ibs_cbs_elem = ibs_cbs_fragment[0]  # Primeiro filho
                        
                        # Adicionar dentro de <imposto> (conforme XML de referencia)
                        imposto_elem.append(ibs_cbs_elem)
                        print(f"  [IBS/CBS] Item {idx} - Tag <IBSCBS> adicionada em imposto")
                
                # Adicionar <IBSCBSTot> aos totais
                total_elem = xml_tree.find('.//nfe:total/nfe:ICMSTot', ns)
                if total_elem is not None:
                    # Preparar dados dos totais
                    totais_ibs = {
                        'vBCTotal': float(v_bc_ibs_cbs_total),
                        'vIBSUF': float(v_ibs_uf_total),
                        'vIBSMun': float(v_ibs_mun_total),
                        'vIBS': float(v_ibs_total)
                    }
                    totais_cbs = {
                        'vCBS': float(v_cbs_total)
                    }
                    
                    # Gerar XML dos totalizadores
                    totais_xml_str = gerar_xml_totais_ibscbs(totais_ibs, totais_cbs)
                    totais_fragment = etree.fromstring(f'<root xmlns="http://www.portalfiscal.inf.br/nfe">{totais_xml_str}</root>')
                    
                    # Adicionar após ICMSTot
                    parent_total = total_elem.getparent()
                    for child in totais_fragment:
                        parent_total.append(child)
                    
                    print(f"  [IBS/CBS] Totalizadores adicionados: IBS R$ {v_ibs_total:.2f}, CBS R$ {v_cbs_total:.2f}")

            
            _injetar_valores_produto_liquido(xml_tree, items, ano_vigencia_reforma)
            det_elements = xml_tree.findall('.//nfe:det', ns)

            modelo = str(form_data.get('modelo') or form_data.get('mod') or '55').strip().zfill(2)
            pagamento_antecipado = (
                str(form_data.get('tpNFDebito') or '').strip() == '06'
                or str(form_data.get('tpOperGov') or '').strip() == '4'
            )
            if modelo != '65' and pagamento_antecipado:
                for det_elem, item in zip(det_elements, items):
                    icms_elem = det_elem.find('.//nfe:ICMS', ns)
                    if icms_elem is None:
                        continue
                    grupo_previsto = icms_elem.find('nfe:ICMSPrevistoPagtoAntecip', ns)
                    if grupo_previsto is None:
                        # TODO: validar posição contra XSD oficial da NT 2026.008 na homologação (tpAmb=2).
                        grupo_previsto = etree.SubElement(
                            icms_elem,
                            '{http://www.portalfiscal.inf.br/nfe}ICMSPrevistoPagtoAntecip',
                        )
                    valor_previsto = item.get('vICMSPrevisto')
                    if valor_previsto is None:
                        valores_icms = icms_elem.xpath(".//*[local-name()='vICMS']/text()")
                        valor_previsto = sum(
                            (Decimal(str(valor).replace(',', '.')) for valor in valores_icms),
                            Decimal('0.00'),
                        ) if valores_icms else Decimal('0.00')
                    valor_previsto = converter_para_decimal(valor_previsto, 2)
                    etree.SubElement(
                        grupo_previsto,
                        '{http://www.portalfiscal.inf.br/nfe}vICMSPrevisto',
                    ).text = f"{valor_previsto:.2f}"

            # ========== ADICIONAR cBenef MANUALMENTE (nfelib não suporta) ==========
            print(f"🔧 [cBenef] Verificando necessidade de adicionar cBenef manualmente...")
            for idx, item in enumerate(items, 1):
                cbenef = (item.get('_cbenef_resolvido') or _extrair_cbenef_item(item) or '').strip().upper()
                if cbenef:
                    print(f"  [cBenef] Item {idx} - Código: {cbenef}")
                    # Encontrar o elemento det correspondente
                    det_elem = xml_tree.find(f'.//nfe:det[@nItem="{idx}"]', ns)
                    if det_elem is not None:
                        # Encontrar grupo ICMS que suporta cBenef
                        target_elem = None
                        for grupo_icms in ('ICMS20', 'ICMS40', 'ICMS30', 'ICMS51', 'ICMS70', 'ICMS90'):
                            target_elem = det_elem.find(f'.//nfe:{grupo_icms}', ns)
                            if target_elem is not None:
                                break
                        if target_elem is not None:
                            # Adicionar <cBenef> após <CST>
                            cst_elem = target_elem.find('nfe:CST', ns)
                            if cst_elem is not None:
                                cbenef_elem = etree.Element('{http://www.portalfiscal.inf.br/nfe}cBenef')
                                cbenef_elem.text = cbenef
                                # Inserir após CST (posição 2, já que 0=orig, 1=CST)
                                cst_index = list(target_elem).index(cst_elem)
                                target_elem.insert(cst_index + 1, cbenef_elem)
                                print(f"  ✅ [cBenef] Item {idx} - <cBenef>{cbenef}</cBenef> adicionado")
            
            # IMPORTANTE: Adicionar infAdic ANTES de infRespTec (ordem correta do leiaute)
            inf_cpl_text = form_data.get('infCpl', '').strip()
            if inf_cpl_text:
                # Remover caracteres de controle que violam o XSD (CR, LF, TAB exceto espaços)
                # Permitir apenas espaços e quebras de linha simples
                inf_cpl_text = inf_cpl_text.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')
                # Remover múltiplos espaços
                inf_cpl_text = ' '.join(inf_cpl_text.split())
                
                # Criar infAdic com infCpl
                inf_adic = etree.Element('{http://www.portalfiscal.inf.br/nfe}infAdic')
                
                inf_cpl = etree.SubElement(inf_adic, '{http://www.portalfiscal.inf.br/nfe}infCpl')
                inf_cpl.text = inf_cpl_text
                
                # Adicionar infAdic ao final do infNFe
                inf_nfe_elem.append(inf_adic)
                print(f"✅ [NFELIB] infAdic adicionado: {inf_cpl_text[:50]}...")
            
            # Criar infRespTec (após infAdic) — omitido no retry para nós SEFAZ legados
            if include_resp_tec:
                inf_resp_tec = etree.Element('{http://www.portalfiscal.inf.br/nfe}infRespTec')
                
                cnpj = etree.SubElement(inf_resp_tec, '{http://www.portalfiscal.inf.br/nfe}CNPJ')
                cnpj.text = '46840224000102'
                
                x_contato = etree.SubElement(inf_resp_tec, '{http://www.portalfiscal.inf.br/nfe}xContato')
                x_contato.text = 'Carlos Renato'
                
                email = etree.SubElement(inf_resp_tec, '{http://www.portalfiscal.inf.br/nfe}email')
                email.text = 'contato@emitemax.com.br'
                
                fone = etree.SubElement(inf_resp_tec, '{http://www.portalfiscal.inf.br/nfe}fone')
                fone.text = '1732118981'
                
                # Adicionar infRespTec ao final do infNFe (antes da assinatura)
                inf_nfe_elem.append(inf_resp_tec)
                print("✅ [NFELIB] infRespTec adicionado manualmente")
            else:
                print("⚠️  [NFELIB] infRespTec OMITIDO (retry para nó legado SEFAZ)")
            
            # Reconverter para string
            xml_string = etree.tostring(xml_tree, encoding='unicode')
        
        # CRÍTICO: Remover TODAS as quebras de linha para evitar erro de assinatura
        # A assinatura deve ser calculada sobre XML compacto (sem \n, \r, \t)
        xml_string = xml_string.replace('\n', '').replace('\r', '').replace('\t', '')
        print(f"✅ [NFELIB] Quebras removidas: {len(xml_string)} caracteres (compacto)")
        
        # DEBUG: Verificar se o campo espécie está correto no XML final
        if '<vol>' in xml_string:
            import re
            esp_match = re.search(r'<esp>([^<]+)</esp>', xml_string)
            if esp_match:
                print(f"[DEBUG-XML] Campo <esp> no XML final: '{esp_match.group(1)}' ({len(esp_match.group(1))} chars)")
            else:
                print(f"[DEBUG-XML] Campo <esp> NÃO ENCONTRADO no XML!")
        
        # Salvar XML para análise offline
        try:
            xml_debug_path = f"/tmp/nfe_debug_{numero_nfe}.xml"
            with open(xml_debug_path, 'w', encoding='utf-8') as f:
                f.write(xml_string)
            print(f"📁 [DEBUG] XML salvo em: {xml_debug_path}")
        except Exception as e2:
            print(f"⚠️ [DEBUG] Erro ao salvar XML: {str(e2)}")
        
        return xml_string
    except Exception as e:
        print(f"❌ [NFELIB] Erro ao gerar XML: {e}")
        import traceback
        traceback.print_exc()
        raise
