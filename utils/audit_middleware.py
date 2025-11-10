"""
Middleware e Decorators para Auditoria Automática
"""
from functools import wraps
from flask import request, g
from flask_login import current_user
from services.auditoria_service import AuditoriaService
from typing import Optional, Callable, Any
import traceback


def auditar_acao(
    acao: str, 
    tabela: Optional[str] = None, 
    obter_registro_id: Optional[Callable] = None, 
    obter_dados_antes: Optional[Callable] = None, 
    obter_dados_depois: Optional[Callable] = None
) -> Callable:
    """
    Decorator para auditar ações em rotas
    
    Args:
        acao: Tipo de ação (CREATE, UPDATE, DELETE, etc.)
        tabela: Nome da tabela afetada
        obter_registro_id: Função para obter o ID do registro (recebe kwargs da rota)
        obter_dados_antes: Função para obter dados antes da ação
        obter_dados_depois: Função para obter dados depois da ação
    
    Exemplo de uso:
        @auditar_acao('CREATE', 'produtos', obter_registro_id=lambda kwargs: kwargs.get('produto_id'))
        def criar_produto():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Executa a função original
            resultado = f(*args, **kwargs)
            
            # Tenta registrar a auditoria
            try:
                user_id = current_user.id if current_user and current_user.is_authenticated else None
                
                # Obtém dados se funções foram fornecidas
                registro_id = obter_registro_id(kwargs) if obter_registro_id else None
                dados_antes = obter_dados_antes(kwargs) if obter_dados_antes else None
                dados_depois = obter_dados_depois(kwargs) if obter_dados_depois else None
                
                AuditoriaService.registrar_acao(
                    user_id=user_id,
                    acao=acao,
                    tabela_afetada=tabela,
                    registro_id=registro_id,
                    dados_antes=dados_antes,
                    dados_depois=dados_depois
                )
            except Exception as e:
                # Não falha a requisição se auditoria falhar
                print(f"⚠️ Falha ao registrar auditoria: {e}")
                traceback.print_exc()
            
            return resultado
        return wrapped
    return decorator


def auditar_produto(acao: str):
    """Decorator específico para ações em produtos"""
    return auditar_acao(
        acao=acao,
        tabela='produtos',
        obter_registro_id=lambda kwargs: kwargs.get('produto_id')
    )


def auditar_nfe(acao: str):
    """Decorator específico para ações em NFes"""
    return auditar_acao(
        acao=acao,
        tabela='nfe_emitidas',
        obter_registro_id=lambda kwargs: kwargs.get('nfe_id')
    )


def auditar_cliente(acao: str):
    """Decorator específico para ações em clientes"""
    return auditar_acao(
        acao=acao,
        tabela='clientes',
        obter_registro_id=lambda kwargs: kwargs.get('cliente_id')
    )


def auditar_usuario(acao: str):
    """Decorator específico para ações em usuários"""
    return auditar_acao(
        acao=acao,
        tabela='users',
        obter_registro_id=lambda kwargs: kwargs.get('user_id')
    )


def auditar_certificado(acao: str):
    """Decorator específico para ações em certificados"""
    return auditar_acao(
        acao=acao,
        tabela='certificados',
        obter_registro_id=lambda kwargs: kwargs.get('certificado_id')
    )


class AuditoriaMiddleware:
    """
    Middleware global para capturar requisições importantes
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Inicializa o middleware na aplicação Flask"""
        
        @app.before_request
        def before_request():
            """Captura estado antes da requisição"""
            g.audit_start_time = None
            # Pode armazenar estado inicial aqui se necessário
        
        @app.after_request
        def after_request(response):
            """Captura ações após requisição bem-sucedida"""
            try:
                # Apenas audita rotas específicas
                if self._deve_auditar(request.path, request.method):
                    self._registrar_acesso(request, response)
            except Exception as e:
                print(f"⚠️ Erro no middleware de auditoria: {e}")
            
            return response
    
    def _deve_auditar(self, path: str, method: str) -> bool:
        """
        Determina se a rota deve ser auditada automaticamente
        
        Args:
            path: Caminho da rota
            method: Método HTTP
        
        Returns:
            bool: True se deve auditar
        """
        # Lista de padrões de rotas importantes
        rotas_importantes = [
            '/admin/',
            '/cliente/dashboard',
            '/nfe/emitir',
            '/backup/',
        ]
        
        # Audita métodos de modificação
        if method in ['POST', 'PUT', 'DELETE']:
            for rota in rotas_importantes:
                if path.startswith(rota):
                    return True
        
        return False
    
    def _registrar_acesso(self, req, response):
        """Registra acesso a rota importante"""
        try:
            user_id = current_user.id if current_user and current_user.is_authenticated else None
            
            # Define ação baseada no método
            acoes = {
                'GET': 'VIEW',
                'POST': 'CREATE',
                'PUT': 'UPDATE',
                'DELETE': 'DELETE'
            }
            acao = acoes.get(req.method, 'ACCESS')
            
            # Determina descrição baseada na rota
            descricao = f"{req.method} {req.path}"
            if response.status_code >= 400:
                descricao += f" (HTTP {response.status_code})"
            
            AuditoriaService.registrar_acao(
                user_id=user_id,
                acao=acao,
                descricao=descricao,
                ip_address=req.remote_addr,
                user_agent=req.headers.get('User-Agent', '')
            )
        except Exception as e:
            print(f"⚠️ Erro ao registrar acesso: {e}")


# Funções auxiliares para uso manual
def auditar_login_sucesso(user_id: int):
    """Registra login bem-sucedido"""
    from services.auditoria_service import registrar_login
    registrar_login(user_id, sucesso=True)


def auditar_login_falha(username: str):
    """Registra tentativa de login falhada"""
    AuditoriaService.registrar_acao(
        user_id=None,
        acao='LOGIN_FAILED',
        descricao=f"Tentativa de login falhou para usuário: {username}"
    )


def auditar_logout(user_id: int):
    """Registra logout"""
    from services.auditoria_service import registrar_logout
    registrar_logout(user_id)


def auditar_alteracao_manual(user_id: int, acao: str, tabela: str, registro_id: int, 
                             dados_antes=None, dados_depois=None, descricao=None):
    """Registra alteração manual (para casos específicos)"""
    AuditoriaService.registrar_acao(
        user_id=user_id,
        acao=acao,
        tabela_afetada=tabela,
        registro_id=registro_id,
        dados_antes=dados_antes,
        dados_depois=dados_depois,
        descricao=descricao
    )
