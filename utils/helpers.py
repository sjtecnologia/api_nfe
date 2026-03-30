from decimal import Decimal

def produto_to_dict_for_template(produto_obj):
    """Converte um objeto Produto para dicionário serializável para templates"""
    return {
        "produto_id": produto_obj.produto_id,
        "codigo_interno": produto_obj.codigo_interno,
        "descricao": produto_obj.descricao,
        "ncm": {
            "codigo": produto_obj.ncm.codigo, 
            "descricao": produto_obj.ncm.descricao
        } if produto_obj.ncm else None,
        "cest": produto_obj.cest,
        "unidade_comercial": produto_obj.unidade_comercial,
        "preco_unitario_padrao": float(produto_obj.preco_unitario_padrao) if produto_obj.preco_unitario_padrao is not None else 0.0,
        "origem": {
            "codigo": produto_obj.origem.codigo, 
            "descricao": produto_obj.origem.descricao
        } if produto_obj.origem else None,
        "tipo_item": produto_obj.tipo_item,
        "ativo": produto_obj.ativo,
        "cfop": {
            "cfop": produto_obj.cfop.cfop, 
            "descricao": produto_obj.cfop.descricao
        } if produto_obj.cfop else None,
        "csts_icms": {
            "codigo": produto_obj.csts_icms.codigo, 
            "descricao": produto_obj.csts_icms.descricao
        } if produto_obj.csts_icms else None,
        "csosns_icms": {
            "codigo": produto_obj.csosns_icms.codigo, 
            "descricao": produto_obj.csosns_icms.descricao
        } if produto_obj.csosns_icms else None,
    }

def get_uf_ibge_code(uf_abbr):
    """Retorna o código IBGE da UF a partir de sua sigla"""
    if not uf_abbr:
        return 99
        
    uf_codes = {
        "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29, "CE": 23, "DF": 53,
        "ES": 32, "GO": 52, "MA": 21, "MG": 31, "MS": 50, "MT": 51, "PA": 15,
        "PB": 25, "PE": 26, "PI": 22, "PR": 41, "RJ": 33, "RN": 24, "RO": 11,
        "RR": 14, "RS": 43, "SC": 42, "SE": 28, "SP": 35, "TO": 17
    }
    return uf_codes.get(uf_abbr.upper(), 99)

def limpar_cnpj_cpf(documento):
    """Remove formatação de CNPJ ou CPF, retornando apenas dígitos"""
    if not documento:
        return ""
    return ''.join(filter(str.isdigit, str(documento)))

def format_cnpj_cpf(documento):
    """Formata CNPJ ou CPF adicionando máscaras"""
    if not documento:
        return ""
    
    # Remove caracteres não numéricos
    numeros = ''.join(filter(str.isdigit, documento))
    
    if len(numeros) == 11:  # CPF
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    elif len(numeros) == 14:  # CNPJ
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    else:
        return documento

def format_currency(value):
    """Formata valor monetário"""
    if value is None:
        return "R$ 0,00"
    
    if isinstance(value, str):
        try:
            value = Decimal(value)
        except:
            return "R$ 0,00"
    
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def validate_cnpj(cnpj):
    """Valida CNPJ"""
    if not cnpj:
        return False
    
    # Remove caracteres não numéricos
    cnpj = ''.join(filter(str.isdigit, cnpj))
    
    if len(cnpj) != 14:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Validação do primeiro dígito verificador
    sequence = cnpj[:12]
    weights = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_result = sum(int(digit) * weight for digit, weight in zip(sequence, weights))
    remainder = sum_result % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    if int(cnpj[12]) != first_digit:
        return False
    
    # Validação do segundo dígito verificador
    sequence = cnpj[:13]
    weights = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum_result = sum(int(digit) * weight for digit, weight in zip(sequence, weights))
    remainder = sum_result % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return int(cnpj[13]) == second_digit

def validate_cpf(cpf):
    """Valida CPF"""
    if not cpf:
        return False
    
    # Remove caracteres não numéricos
    cpf = ''.join(filter(str.isdigit, cpf))
    
    if len(cpf) != 11:
        return False
    
    # Verifica se todos os dígitos são iguais
    if cpf == cpf[0] * 11:
        return False
    
    # Validação do primeiro dígito verificador
    sum_result = sum(int(cpf[i]) * (10 - i) for i in range(9))
    remainder = sum_result % 11
    first_digit = 0 if remainder < 2 else 11 - remainder
    
    if int(cpf[9]) != first_digit:
        return False
    
    # Validação do segundo dígito verificador
    sum_result = sum(int(cpf[i]) * (11 - i) for i in range(10))
    remainder = sum_result % 11
    second_digit = 0 if remainder < 2 else 11 - remainder
    
    return int(cpf[10]) == second_digit