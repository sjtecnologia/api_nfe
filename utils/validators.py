import re
from decimal import Decimal, InvalidOperation

def validate_email(email):
    """Valida formato de email"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_cep(cep):
    """Valida formato de CEP"""
    if not cep:
        return False
    
    # Remove caracteres não numéricos
    cep_clean = ''.join(filter(str.isdigit, cep))
    return len(cep_clean) == 8

def validate_decimal(value, max_digits=None, decimal_places=None):
    """Valida se um valor pode ser convertido para Decimal"""
    try:
        decimal_value = Decimal(str(value))
        
        if max_digits is not None:
            # Conta dígitos totais
            total_digits = len(str(decimal_value).replace('.', '').replace('-', ''))
            if total_digits > max_digits:
                return False
        
        if decimal_places is not None:
            # Verifica casas decimais
            decimal_str = str(decimal_value)
            if '.' in decimal_str:
                current_decimal_places = len(decimal_str.split('.')[1])
                if current_decimal_places > decimal_places:
                    return False
        
        return True
    except (InvalidOperation, ValueError):
        return False

def validate_positive_number(value):
    """Valida se um valor é um número positivo"""
    try:
        num_value = Decimal(str(value))
        return num_value > 0
    except (InvalidOperation, ValueError):
        return False

def validate_ncm(ncm_code):
    """Valida código NCM"""
    if not ncm_code:
        return False
    
    # Remove caracteres não numéricos
    ncm_clean = ''.join(filter(str.isdigit, ncm_code))
    return len(ncm_clean) == 8

def validate_cfop(cfop_code):
    """Valida código CFOP"""
    if not cfop_code:
        return False
    
    # Remove caracteres não numéricos
    cfop_clean = ''.join(filter(str.isdigit, cfop_code))
    return len(cfop_clean) == 4

def validate_required_fields(data, required_fields):
    """Valida se todos os campos obrigatórios estão presentes"""
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field] or str(data[field]).strip() == '':
            missing_fields.append(field)
    
    return missing_fields