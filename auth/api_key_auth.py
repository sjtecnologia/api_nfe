"""
Middleware e decorators para autenticação via API Key
"""
from functools import wraps
from flask import request, jsonify, g
from database.connection import get_db
from database.models import ApiKey, ApiUsageLog
import hashlib
import time
from datetime import datetime
from sqlalchemy import text


def generate_api_key(cliente_id, nome):
    """
    Gera uma nova API Key
    
    Returns:
        tuple: (key_string, key_hash, key_prefix)
    """
    import secrets
    
    # Gerar chave aleatória (formato: emx_live_xxxxxxxxxxxxxxxxxxxxx)
    random_part = secrets.token_urlsafe(32)
    key_string = f"emx_live_{random_part}"
    
    # Hash da chave para armazenar no banco
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()
    
    # Prefixo para identificação (primeiros 12 caracteres)
    key_prefix = key_string[:12]
    
    return key_string, key_hash, key_prefix


def verify_api_key(api_key_string):
    """
    Verifica se uma API Key é válida
    
    Args:
        api_key_string: String da chave (emx_live_xxxxx)
        
    Returns:
        ApiKey object ou None
    """
    if not api_key_string or not api_key_string.startswith('emx_'):
        return None
    
    db = next(get_db())
    key_hash = hashlib.sha256(api_key_string.encode()).hexdigest()
    
    api_key = db.query(ApiKey).filter_by(key_hash=key_hash).first()
    
    if not api_key or not api_key.is_valid():
        return None
    
    return api_key


def check_rate_limit(api_key):
    """
    Verifica se a API Key está dentro do rate limit
    
    Args:
        api_key: Objeto ApiKey
        
    Returns:
        tuple: (bool, mensagem)
    """
    if not api_key.rate_limit or api_key.rate_limit == 0:
        return True, "Sem limite"
    
    db = next(get_db())
    
    try:
        # Usar função do banco para verificar
        result = db.execute(
            text("SELECT check_rate_limit(:api_key_id)"),
            {"api_key_id": api_key.api_key_id}
        ).scalar()
        
        if result:
            return True, "Dentro do limite"
        else:
            return False, f"Rate limit excedido ({api_key.rate_limit} req/hora)"
    except Exception as e:
        print(f"[WARN] Erro ao verificar rate limit: {e}")
        # Fallback: contar manualmente
        from datetime import datetime, timedelta
        uma_hora_atras = datetime.now() - timedelta(hours=1)
        db.rollback()
        
        count = db.query(ApiUsageLog).filter(
            ApiUsageLog.api_key_id == api_key.api_key_id,
            ApiUsageLog.request_time >= uma_hora_atras
        ).count()
        
        if count < api_key.rate_limit:
            return True, "Dentro do limite"
        else:
            return False, f"Rate limit excedido ({api_key.rate_limit} req/hora)"


def check_ip_whitelist(api_key, ip_address):
    """
    Verifica se o IP está na whitelist
    
    Args:
        api_key: Objeto ApiKey
        ip_address: IP do cliente
        
    Returns:
        bool
    """
    if not api_key.ip_whitelist:
        return True  # Sem restrição de IP
    
    import json
    try:
        whitelist = json.loads(api_key.ip_whitelist)
        if not whitelist:
            return True
        return ip_address in whitelist
    except:
        return True


def log_api_request(api_key, endpoint, metodo, status_code, response_time_ms=None, erro=None):
    """
    Registra uso da API no banco de dados
    
    Args:
        api_key: Objeto ApiKey
        endpoint: Endpoint acessado
        metodo: Método HTTP
        status_code: Código de status da resposta
        response_time_ms: Tempo de resposta em ms
        erro: Mensagem de erro (se houver)
    """
    try:
        db = next(get_db())
        
        log = ApiUsageLog(
            api_key_id=api_key.api_key_id if api_key else None,
            cliente_id=api_key.cliente_id if api_key else None,
            endpoint=endpoint,
            metodo=metodo,
            status_code=status_code,
            ip_origem=request.remote_addr,
            user_agent=request.headers.get('User-Agent'),
            response_time_ms=response_time_ms,
            erro=erro
        )
        
        db.add(log)
        db.commit()
    except Exception as e:
        print(f"[WARN] Erro ao registrar log de API: {e}")


def require_api_key(permissions=None):
    """
    Decorator para exigir autenticação via API Key
    
    Args:
        permissions: Lista de permissões necessárias (ex: ['nfe.read', 'nfe.write'])
        
    Usage:
        @app.route('/api/v2/produtos')
        @require_api_key(permissions=['produtos.read'])
        def get_produtos():
            # g.api_key contém o objeto ApiKey
            # g.cliente_id contém o ID do cliente
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            # Extrair API Key do header
            auth_header = request.headers.get('Authorization')
            api_key_string = None
            
            if auth_header:
                # Formato: "Bearer emx_live_xxxxx" ou "emx_live_xxxxx"
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    api_key_string = parts[1]
                elif len(parts) == 1:
                    api_key_string = parts[0]
            
            # Ou do query parameter (menos seguro, mas útil para testes)
            if not api_key_string:
                api_key_string = request.args.get('api_key')
            
            if not api_key_string:
                log_api_request(None, request.path, request.method, 401, erro="API Key não fornecida")
                return jsonify({
                    "error": "API Key não fornecida",
                    "message": "Inclua sua API Key no header: Authorization: Bearer sua_chave"
                }), 401
            
            # Verificar validade da chave
            api_key = verify_api_key(api_key_string)
            if not api_key:
                log_api_request(None, request.path, request.method, 401, erro="API Key inválida ou expirada")
                return jsonify({
                    "error": "API Key inválida ou expirada"
                }), 401
            
            # Verificar IP whitelist
            if not check_ip_whitelist(api_key, request.remote_addr):
                log_api_request(api_key, request.path, request.method, 403, erro="IP não autorizado")
                return jsonify({
                    "error": "IP não autorizado",
                    "message": f"Seu IP ({request.remote_addr}) não está na whitelist"
                }), 403
            
            # Verificar rate limit
            within_limit, msg = check_rate_limit(api_key)
            if not within_limit:
                response_time = int((time.time() - start_time) * 1000)
                log_api_request(api_key, request.path, request.method, 429, response_time, msg)
                return jsonify({
                    "error": "Rate limit excedido",
                    "message": msg,
                    "retry_after": 3600  # 1 hora em segundos
                }), 429
            
            # Verificar permissões específicas
            if permissions:
                for perm in permissions:
                    if not api_key.has_permission(perm):
                        log_api_request(api_key, request.path, request.method, 403, erro=f"Permissão negada: {perm}")
                        return jsonify({
                            "error": "Permissão insuficiente",
                            "message": f"Esta chave não tem permissão para: {perm}"
                        }), 403
            
            # Armazenar no contexto do Flask
            g.api_key = api_key
            g.cliente_id = api_key.cliente_id
            g.api_authenticated = True
            g.request_start_time = start_time
            
            # Executar função
            try:
                response = f(*args, **kwargs)
                
                # Registrar sucesso
                response_time = int((time.time() - start_time) * 1000)
                status_code = response[1] if isinstance(response, tuple) else 200
                log_api_request(api_key, request.path, request.method, status_code, response_time)
                
                return response
            except Exception as e:
                # Registrar erro
                response_time = int((time.time() - start_time) * 1000)
                log_api_request(api_key, request.path, request.method, 500, response_time, str(e))
                raise
        
        return decorated_function
    return decorator


def optional_api_key(f):
    """
    Decorator que permite autenticação via API Key OU sessão Flask-Login
    
    Usage:
        @app.route('/api/mixed/produtos')
        @optional_api_key
        def get_produtos():
            # g.api_authenticated = True se autenticado via API Key
            # current_user.is_authenticated se autenticado via sessão
            pass
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Tentar autenticação via API Key
        auth_header = request.headers.get('Authorization')
        if auth_header or request.args.get('api_key'):
            # Usar autenticação de API Key
            return require_api_key()(f)(*args, **kwargs)
        
        # Caso contrário, continuar com autenticação normal (Flask-Login)
        g.api_authenticated = False
        return f(*args, **kwargs)
    
    return decorated_function
