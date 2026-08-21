"""Testes da rota protegida de geração de descrição de produto."""

from unittest.mock import patch

import pytest
class FakeAdmin:
    id = 7
    is_authenticated = True

    def is_admin(self):
        return True

    def is_super_admin(self):
        return False

    def get_accessible_clients(self):
        return [{'cliente_id': 5}]


def test_endpoint_gera_sem_salvar_produto(client, monkeypatch):
    monkeypatch.setattr('models.user.User.get', lambda user_id: FakeAdmin())
    monkeypatch.setattr('routes.admin_api_routes._resolve_cliente_id_admin_api', lambda: 5)
    with client.session_transaction() as sess:
        sess['_user_id'] = '7'
        sess['_fresh'] = True
        sess['current_client_id'] = 5
        sess['active_cliente_id'] = 5

    result = {
        'titulo': 'Mouse sem fio',
        'descricao_curta': 'Mouse sem fio para uso diário.',
        'descricao_completa': 'Descrição baseada nos dados fornecidos.',
        'caracteristicas': ['Sem fio'],
        'beneficios': ['Liberdade de movimentação'],
        'palavras_chave': ['mouse', 'sem fio'],
        'avisos': [],
    }
    with patch('routes.admin_api_routes.ProductDescriptionService.generate', return_value=result):
        response = client.post('/admin/api/ia/produtos/gerar-descricao', json={
            'descricao': 'Mouse sem fio',
            'codigo_interno': 'M001',
            'unidade_comercial': 'UN',
            'informacoes_adicionais': 'Cor preta',
        })

    assert response.status_code == 200
    assert response.get_json()['data']['descricao_curta'] == 'Mouse sem fio para uso diário.'


def test_endpoint_rejeita_produto_de_outra_empresa(client, monkeypatch):
    monkeypatch.setattr('models.user.User.get', lambda user_id: FakeAdmin())
    monkeypatch.setattr('routes.admin_api_routes._resolve_cliente_id_admin_api', lambda: 5)

    class FakeRow:
        _mapping = {'produto_id': 99, 'cliente_id': 88, 'descricao': 'Produto de outra empresa'}
        produto_id = 99
        cliente_id = 88
        descricao = 'Produto de outra empresa'

    class FakeResult:
        def fetchone(self):
            return FakeRow()

    class FakeDb:
        def execute(self, *args, **kwargs):
            return FakeResult()

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr('routes.admin_api_routes.get_db', lambda: iter([FakeDb()]))

    with client.session_transaction() as sess:
        sess['_user_id'] = '7'
        sess['_fresh'] = True
        sess['current_client_id'] = 5
        sess['active_cliente_id'] = 5

    response = client.post('/admin/api/ia/produtos/gerar-descricao', json={
        'produto_id': 99,
    })

    assert response.status_code == 403
    assert response.get_json()['success'] is False
