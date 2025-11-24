import re
from decimal import Decimal, InvalidOperation

def get_uf_ibge_code(uf):
    """
    Retorna o código IBGE da UF
    """
    uf_codes = {
        'AC': 12, 'AL': 17, 'AP': 16, 'AM': 13, 'BA': 29,
        'CE': 23, 'DF': 53, 'ES': 32, 'GO': 52, 'MA': 21,
        'MT': 51, 'MS': 50, 'MG': 31, 'PA': 15, 'PB': 25,
        'PR': 41, 'PE': 26, 'PI': 22, 'RJ': 33, 'RN': 24,
        'RS': 43, 'RO': 11, 'RR': 14, 'SC': 42, 'SP': 35,
        'SE': 28, 'TO': 27
    }
    return uf_codes.get(uf.upper(), 35)  # Default SP

def limpar_cnpj_cpf(documento):
    """
    Remove formatação de CPF/CNPJ, mantendo apenas números
    """
    if not documento:
        return ''
    return re.sub(r'[^0-9]', '', str(documento))

def formatar_cnpj(cnpj):
    """
    Formata CNPJ no padrão XX.XXX.XXX/XXXX-XX
    """
    cnpj = limpar_cnpj_cpf(cnpj)
    if len(cnpj) == 14:
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    return cnpj

def formatar_cpf(cpf):
    """
    Formata CPF no padrão XXX.XXX.XXX-XX
    """
    cpf = limpar_cnpj_cpf(cpf)
    if len(cpf) == 11:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:11]}"
    return cpf

def produto_to_dict_for_template(produto):
    """
    Converte objeto Produto para dicionário para uso em templates
    """
    if not produto:
        return {}
    
    return {
        'produto_id': produto.produto_id,
        'codigo_interno': produto.codigo_interno or '',
        'descricao': produto.descricao or '',
        'preco_unitario_padrao': float(produto.preco_unitario_padrao) if produto.preco_unitario_padrao else 0.0,
        'unidade_comercial': produto.unidade_comercial or 'UN',
        'ncm': produto.ncm or '',
        'ativo': bool(produto.ativo) if hasattr(produto, 'ativo') else True
    }

def calcular_digito_verificador(chave_sem_dv):
    """
    Calcula o dígito verificador da chave de acesso da NFe
    """
    if not chave_sem_dv or len(chave_sem_dv) != 43:
        return 0
    
    # Algoritmo para calcular DV da NFe
    peso = [4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    
    soma = sum(int(chave_sem_dv[i]) * peso[i] for i in range(43))
    resto = soma % 11
    
    if resto < 2:
        return 0
    else:
        return 11 - resto

def formatar_valor_monetario(valor):
    """
    Formatar valor para exibição monetária
    """
    try:
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.'))
        elif isinstance(valor, Decimal):
            valor = float(valor)
        
        return f"R$ {valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

def validar_email(email):
    """
    Validação básica de email
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def normalizar_texto(texto):
    """
    Remove acentos e caracteres especiais
    """
    if not texto:
        return ''
    
    # Dicionário de substituições
    substituicoes = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N'
    }
    
    texto_normalizado = texto
    for original, substituto in substituicoes.items():
        texto_normalizado = texto_normalizado.replace(original, substituto)
    
    return texto_normalizado

def truncar_texto(texto, max_length):
    """
    Trunca texto respeitando limite de caracteres
    """
    if not texto:
        return ''
    
    if len(texto) <= max_length:
        return texto
    
    return texto[:max_length-3] + '...'

def gerar_numero_sequencial(prefixo='', tamanho=6):
    """
    Gera número sequencial para NFe (simplificado)
    """
    import random
    numero = random.randint(1, 10**tamanho - 1)
    return f"{prefixo}{numero:0{tamanho}d}"

def validar_cep(cep):
    """
    Valida formato de CEP brasileiro
    """
    if not cep:
        return False
    
    cep_limpo = limpar_cnpj_cpf(cep)
    return len(cep_limpo) == 8 and cep_limpo.isdigit()

def formatar_cep(cep):
    """
    Formata CEP no padrão XXXXX-XXX
    """
    cep_limpo = limpar_cnpj_cpf(cep)
    if len(cep_limpo) == 8:
        return f"{cep_limpo[:5]}-{cep_limpo[5:]}"
    return cep

def converter_para_decimal(valor, casas_decimais=2):
    """
    Converte valor para Decimal com precisão
    """
    try:
        if isinstance(valor, str):
            valor = valor.replace(',', '.')
        
        decimal_val = Decimal(str(valor))
        return decimal_val.quantize(Decimal('0.' + '0' * casas_decimais))
    except (ValueError, TypeError, InvalidOperation):
        return Decimal('0.' + '0' * casas_decimais)