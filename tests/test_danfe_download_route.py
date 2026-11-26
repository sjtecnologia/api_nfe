from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


class TestDanfeDownloadRoute:
    def test_download_danfe_pdf_returns_pdf(self, client):
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.is_anonymous = False

        static_danfe_dir = Path(__file__).resolve().parents[1] / 'static' / 'danfe'
        static_danfe_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = static_danfe_dir / 'danfe_123.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\n%fake pdf content\n')

        try:
            mock_role_query = MagicMock()
            mock_role_query.fetchall.return_value = [SimpleNamespace(name='Viewer')]

            with patch('flask_login.utils._get_user', return_value=mock_user), \
                 patch('auth.decorators.get_db') as mock_get_db:
                mock_db = MagicMock()
                mock_db.execute.return_value = mock_role_query
                mock_get_db.return_value = iter([mock_db])

                response = client.get('/admin/nfe/danfe/123/pdf')

            assert response.status_code == 200
            assert response.headers['Content-Type'].startswith('application/pdf')
            assert response.data.startswith(b'%PDF')
        finally:
            if pdf_path.exists():
                pdf_path.unlink()
