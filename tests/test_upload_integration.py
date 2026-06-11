import io
from types import SimpleNamespace


class _FakeResult:
    def __init__(self, first_obj=None, rows=None):
        self._first_obj = first_obj
        self._rows = rows or []

    def first(self):
        return self._first_obj

    def fetchall(self):
        return self._rows


class _FakeDb:
    def execute(self, *args, **kwargs):
        return _FakeResult(first_obj=object(), rows=[SimpleNamespace(name='Admin')])

    def close(self):
        return None


def _force_admin_auth(monkeypatch):
    # Flask-Login user loader
    from models.user import User

    class _DummyUser:
        id = 1
        is_authenticated = True

        def is_super_admin(self):
            return False

    monkeypatch.setattr(User, 'get', staticmethod(lambda _uid: _DummyUser()))

    # Decorators (admin_required/permission_required) consultam DB para roles/permissoes
    import auth.decorators as decorators
    monkeypatch.setattr(decorators, 'get_db', lambda: iter([_FakeDb()]))


def test_upload_siscomex_invalid_json_rejected(client, app, monkeypatch):
    _force_admin_auth(monkeypatch)

    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True

    data = {
        'siscomex_file': (io.BytesIO(b'{"invalido":'), 'siscomex.json'),
    }
    response = client.post(
        '/admin/ncms/upload-siscomex',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=False,
    )

    assert response.status_code in (301, 302)
    assert '/admin/ncms' in response.headers.get('Location', '')


def test_upload_siscomex_valid_json_calls_service(client, app, monkeypatch):
    _force_admin_auth(monkeypatch)

    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True

    class _FakeNcmService:
        def process_siscomex_json(self, _content):
            return {'success': True, 'message': 'Processado com sucesso'}

    import services.ncm_service as ncm_module
    monkeypatch.setattr(ncm_module, 'ncm_service', _FakeNcmService())

    data = {
        'siscomex_file': (io.BytesIO(b'{"ok": true}'), 'siscomex.json'),
    }
    response = client.post(
        '/admin/ncms/upload-siscomex',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=False,
    )

    assert response.status_code in (301, 302)
    assert '/admin/ncms' in response.headers.get('Location', '')


def test_private_logo_requires_auth(client):
    response = client.get('/admin/media/logos/qualquer.png', follow_redirects=False)
    assert response.status_code in (301, 302)


def test_private_logo_authenticated_serves_file(client, app, monkeypatch, tmp_path):
    _force_admin_auth(monkeypatch)

    private_dir = tmp_path / 'private_uploads'
    logos_dir = private_dir / 'logos'
    logos_dir.mkdir(parents=True, exist_ok=True)
    logo_file = logos_dir / 'cliente_test.png'
    logo_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 8)

    app.config['PRIVATE_UPLOAD_FOLDER'] = str(private_dir)

    with client.session_transaction() as sess:
        sess['_user_id'] = '1'
        sess['_fresh'] = True

    response = client.get('/admin/media/logos/cliente_test.png', follow_redirects=False)

    assert response.status_code == 200
    assert response.mimetype == 'image/png'
