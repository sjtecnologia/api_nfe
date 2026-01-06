"""
Módulo para encriptar/descriptografar IDs nas URLs
Ofusca IDs numéricos para dificultar manipulação de URLs
"""
import hashlib
import base64
from flask import current_app

# Salt secreto para encriptação (deve estar em variável de ambiente em produção)
SECRET_SALT = "nfe-emitemax-2026-secure"

def encode_id(id_num):
    """
    Encripta um ID numérico em uma string hash
    Exemplo: 11 -> 'a7f3b9e2k4'
    """
    if id_num is None:
        return None
    
    # Concatena ID com salt e gera hash
    raw = f"{id_num}-{SECRET_SALT}"
    hash_obj = hashlib.sha256(raw.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Usa os primeiros 10 caracteres + ID codificado
    # Formato: hash[0:10] + base64(id)
    id_encoded = base64.urlsafe_b64encode(str(id_num).encode()).decode().rstrip('=')
    return f"{hash_hex[:10]}{id_encoded}"

def decode_id(encoded_str):
    """
    Descriptografa uma string hash de volta para ID numérico
    Retorna None se o hash for inválido
    """
    if not encoded_str or len(encoded_str) < 10:
        return None
    
    try:
        # Extrai o hash e o ID codificado
        hash_part = encoded_str[:10]
        id_part = encoded_str[10:]
        
        # Decodifica o ID
        # Adiciona padding se necessário
        padding = 4 - (len(id_part) % 4)
        if padding != 4:
            id_part += '=' * padding
        
        id_decoded = base64.urlsafe_b64decode(id_part).decode()
        id_num = int(id_decoded)
        
        # Valida o hash para garantir que não foi adulterado
        expected_encoded = encode_id(id_num)
        if encoded_str != expected_encoded:
            return None
        
        return id_num
    except Exception as e:
        print(f"[ERROR] Erro ao decodificar ID: {e}")
        return None

def validate_encoded_id(encoded_str):
    """
    Valida se um ID encriptado é válido
    """
    return decode_id(encoded_str) is not None
