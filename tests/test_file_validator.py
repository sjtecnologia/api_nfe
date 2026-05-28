"""
Testes unitários para utils/file_validator.py.

Não requerem banco de dados ou contexto Flask.
"""
import io
import pytest
from unittest.mock import MagicMock
from werkzeug.datastructures import FileStorage
from utils.file_validator import validate_upload, FileValidationError


def _make_file(content: bytes, filename: str) -> FileStorage:
    """Helper: cria um FileStorage simulado com conteúdo real."""
    return FileStorage(stream=io.BytesIO(content), filename=filename)


class TestValidateUpload:
    # --- Ausência de arquivo ---
    def test_no_file_raises(self):
        with pytest.raises(FileValidationError):
            validate_upload(None, "certificado")

    def test_empty_filename_raises(self):
        f = FileStorage(stream=io.BytesIO(b"data"), filename="")
        with pytest.raises(FileValidationError):
            validate_upload(f, "certificado")

    # --- Extensões bloqueadas ---
    def test_executable_ext_blocked(self):
        f = _make_file(b"#!/bin/sh\nrm -rf /", "exploit.sh")
        with pytest.raises(FileValidationError, match="não é permitida"):
            validate_upload(f, "default")

    def test_php_ext_blocked(self):
        f = _make_file(b"<?php system($_GET['cmd']); ?>", "shell.php")
        with pytest.raises(FileValidationError):
            validate_upload(f, "default")

    # --- Logo (PNG/JPG) ---
    def test_valid_png_logo(self):
        png_magic = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        f = _make_file(png_magic, "logo.png")
        result = validate_upload(f, "logo")
        assert result == "logo.png"

    def test_invalid_magic_bytes_png(self):
        """Arquivo com extensão .png mas conteúdo de texto deve ser rejeitado."""
        f = _make_file(b"Isso nao eh uma imagem PNG", "falso.png")
        with pytest.raises(FileValidationError, match="conteúdo do arquivo"):
            validate_upload(f, "logo")

    def test_wrong_ext_for_logo_context(self):
        """PDF enviado como logo deve ser rejeitado."""
        f = _make_file(b'%PDF-1.4 conteudo', "doc.pdf")
        with pytest.raises(FileValidationError, match="Extensão"):
            validate_upload(f, "logo")

    # --- Certificado (PFX/P12) ---
    def test_valid_pfx_cert(self):
        pkcs12_magic = b'\x30\x82' + b'\x00' * 50
        f = _make_file(pkcs12_magic, "cert.pfx")
        result = validate_upload(f, "certificado")
        assert result == "cert.pfx"

    def test_cert_wrong_magic(self):
        f = _make_file(b"isso nao e um certificado", "fake.pfx")
        with pytest.raises(FileValidationError, match="conteúdo do arquivo"):
            validate_upload(f, "certificado")

    # --- CSV ---
    def test_valid_csv(self):
        f = _make_file(b"col1,col2\nval1,val2\n", "dados.csv")
        result = validate_upload(f, "csv")
        assert result == "dados.csv"

    # --- Arquivo vazio ---
    def test_empty_file_raises(self):
        f = _make_file(b"", "vazio.csv")
        with pytest.raises(FileValidationError, match="vazio"):
            validate_upload(f, "csv")

    # --- Limite de tamanho ---
    def test_file_exceeds_size_limit(self):
        """Logo com mais de 500 KB deve ser rejeitado."""
        big_content = b'\x89PNG\r\n\x1a\n' + b'\x00' * (600 * 1024)
        f = _make_file(big_content, "grande.png")
        with pytest.raises(FileValidationError, match="grande"):
            validate_upload(f, "logo")

    # --- Override de extensões ---
    def test_allowed_extensions_override(self):
        f = _make_file(b"col1,col2\n", "planilha.csv")
        result = validate_upload(f, "default", allowed_extensions={"csv"})
        assert result == "planilha.csv"

    def test_override_rejects_disallowed_ext(self):
        f = _make_file(b"%PDF content", "doc.pdf")
        with pytest.raises(FileValidationError):
            validate_upload(f, "default", allowed_extensions={"csv"})
