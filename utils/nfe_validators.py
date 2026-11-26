import re
import logging
from datetime import datetime
from decimal import Decimal
from utils.helpers import limpar_cnpj_cpf, formatar_cnpj, formatar_cpf  # noqa: F401 (reexported)


logger = logging.getLogger(__name__)


def _descricao_item_validacao(item, indice):
    descricao = str(item.get('descricao') or item.get('codigo_produto') or item.get('codigo') or '').strip()
    if descricao:
        return f"Item {indice} ({descricao[:60]})"
    return f"Item {indice}"


def _valor_numerico_texto(valor):
    texto = str(valor or '').strip()
    if not texto:
        return ''
    texto = texto.replace('R$', '').replace(' ', '')
    if ',' in texto and '.' in texto:
        if texto.rfind(',') > texto.rfind('.'):
            texto = texto.replace('.', '').replace(',', '.')
        else:
            texto = texto.replace(',', '')
    elif ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    return texto


def _mascarar_documento(valor):
    digits = re.sub(r'[^0-9]', '', str(valor or ''))
    if not digits:
        return ''
    if len(digits) <= 4:
        return '*' * len(digits)
    return ('*' * (len(digits) - 4)) + digits[-4:]

def validar_cnpj(cnpj):
    """
    Valida CNPJ brasileiro
    """
    if not cnpj:
        return False
    
    # Remove caracteres não numéricos
    cnpj = re.sub(r'[^0-9]', '', str(cnpj))
    
    # Verifica se tem 14 dígitos
    if len(cnpj) != 14:
        return False
    
    # Verifica se não são todos os dígitos iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcula o primeiro dígito verificador
    soma = 0
    peso = 5
    for i in range(12):
        soma += int(cnpj[i]) * peso
        peso -= 1
        if peso < 2:
            peso = 9
    
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula o segundo dígito verificador
    soma = 0
    peso = 6
    for i in range(13):
        soma += int(cnpj[i]) * peso
        peso -= 1
        if peso < 2:
            peso = 9
    
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos calculados conferem
    return cnpj[-2:] == f"{digito1}{digito2}"

def validar_cpf(cpf):
    """
    Valida CPF brasileiro
    """
    if not cpf:
        return False
    
    # Remove caracteres não numéricos
    cpf = re.sub(r'[^0-9]', '', str(cpf))
    
    # Verifica se tem 11 dígitos
    if len(cpf) != 11:
        return False
    
    # Verifica se não são todos os dígitos iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Calcula o primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto
    
    # Calcula o segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto
    
    # Verifica se os dígitos calculados conferem
    return cpf[-2:] == f"{digito1}{digito2}"

def validar_dados_nfe(form_data, emitente_data, destinatario_data, nfe_items):
    """
    Valida todos os dados necessários para emissão da NFe
    """
    erros = []
    
    logger.debug("VALIDAÇÃO - CNPJ emitente recebido: %s", _mascarar_documento(emitente_data.get('cnpj')))
    logger.debug("VALIDAÇÃO - Tipo do CNPJ emitente: %s", type(emitente_data.get('cnpj')))
    
    # [OK] VALIDAÇÕES DO EMITENTE
    cnpj_emitente = emitente_data.get('cnpj', '').strip()
    logger.debug("VALIDAÇÃO - CNPJ emitente normalizado: %s", _mascarar_documento(cnpj_emitente))
    
    if not cnpj_emitente:
        erros.append("CNPJ do emitente é obrigatório")
    elif not validar_cnpj(cnpj_emitente):
        erros.append(f"CNPJ do emitente é inválido: {cnpj_emitente}")
    else:
        logger.debug("VALIDAÇÃO - CNPJ do emitente válido: %s", _mascarar_documento(cnpj_emitente))
    
    if not emitente_data.get('razao_social'):
        erros.append("Razão social do emitente é obrigatória")
    
    if not emitente_data.get('inscricao_estadual'):
        erros.append("Inscrição estadual do emitente é obrigatória")
    
    if not emitente_data.get('logradouro'):
        erros.append("Endereço do emitente é obrigatório")
    
    if not emitente_data.get('uf'):
        erros.append("UF do emitente é obrigatória")
    
    # [OK] VALIDAÇÕES DO DESTINATÁRIO
    if not destinatario_data:
        erros.append("Destinatário é obrigatório")
    else:
        cpf_cnpj_dest = destinatario_data.get('cpf_cnpj', '').strip()
        logger.debug("VALIDAÇÃO - CPF/CNPJ destinatário: %s", _mascarar_documento(cpf_cnpj_dest))
        
        if not cpf_cnpj_dest:
            erros.append("CPF/CNPJ do destinatário é obrigatório")
        else:
            # Verifica se é CPF (11 dígitos) ou CNPJ (14 dígitos)
            cpf_cnpj_limpo = re.sub(r'[^0-9]', '', cpf_cnpj_dest)
            if len(cpf_cnpj_limpo) == 11:
                if not validar_cpf(cpf_cnpj_dest):
                    erros.append(f"CPF do destinatário é inválido: {cpf_cnpj_dest}")
                else:
                    logger.debug("VALIDAÇÃO - CPF destinatário válido: %s", _mascarar_documento(cpf_cnpj_dest))
            elif len(cpf_cnpj_limpo) == 14:
                if not validar_cnpj(cpf_cnpj_dest):
                    erros.append(f"CNPJ do destinatário é inválido: {cpf_cnpj_dest}")
                else:
                    logger.debug("VALIDAÇÃO - CNPJ destinatário válido: %s", _mascarar_documento(cpf_cnpj_dest))

                ie_dest = str(
                    destinatario_data.get('inscricao_estadual')
                    or destinatario_data.get('ie')
                    or ''
                ).strip()
                indicador_ie = str(destinatario_data.get('ie_indicador_nfe') or '').strip().upper()
                if not ie_dest and indicador_ie in ('C', '1', 'CONTRIBUINTE'):
                    erros.append(
                        "Campo Inscrição estadual do destinatário está vazio. "
                        "Se o destinatário for contribuinte, preencha a IE no cadastro ou no campo IE manual; "
                        "se não for contribuinte/isento, ajuste o indicador de IE no cadastro."
                    )
            else:
                erros.append(f"CPF/CNPJ do destinatário deve ter 11 ou 14 dígitos: {cpf_cnpj_dest}")
        
        if not destinatario_data.get('nome_razao_social'):
            erros.append("Nome/Razão social do destinatário é obrigatório")
        
        if not destinatario_data.get('logradouro'):
            erros.append("Endereço do destinatário é obrigatório")
        
        if not destinatario_data.get('uf'):
            erros.append("UF do destinatário é obrigatória")
    
    # [OK] VALIDAÇÕES DOS DADOS GERAIS
    if not form_data.get('natOp'):
        erros.append("Natureza da operação é obrigatória")
    
    if not form_data.get('serie'):
        erros.append("Série da NFe é obrigatória")
    else:
        try:
            serie = int(form_data.get('serie'))
            if serie < 1 or serie > 999:
                erros.append("Série deve estar entre 1 e 999")
        except ValueError:
            erros.append("Série deve ser um número válido")
    
    # [OK] VALIDAÇÕES DOS ITENS
    if not nfe_items:
        erros.append("Pelo menos um item deve ser informado")
    else:
        for i, item in enumerate(nfe_items, 1):
            item_prefix = _descricao_item_validacao(item, i)
            item_prefix_campo = f"{item_prefix}: "
            
            # Descrição é opcional - será buscada do produto se não fornecida
            # if not item.get('descricao'):
            #     erros.append(f"{item_prefix}Descrição é obrigatória")
            
            # Quantidade é opcional - usar 1 se não fornecida
            if item.get('quantidade'):
                try:
                    qtd = float(_valor_numerico_texto(item.get('quantidade')))
                    if qtd <= 0:
                        erros.append(f"{item_prefix_campo}campo Quantidade deve ser maior que zero")
                except ValueError:
                    erros.append(f"{item_prefix_campo}campo Quantidade deve conter apenas números")
            
            if not item.get('valor_unitario'):
                erros.append(f"{item_prefix_campo}campo Valor unitário é obrigatório")
            else:
                try:
                    valor = float(_valor_numerico_texto(item.get('valor_unitario')))
                    if valor <= 0:
                        erros.append(f"{item_prefix_campo}campo Valor unitário deve ser maior que zero")
                except ValueError:
                    erros.append(f"{item_prefix_campo}campo Valor unitário deve conter apenas números")
            
            if not item.get('ncm'):
                erros.append(f"{item_prefix_campo}campo NCM é obrigatório")
            elif len(re.sub(r'[^0-9]', '', item.get('ncm', ''))) != 8:
                erros.append(f"{item_prefix_campo}campo NCM deve ter 8 dígitos")
            
            if not item.get('cfop'):
                erros.append(f"{item_prefix_campo}campo CFOP é obrigatório")
            elif len(re.sub(r'[^0-9]', '', item.get('cfop', ''))) != 4:
                erros.append(f"{item_prefix_campo}campo CFOP deve ter 4 dígitos")
            
            # Validar CST ICMS ou CSOSN (um dos dois é obrigatório)
            # Aceitar ambos os formatos: csosn_icms (usado no XML) ou csosn (legado)
            if not item.get('cst_icms') and not item.get('csosn_icms') and not item.get('csosn'):
                regime = emitente_data.get('regime_tributario_id')
                if str(regime) in ('1', '2'):
                    erros.append(f"{item_prefix_campo}campo CSOSN é obrigatório para este regime tributário")
                elif str(regime) == '3':
                    erros.append(f"{item_prefix_campo}campo CST ICMS é obrigatório para este regime tributário")
                else:
                    erros.append(f"{item_prefix_campo}campo CST ICMS ou CSOSN é obrigatório")
            
            if item.get('origem') is None or item.get('origem') == '':
                erros.append(f"{item_prefix_campo}campo Origem da mercadoria é obrigatório")

            if form_data.get('regime_tributario_id') == 3:
                if not item.get('classificacao_ibs_cbs_id'):
                    erros.append(f"{item_prefix_campo}campo Classificação IBS/CBS é obrigatório para CRT=3")
    
    # [OK] VALIDAÇÃO DO PAGAMENTO
    if not form_data.get('formaPagamento'):
        erros.append("Forma de pagamento é obrigatória")
    
    # Valor pagamento opcional — não validar para 'Sem Pagamento' (90)
    if form_data.get('valorPagamento') and str(form_data.get('formaPagamento')).strip() != '90':
        try:
            valor_str = str(form_data.get('valorPagamento')).replace(',', '.')
            valor_pag = float(valor_str)
            if valor_pag <= 0:
                erros.append("Valor do pagamento deve ser maior que zero")
        except ValueError:
            erros.append("Valor do pagamento deve ser um número válido")
    
    logger.debug("VALIDAÇÃO FINAL - %s erro(s) encontrado(s)", len(erros))
    if erros:
        for erro in erros:
            logger.debug("VALIDAÇÃO - erro: %s", erro)
    
    return erros

def validar_xml_nfe(xml_content):
    """
    Valida o XML da NFe gerado
    """
    erros = []
    
    if not xml_content:
        erros.append("XML não foi gerado")
        return False, erros
    
    logger.debug("VALIDAÇÃO XML - tamanho: %s caracteres", len(xml_content))
    
    # Converter para minúsculas para validação case-insensitive
    xml_lower = xml_content.lower()
    
    # [OK] VALIDAÇÕES BÁSICAS DO XML - CORRIGIDAS
    if '<nfe>' not in xml_lower and '<nfe ' not in xml_lower:
        erros.append("XML não contém tag NFe")
    else:
        logger.debug("VALIDAÇÃO XML - tag NFe encontrada")
    
    if '<emit>' not in xml_lower:
        erros.append("XML não contém dados do emitente")
    else:
        logger.debug("VALIDAÇÃO XML - dados do emitente encontrados")
    
    if '<dest>' not in xml_lower:
        erros.append("XML não contém dados do destinatário")
    else:
        logger.debug("VALIDAÇÃO XML - dados do destinatário encontrados")
    
    # [OK] VALIDAÇÃO DE ITENS - CORRIGIDA
    if '<det ' not in xml_lower and '<det>' not in xml_lower:
        erros.append("XML não contém itens da NFe")
        logger.debug("VALIDAÇÃO XML - tag <det> não encontrada")
        logger.debug("VALIDAÇÃO XML - buscando por 'det' no XML")
        # Debug: mostrar onde deveria estar
        if 'det' in xml_lower:
            logger.debug("VALIDAÇÃO XML - palavra 'det' encontrada em algum lugar")
        else:
            logger.debug("VALIDAÇÃO XML - palavra 'det' não encontrada")
    else:
        logger.debug("VALIDAÇÃO XML - itens da NFe encontrados")
    
    # [OK] VALIDAÇÕES ADICIONAIS
    if '<infnfe' not in xml_lower:
        erros.append("XML não contém informações da NFe (infNFe)")
    else:
        logger.debug("VALIDAÇÃO XML - infNFe encontrado")
    
    if '<ide>' not in xml_lower:
        erros.append("XML não contém identificação da NFe")
    else:
        logger.debug("VALIDAÇÃO XML - IDE encontrado")
    
    # Verificar se tem assinatura (se já foi assinado)
    has_signature = '<signature>' in xml_lower or '<ds:signature>' in xml_lower
    if has_signature:
        logger.debug("VALIDAÇÃO XML - assinatura encontrada")
    else:
        logger.debug("VALIDAÇÃO XML - XML ainda não foi assinado")
    
    # [OK] DEBUG: Mostrar estrutura do XML
    logger.debug("VALIDAÇÃO XML - estrutura (amostra):")
    linhas = xml_content.split('\n')[:20]  # Primeiras 20 linhas
    for i, linha in enumerate(linhas, 1):
        if 'det' in linha.lower():
            logger.debug("%2d: %s [DET]", i, linha.strip())
        elif any(tag in linha.lower() for tag in ['nfe', 'emit', 'dest', 'ide']):
            logger.debug("%2d: %s [OK]", i, linha.strip())
        else:
            logger.debug("%2d: %s", i, linha.strip())
    
    if erros:
        logger.debug("VALIDAÇÃO XML - %s erro(s) encontrado(s)", len(erros))
        for erro in erros:
            logger.debug("VALIDAÇÃO XML - erro: %s", erro)
        return False, erros
    
    logger.debug("VALIDAÇÃO XML - XML válido")
    return True, []

# limpar_cnpj_cpf, formatar_cnpj e formatar_cpf são importadas de utils.helpers (acima).
# As definições locais foram removidas para eliminar duplicação (princípio DRY).