"""
Serviço de geração de NFe usando a biblioteca nfelib
Substitui a geração manual de XML por uma biblioteca validada e homologada
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from decimal import Decimal
from nfelib.nfe.bindings.v4_0.nfe_v4_00 import Nfe
from nfelib.nfe.bindings.v4_0.leiaute_nfe_v4_00 import TenderEmi, Tendereco
from utils.helpers import get_uf_ibge_code, limpar_cnpj_cpf
from services.ibs_cbs_service import calcular_ibs_cbs, gerar_xml_ibscbs, gerar_xml_totais_ibscbs
import re
import unicodedata


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


def remover_acentos(texto: str) -> str:
    """
    Remove acentos e caracteres especiais de um texto
    Exemplo: 'ASSOCIAÇÃO' → 'ASSOCIACAO'
    """
    if not texto:
        return texto
    # Normaliza para NFD (separa caracteres base de acentos)
    nfd = unicodedata.normalize('NFD', texto)
    # Remove marcas de acentuação (categoria 'Mn')
    sem_acentos = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    return sem_acentos


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


def generate_nfe_xml_nfelib(
    emitente_data: Dict[str, Any],
    destinatario_data: Dict[str, Any],
    items: list,
    form_data: Dict[str, Any],
    numero_nfe: int,
    certificado_data: Dict[str, Any]
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
    uf_emitente = emitente_data.get('uf', 'SP')
    uf_destinatario = destinatario_data.get('uf', 'SP')
    
    if cfop_primeiro_item.startswith('6') or cfop_primeiro_item.startswith('7'):
        # CFOP 6xxx ou 7xxx = Operação interestadual
        id_dest = "2"
    elif uf_emitente != uf_destinatario:
        # UFs diferentes = Operação interestadual
        id_dest = "2"
    elif cfop_primeiro_item.startswith('3'):
        # CFOP 3xxx = Operação com exterior
        id_dest = "3"
    else:
        # CFOP 5xxx e mesma UF = Operação interna
        id_dest = "1"
    
    print(f"📋 [DEBUG] idDest: {id_dest} (CFOP: {cfop_primeiro_item}, UF Emit: {uf_emitente}, UF Dest: {uf_destinatario})")
    
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
        finNFe=str(form_data.get('finNFe', '1')),
        indFinal="1",
        indPres=form_data.get('indPres', "1"),
        indIntermed="0",
        procEmi="0",  # MANTIDO 0=Aplicação do contribuinte (correto para aplicação própria)
        verProc="EmiteMax_1.0"
    )
    
    print("✅ [NFELIB] IDE criado")
    
    # 5. Criar enderEmit
    cod_mun_emit = str(emitente_data.get('codigo_municipio', '3550308'))
    nome_mun_emit = normalizar_municipio(cod_mun_emit, emitente_data.get('municipio', 'SAO PAULO'))
    
    ender_emit = TenderEmi(
        xLgr=(emitente_data.get('logradouro') or 'RUA TESTE').strip()[:60],
        nro=str(emitente_data.get('numero') or '0').strip()[:60],
        xCpl=(emitente_data.get('complemento') or '').strip()[:60] if emitente_data.get('complemento') else None,
        xBairro=(emitente_data.get('bairro') or 'CENTRO').strip()[:60],
        cMun=cod_mun_emit,
        xMun=nome_mun_emit,
        UF=(emitente_data.get('uf') or 'SP').strip(),
        CEP=limpar_cnpj_cpf(emitente_data.get('cep') or '00000000'),
        cPais="1058",
        xPais="BRASIL"
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
        xNome=emitente_data.get('razao_social', '')[:60],
        xFant=emitente_data.get('nome_fantasia', '')[:60] if emitente_data.get('nome_fantasia') else None,
        enderEmit=ender_emit,
        IE=ie_emitente,
        CRT=crt_emitente
    )
    
    print("✅ [NFELIB] EMIT criado")
    
    # 7. Criar enderDest
    cod_mun_dest = str(destinatario_data.get('codigo_municipio', '3550308'))
    nome_mun_dest = normalizar_municipio(cod_mun_dest, destinatario_data.get('municipio', 'SAO PAULO'))
    
    ender_dest = Tendereco(
        xLgr=destinatario_data.get('logradouro', 'RUA TESTE')[:60],
        nro=str(destinatario_data.get('numero', '0'))[:60],
        xCpl=destinatario_data.get('complemento', '')[:60] if destinatario_data.get('complemento') else None,
        xBairro=destinatario_data.get('bairro', 'CENTRO')[:60],
        cMun=cod_mun_dest,
        xMun=nome_mun_dest,
        UF=destinatario_data.get('uf', 'SP'),
        CEP=limpar_cnpj_cpf(destinatario_data.get('cep', '00000000')),
        cPais="1058",
        xPais="BRASIL"
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
    ie_dest = destinatario_data.get('ie') or destinatario_data.get('inscricao_estadual', '')
    if len(dest_cpf_cnpj) == 11:  # CPF = pessoa física = não contribuinte
        ind_ie_dest = "9"
    elif ie_dest and ie_dest.upper() not in ('', 'ISENTO'):
        ind_ie_dest = "1"  # Contribuinte ICMS
    elif ie_dest and ie_dest.upper() == 'ISENTO':
        ind_ie_dest = "2"  # Contribuinte isento
    else:
        ind_ie_dest = "9"  # Não contribuinte
    
    print(f"✅ [NFELIB] Nome Destinatário: {nome_dest}, indIEDest: {ind_ie_dest}")
    
    dest_kwargs = {
        'xNome': nome_dest[:60],
        'enderDest': ender_dest,
        'indIEDest': ind_ie_dest
    }
    
    # Adicionar IE se for contribuinte
    if ind_ie_dest == "1":
        dest_kwargs['IE'] = ie_dest
    
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
    
    for idx, item in enumerate(items, start=1):
        print(f"📦 [ITEM {idx}] Dados recebidos:")
        print(f"   - codigo_produto: {item.get('codigo_produto')}")
        print(f"   - codigo: {item.get('codigo')}")
        print(f"   - descricao: {item.get('descricao')}")
        print(f"   - Keys disponíveis: {list(item.keys())}")
        
        # Formatar valores com casas decimais corretas
        quantidade = Decimal(str(item.get('quantidade', '1')))
        valor_unitario = Decimal(str(item.get('valor_unitario', '0')))
        valor_total = Decimal(str(item.get('valor_total', '0')))
        
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
        
        prod = Nfe.InfNfe.Det.Prod(
            cProd=str(codigo_prod).strip()[:60],
            cEAN=(item.get('ean') or 'SEM GTIN').strip(),
            xProd=descricao_prod.strip()[:120],
            NCM=(item.get('ncm') or '00000000').strip(),
            CFOP=str(item.get('cfop') or '5102').strip(),
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
        
        v_prod_total += Decimal(str(item.get('valor_total', '0.00')))
        
        # VERIFICAR CRT DO EMITENTE para usar CST ou CSOSN
        crt_int = int(crt_emitente) if crt_emitente.isdigit() else 1
        usar_csosn = crt_int in [1, 2]  # 1=Simples Nacional, 2=SN Sublimite
        
        print(f"  [NFELIB] Item {idx} - CRT: {crt_int}, Usar CSOSN: {usar_csosn}")
        
        # Buscar CST ou CSOSN do item
        cst_item = item.get('cst_icms') or item.get('cst')
        csosn_item = item.get('csosn_icms') or item.get('csosn')
        cfop = str(item.get('cfop', '5102'))
        
        # DECISÃO: CST ou CSOSN baseado no CRT
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
            
            # Criar ICMS com CSOSN
            if csosn_item == '500':
                # Pegar campos ICMS ST do formulário
                v_bc_st_ret = Decimal(str(item.get('vBCSTRet', '0')))
                p_st = Decimal(str(item.get('pST', '0')))
                v_icms_substituto = Decimal(str(item.get('vICMSSubstituto', '0')))
                v_icms_st_ret = Decimal(str(item.get('vICMSSTRet', '0')))
                
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn500(
                    orig="0",
                    CSOSN="500",
                    vBCSTRet=f"{v_bc_st_ret:.2f}",
                    pST=f"{p_st:.2f}",
                    vICMSSubstituto=f"{v_icms_substituto:.2f}",
                    vICMSSTRet=f"{v_icms_st_ret:.2f}"
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN500=icms_sn)
            elif csosn_item == '103':
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn102(
                    orig="0",
                    CSOSN="103"
                )
                icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN102=icms_sn)
            else:  # 102 ou outros
                icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn102(
                    orig="0",
                    CSOSN="102"
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
            
            # Buscar dados tributários do item
            origem = item.get('origem', '0')
            aliquota_icms = Decimal(str(item.get('aliquota_icms', '7')))
            reducao_bc = Decimal(str(item.get('reducao_base_icms', '0')))
            bc_icms = Decimal(str(item.get('bc_icms', valor_total)))
            valor_icms = Decimal(str(item.get('valor_icms', '0')))
            modalidade_bc = item.get('modalidade_bc_icms', '3')
            
            # Criar ICMS com CST apropriado
            if cst_item == '00':
                # Tributada integralmente
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
                icms20_params = {
                    'orig': origem,
                    'CST': "20",
                    'modBC': modalidade_bc,
                    'pRedBC': f"{reducao_bc:.2f}",
                    'vBC': f"{bc_icms:.2f}",
                    'pICMS': f"{aliquota_icms:.2f}",
                    'vICMS': f"{valor_icms:.2f}"
                }
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
            aliq_pis = Decimal(str(item.get('aliquota_pis', '1.65')))
            aliq_cofins = Decimal(str(item.get('aliquota_cofins', '7.6')))
            
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
        aliq_ipi = Decimal(str(item.get('aliquota_ipi', '0')))
        
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
        
        # IBS/CBS - Reforma Tributária (opcional, apenas se CRT=3 e classificacao_ibs_cbs_id presente)
        ibs_cbs_xml = None
        classificacao_ibs_cbs_id = item.get('classificacao_ibs_cbs_id')
        
        # DEBUG: Sempre mostrar se campo IBS/CBS foi recebido
        print(f"  [IBS/CBS] Item {idx} - CRT={crt_int}, classificacao_ibs_cbs_id='{classificacao_ibs_cbs_id}' (tipo: {type(classificacao_ibs_cbs_id).__name__})")
        
        # Verificar se é CRT=3 (Lucro Real/Presumido) e tem classificação
        if crt_int == 3 and classificacao_ibs_cbs_id:
            try:
                from database.connection import get_db
                db = next(get_db())
                
                # ⚠️ CORREÇÃO: Converter para inteiro (vem como string do formulário)
                classificacao_id_int = int(classificacao_ibs_cbs_id)
                print(f"  [IBS/CBS] Item {idx} - Convertido para int: {classificacao_id_int}")
                
                # Calcular IBS/CBS
                ibs_cbs_data = calcular_ibs_cbs(valor_total, classificacao_id_int, db)
                
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
        
        imposto = Nfe.InfNfe.Det.Imposto(**imposto_params)
        
        det = Nfe.InfNfe.Det(
            nItem=str(idx),
            prod=prod,
            imposto=imposto
        )
        
        det_list.append(det)
    
    v_nf_total = v_prod_total
    
    print(f"✅ [NFELIB] {len(det_list)} itens criados")
    
    # 10. Criar TOTAL
    icms_tot = Nfe.InfNfe.Total.Icmstot(
        vBC=f"{v_bc_icms_total:.2f}",
        vICMS=f"{v_icms_total:.2f}",
        vICMSDeson="0.00",
        vFCPUFDest="0.00",  # ICMS interestadual
        vICMSUFDest="0.00",  # ICMS interestadual
        vICMSUFRemet="0.00",  # ICMS interestadual
        vFCP="0.00",
        vBCST="0.00",
        vST="0.00",
        vFCPST="0.00",
        vFCPSTRet="0.00",
        vProd=f"{v_prod_total:.2f}",
        vFrete="0.00",
        vSeg="0.00",
        vDesc="0.00",
        vII="0.00",
        vIPI=f"{v_ipi_total:.2f}",
        vIPIDevol="0.00",
        vPIS=f"{v_pis_total:.2f}",
        vCOFINS=f"{v_cofins_total:.2f}",
        vOutro="0.00",
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
    det_pag = Nfe.InfNfe.Pag.DetPag(
        indPag="0",  # 0=Pagamento à vista, 1=Pagamento a prazo
        tPag="01",  # 01=Dinheiro
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
            if itens_ibs_cbs:
                print(f"🏛️ [IBS/CBS] Adicionando tags aos {len(itens_ibs_cbs)} itens com classificação")
                
                # Adicionar <IBSCBS> a cada <imposto> dos itens
                det_elements = xml_tree.findall('.//nfe:det', ns)
                for idx, (det_elem, ibs_cbs_data) in enumerate(zip(det_elements, itens_ibs_cbs), 1):
                    imposto_elem = det_elem.find('.//nfe:imposto', ns)
                    if imposto_elem is not None:
                        # Gerar XML IBS/CBS e parsear
                        ibs_cbs_xml_str = gerar_xml_ibscbs(ibs_cbs_data)
                        ibs_cbs_fragment = etree.fromstring(f'<root xmlns="http://www.portalfiscal.inf.br/nfe">{ibs_cbs_xml_str}</root>')
                        ibs_cbs_elem = ibs_cbs_fragment[0]  # Primeiro filho
                        
                        # Adicionar após COFINS
                        imposto_elem.append(ibs_cbs_elem)
                        print(f"  [IBS/CBS] Item {idx} - Tag <IBSCBS> adicionada")
                
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
            
            # Criar infRespTec (após infAdic)
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
            
            # Reconverter para string
            xml_string = etree.tostring(xml_tree, encoding='unicode')
            print("✅ [NFELIB] infRespTec adicionado manualmente")
        
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
