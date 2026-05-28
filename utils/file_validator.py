"""
Validação robusta de arquivos enviados via upload.

Verifica extensão, tamanho e assinatura binária (magic bytes),
não confiando apenas na extensão declarada pelo cliente.
"""
import os
import logging
from typing import Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Magic bytes por tipo de arquivo (primeiros bytes do arquivo)
_MAGIC_BYTES: dict[str, list[bytes]] = {
    'pfx':  [b'\x30\x82'],                          # PKCS#12 / DER ASN.1
    'p12':  [b'\x30\x82'],
    'csv':  [],                                      # CSV não tem magic bytes — só extensão
    'pdf':  [b'%PDF'],
    'png':  [b'\x89PNG\r\n\x1a\n'],
    'jpg':  [b'\xff\xd8\xff'],
    'jpeg': [b'\xff\xd8\xff'],
    'json': [],                                      # JSON não tem magic bytes
}

# Tamanho máximo por contexto (bytes)
_SIZE_LIMITS: dict[str, int] = {
    'certificado': 2 * 1024 * 1024,     # 2 MB
    'logo':        500 * 1024,           # 500 KB
    'csv':         5 * 1024 * 1024,      # 5 MB
    'json':        10 * 1024 * 1024,     # 10 MB
    'default':     16 * 1024 * 1024,     # 16 MB
}

# Extensões permitidas por contexto
_ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    'certificado': {'pfx', 'p12'},
    'logo':        {'png', 'jpg', 'jpeg'},
    'csv':         {'csv'},
    'json':        {'json', 'txt'},
}

# Extensões executáveis que nunca devem ser aceitas
_BLOCKED_EXTENSIONS = {
    'exe', 'sh', 'bat', 'cmd', 'ps1', 'vbs', 'js', 'php',
    'py', 'rb', 'pl', 'cgi', 'htm', 'html', 'xml', 'svg',
}


class FileValidationError(ValueError):
    """Erro de validação de arquivo enviado."""


def validate_upload(
    file: FileStorage,
    context: str,
    allowed_extensions: Optional[set[str]] = None,
) -> str:
    """
    Valida um arquivo de upload.

    Args:
        file: objeto FileStorage do Flask
        context: tipo do upload ('certificado', 'logo', 'csv', 'json', 'default')
        allowed_extensions: override opcional do conjunto de extensões permitidas

    Returns:
        Nome de arquivo seguro (secure_filename).

    Raises:
        FileValidationError: se alguma validação falhar.
    """
    if not file or not file.filename:
        raise FileValidationError("Nenhum arquivo enviado.")

    filename = file.filename
    safe_name = secure_filename(filename)
    if not safe_name:
        raise FileValidationError("Nome de arquivo inválido.")

    # Extensão
    ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''

    if ext in _BLOCKED_EXTENSIONS:
        logger.warning("Upload bloqueado: extensão executável '%s' enviada por user_id desconhecido", ext)
        raise FileValidationError(f"Extensão '{ext}' não é permitida.")

    permitted = allowed_extensions or _ALLOWED_EXTENSIONS.get(context, set())
    if permitted and ext not in permitted:
        raise FileValidationError(
            f"Extensão '{ext}' não permitida para este upload. "
            f"Extensões aceitas: {', '.join(sorted(permitted))}"
        )

    # Tamanho
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    max_size = _SIZE_LIMITS.get(context, _SIZE_LIMITS['default'])
    if size > max_size:
        raise FileValidationError(
            f"Arquivo muito grande ({size / 1024:.1f} KB). "
            f"Limite: {max_size // 1024} KB."
        )
    if size == 0:
        raise FileValidationError("Arquivo vazio.")

    # Magic bytes (assinatura binária)
    expected_magics = _MAGIC_BYTES.get(ext, [])
    if expected_magics:
        header = file.read(16)
        file.seek(0)
        if not any(header.startswith(magic) for magic in expected_magics):
            logger.warning(
                "Upload bloqueado: conteúdo real não corresponde à extensão '%s' (magic bytes inválidos)",
                ext,
            )
            raise FileValidationError(
                f"O conteúdo do arquivo não corresponde à extensão '{ext}'."
            )

    return safe_name
