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
import re


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
    
    tp_amb = form_data.get('tpAmb', 2)
    print(f"📋 [DEBUG] Ambiente: {'PRODUÇÃO' if tp_amb == 1 else 'HOMOLOGAÇÃO'} (tpAmb={tp_amb})")
    
    if tp_amb == 2:  # Homologação
        print(f"⚠️  [HOMOLOGAÇÃO] CNPJs reais podem ser rejeitados pela SEFAZ")
        print(f"⚠️  [HOMOLOGAÇÃO] Use CNPJ teste: 99999999000191 se houver rejeição")
    
    print(f"📋 [DEBUG] Emitente CNPJ: {emitente_data.get('cnpj', 'N/A')}")
    print(f"📋 [DEBUG] Emitente Razão: {emitente_data.get('razao_social', 'N/A')}")
    print(f"📋 [DEBUG] Destinatário CPF/CNPJ: {destinatario_data.get('cpf_cnpj', 'N/A')}")
    print(f"📋 [DEBUG] Destinatário Nome: {destinatario_data.get('nome', destinatario_data.get('nome_razao_social', 'N/A'))}")
    print(f"📋 [DEBUG] Número de itens: {len(items)}")
    
    # 1. Gerar data de emissão (usar timezone brasileiro BRT = UTC-3)
    # Subtrair 5 minutos para garantir que não seja futura (margem ampla de segurança)
    from datetime import timezone as tz
    brt = tz(timedelta(hours=-3))
    data_emissao = datetime.now(brt) - timedelta(minutes=5)
    
    print(f"✅ [NFELIB] Data de emissão (BRT -5min): {data_emissao.isoformat()}")
    
    # 2. Gerar chave de acesso (44 dígitos)
    chave_acesso = gerar_chave_acesso(emitente_data, form_data, numero_nfe, data_emissao)
    
    # 3. Gerar Id do infNFe (formato: "NFe" + chave de 44 dígitos)
    id_nfe = f"NFe{chave_acesso}"
    
    # 4. Criar IDE (identificação)
    ide = Nfe.InfNfe.Ide(
        cUF=str(get_uf_ibge_code(emitente_data.get('uf', 'SP'))),
        cNF=form_data.get('codigo_numerico', str(abs(hash(str(numero_nfe))) % 100000000))[:8],
        natOp=form_data.get('natOp', 'VENDA')[:60],
        mod="55",
        serie=str(form_data.get('serie', '1')),
        nNF=str(numero_nfe),
        dhEmi=data_emissao.isoformat(),
        tpNF=str(form_data.get('tpNF', '1')),
        idDest="1",
        cMunFG=str(emitente_data.get('codigo_municipio', '3550308')),
        tpImp="1",
        tpEmis="1",
        tpAmb=str(form_data.get('tpAmb', 2)),
        finNFe=str(form_data.get('finNFe', '1')),
        indFinal="1",
        indPres=form_data.get('indPres', "1"),
        indIntermed="0",
        procEmi="1",  # 1=Aplicação do contribuinte (NFe emitida em produção)
        verProc="EmiteMax_1.0"
    )
    
    print("✅ [NFELIB] IDE criado")
    
    # 5. Criar enderEmit
    ender_emit = TenderEmi(
        xLgr=emitente_data.get('logradouro', 'RUA TESTE')[:60],
        nro=str(emitente_data.get('numero', '0'))[:60],
        xCpl=emitente_data.get('complemento', '')[:60] if emitente_data.get('complemento') else None,
        xBairro=emitente_data.get('bairro', 'CENTRO')[:60],
        cMun=str(emitente_data.get('codigo_municipio', '3550308')),
        xMun=emitente_data.get('municipio', 'SAO PAULO')[:60],
        UF=emitente_data.get('uf', 'SP'),
        CEP=limpar_cnpj_cpf(emitente_data.get('cep', '00000000')),
        cPais="1058",
        xPais="BRASIL"
    )
    
    # 6. Criar EMIT (emitente) com endereço
    cnpj_emitente = limpar_cnpj_cpf(emitente_data.get('cnpj', ''))
    if not cnpj_emitente or cnpj_emitente == '0' * 14:
        raise ValueError(f"CNPJ do emitente inválido ou vazio: {emitente_data.get('cnpj', 'N/A')}")
    cnpj_emitente = cnpj_emitente.zfill(14)
    print(f"✅ [NFELIB] CNPJ Emitente: {cnpj_emitente} ({len(cnpj_emitente)} dígitos)")
    
    # Buscar IE (pode estar como 'ie' ou 'inscricao_estadual')
    ie_emitente = emitente_data.get('ie') or emitente_data.get('inscricao_estadual', '')
    if not ie_emitente:
        raise ValueError("Inscrição Estadual do emitente é obrigatória")
    
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
    ender_dest = Tendereco(
        xLgr=destinatario_data.get('logradouro', 'RUA TESTE')[:60],
        nro=str(destinatario_data.get('numero', '0'))[:60],
        xCpl=destinatario_data.get('complemento', '')[:60] if destinatario_data.get('complemento') else None,
        xBairro=destinatario_data.get('bairro', 'CENTRO')[:60],
        cMun=str(destinatario_data.get('codigo_municipio', '3550308')),
        xMun=destinatario_data.get('municipio', 'SAO PAULO')[:60],
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
    
    print(f"✅ [NFELIB] CPF/CNPJ Destinatário: {dest_cpf_cnpj} ({len(dest_cpf_cnpj)} dígitos)")
    
    # Nome pode estar em 'nome' ou 'nome_razao_social'
    nome_dest = (destinatario_data.get('nome') or 
                destinatario_data.get('nome_razao_social') or '')
    if not nome_dest:
        raise ValueError("Nome do destinatário é obrigatório")
    
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
    
    for idx, item in enumerate(items, start=1):
        # Produto
        prod = Nfe.InfNfe.Det.Prod(
            cProd=str(item.get('codigo', idx))[:60],
            cEAN=item.get('ean', 'SEM GTIN'),
            xProd=item.get('descricao', 'PRODUTO')[:120],
            NCM=item.get('ncm', '00000000'),
            CFOP=str(item.get('cfop', '5102')),
            uCom=item.get('unidade', 'UN')[:6],
            qCom=str(item.get('quantidade', '1.0000')),
            vUnCom=str(item.get('valor_unitario', '0.00')),
            vProd=str(item.get('valor_total', '0.00')),
            cEANTrib=item.get('ean', 'SEM GTIN'),
            uTrib=item.get('unidade', 'UN')[:6],
            qTrib=str(item.get('quantidade', '1.0000')),
            vUnTrib=str(item.get('valor_unitario', '0.00')),
            indTot="1"
        )
        
        v_prod_total += Decimal(str(item.get('valor_total', '0.00')))
        
        # Determinar CSOSN baseado no CFOP
        cfop = str(item.get('cfop', '5102'))
        csosn_item = item.get('csosn', None)
        
        # Se não fornecido, determinar automaticamente
        if not csosn_item:
            # CFOP 5102/6102 = Venda de mercadoria (CSOSN 102 - SN sem crédito)
            # CFOP 5405/6405 = Venda de bem do ativo imobilizado (CSOSN 102 - SN sem destaque ICMS)
            if cfop in ('5102', '6102', '5405', '6405'):
                csosn_item = '102'
            # CFOP 5103/6103 = Venda com ICMS ST (CSOSN 500)
            elif cfop in ('5103', '6103'):
                csosn_item = '500'
            # CFOP 5403/6403 = Retorno de remessa ST (CSOSN 500)
            elif cfop in ('5403', '6403'):
                csosn_item = '500'
            else:
                csosn_item = '102'  # Padrão: Simples Nacional sem permissão de crédito
        
        print(f"  [NFELIB] Item {idx} - CFOP {cfop} → CSOSN {csosn_item}")
        
        # Impostos - ICMS baseado no CSOSN
        if csosn_item == '500':
            # CSOSN 500 - ICMS cobrado anteriormente por ST
            icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn500(
                orig="0",
                CSOSN="500",
                vBCSTRet="0.00",
                pST="0.00",
                vICMSSubstituto="0.00",
                vICMSSTRet="0.00"
            )
            icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN500=icms_sn)
        elif csosn_item == '103':
            # CSOSN 103 - Isenção do ICMS para faixa de receita bruta
            icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn102(
                orig="0",
                CSOSN="103"
            )
            icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN102=icms_sn)
        else:
            # CSOSN 102 - Tributada pelo Simples Nacional sem permissão de crédito
            # Usado para: 5102, 5405 (venda ativo), e outros CFOPs sem destaque ICMS
            icms_sn = Nfe.InfNfe.Det.Imposto.Icms.Icmssn102(
                orig="0",
                CSOSN="102"
            )
            icms = Nfe.InfNfe.Det.Imposto.Icms(ICMSSN102=icms_sn)
        
        # PIS (não tributado para Simples Nacional)
        pis_nt = Nfe.InfNfe.Det.Imposto.Pis.Pisnt(CST="07")
        pis = Nfe.InfNfe.Det.Imposto.Pis(PISNT=pis_nt)
        
        # COFINS (não tributado para Simples Nacional)
        cofins_nt = Nfe.InfNfe.Det.Imposto.Cofins.Cofinsnt(CST="07")
        cofins = Nfe.InfNfe.Det.Imposto.Cofins(COFINSNT=cofins_nt)
        
        imposto = Nfe.InfNfe.Det.Imposto(
            ICMS=icms,
            PIS=pis,
            COFINS=cofins
        )
        
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
        vBC="0.00",
        vICMS="0.00",
        vICMSDeson="0.00",
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
        vIPI="0.00",
        vIPIDevol="0.00",
        vPIS="0.00",
        vCOFINS="0.00",
        vOutro="0.00",
        vNF=f"{v_nf_total:.2f}"
    )
    
    total = Nfe.InfNfe.Total(ICMSTot=icms_tot)
    
    print("✅ [NFELIB] TOTAL criado")
    
    # 11. Criar TRANSP
    transp = Nfe.InfNfe.Transp(modFrete="9")  # 9=Sem frete
    
    print("✅ [NFELIB] TRANSP criado")
    
    # 12. Criar PAG
    det_pag = Nfe.InfNfe.Pag.DetPag(
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
        return xml_string
    except Exception as e:
        print(f"❌ [NFELIB] Erro ao gerar XML: {e}")
        import traceback
        traceback.print_exc()
        raise
