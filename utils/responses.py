"""
Funções utilitárias para respostas JSON padronizadas.
Elimina os 3 formatos inconsistentes de resposta de erro espalhados pelo projeto.
"""
from flask import jsonify


def ok(data: dict = None, message: str = None):
    """Resposta de sucesso 200."""
    body = {'success': True}
    if message:
        body['message'] = message
    if data:
        body.update(data)
    return jsonify(body), 200


def created(data: dict = None, message: str = None):
    """Resposta de criação bem-sucedida 201."""
    body = {'success': True}
    if message:
        body['message'] = message
    if data:
        body.update(data)
    return jsonify(body), 201


def error(message: str, status: int = 400):
    """Resposta de erro genérica."""
    return jsonify({'success': False, 'message': message}), status


def not_found(entity: str = 'Recurso'):
    """Resposta 404."""
    return error(f'{entity} não encontrado', 404)


def unauthorized(message: str = 'Acesso não autorizado'):
    """Resposta 401."""
    return error(message, 401)


def forbidden(message: str = 'Acesso negado'):
    """Resposta 403."""
    return error(message, 403)


def server_error(e: Exception = None, message: str = None):
    """Resposta de erro interno 500."""
    msg = message or (f'Erro interno: {e}' if e else 'Erro interno do servidor')
    return error(msg, 500)
