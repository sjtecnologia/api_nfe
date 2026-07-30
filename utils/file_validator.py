"""
Validação robusta de arquivos enviados via upload.

Verifica extensão, tamanho e assinatura binária (magic bytes),
não confiando apenas na extensão declarada pelo cliente.
"""
import os
import json
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
    'xls':  [b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'],
    'xlsx': [b'PK\x03\x04'],
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
    'planilha':    8 * 1024 * 1024,      # 8 MB
    'default':     16 * 1024 * 1024,     # 16 MB
}

# Extensões permitidas por contexto
_ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    'certificado': {'pfx', 'p12'},
    'logo':        {'png', 'jpg', 'jpeg'},
    'csv':         {'csv'},
    'json':        {'json', 'txt'},
    'planilha':    {'csv', 'xlsx', 'xls'},
}

_ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    'certificado': {
        'application/x-pkcs12',
        'application/pkcs12',
        'application/octet-stream',
    },
    'logo': {
        'image/png',
        'image/jpeg',
        'application/octet-stream',
    },
    'csv': {
        'text/csv',
        'application/csv',
        'application/vnd.ms-excel',
        'text/plain',
        'application/octet-stream',
    },
    'json': {
        'application/json',
        'text/json',
        'text/plain',
        'application/octet-stream',
    },
    'planilha': {
        'text/csv',
        'application/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/octet-stream',
    },
}

# Extensões executáveis que nunca devem ser aceitas
_BLOCKED_EXTENSIONS = {
    'exe', 'sh', 'bat', 'cmd', 'ps1', 'vbs', 'js', 'php',
    'py', 'rb', 'pl', 'cgi', 'htm', 'html', 'xml', 'svg',
}

_BLOCKED_MIME_TYPES = {
    'application/x-msdownload',
    'application/x-dosexec',
    'application/x-msdos-program',
    'application/x-sh',
    'application/x-bat',
    'application/x-cmd',
    'application/x-powershell',
    'text/x-php',
}


class FileValidationError(ValueError):
    """Erro de validação de arquivo enviado."""


def _detect_mime_by_content(ext: str, header: bytes, sample: bytes) -> str:
    """Inferencia leve de MIME por assinatura e heuristica de conteudo."""
    if ext in {'png'} and header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if ext in {'jpg', 'jpeg'} and header.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if ext in {'pfx', 'p12'} and header.startswith(b'\x30\x82'):
        return 'application/x-pkcs12'
    if ext == 'xlsx' and header.startswith(b'PK\x03\x04'):
        return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    if ext == 'xls' and header.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'):
        return 'application/vnd.ms-excel'
    if ext == 'pdf' and header.startswith(b'%PDF'):
        return 'application/pdf'

    if ext in {'json', 'txt', 'csv'}:
        if b'\x00' in sample:
            return 'application/octet-stream'
        try:
            decoded = sample.decode('utf-8')
        except UnicodeDecodeError:
            return 'application/octet-stream'

        if ext == 'json':
            stripped = decoded.lstrip()
            if stripped.startswith('{') or stripped.startswith('['):
                return 'application/json'
        return 'text/plain'

    return 'application/octet-stream'


def _validate_text_payload(ext: str, sample: bytes) -> None:
    if b'\x00' in sample:
        raise FileValidationError('Arquivo contem bytes binarios invalidos para este tipo de upload.')

    try:
        decoded = sample.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise FileValidationError('Arquivo deve estar em UTF-8.') from exc

    if ext == 'json':
        stripped = decoded.lstrip()
        if not stripped:
            raise FileValidationError('Arquivo JSON vazio.')
        try:
            json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise FileValidationError('Conteudo JSON invalido.') from exc

    if ext == 'csv':
        if ',' not in decoded and ';' not in decoded and '\t' not in decoded:
            raise FileValidationError('CSV invalido: delimitador nao identificado.')


def validate_upload(
    file: FileStorage,
    context: str,
    allowed_extensions: Optional[set[str]] = None,
    max_size: Optional[int] = None,
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

    # Extensao
    parts = [part for part in safe_name.split('.') if part]
    if len(parts) > 2:
        middle_parts = [p.lower() for p in parts[1:-1]]
        if any(p in _BLOCKED_EXTENSIONS for p in middle_parts):
            raise FileValidationError('Nome de arquivo contem extensao intermediaria bloqueada.')

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

    declared_mimetype = (file.mimetype or '').lower().strip()
    if declared_mimetype in _BLOCKED_MIME_TYPES:
        raise FileValidationError('MIME type bloqueado para upload.')

    allowed_mimes = _ALLOWED_MIME_TYPES.get(context, set())
    if declared_mimetype and allowed_mimes and declared_mimetype not in allowed_mimes:
        # Permite text/plain para csv/json quando navegador envia tipos genericos.
        if not (ext in {'csv', 'json', 'txt'} and declared_mimetype.startswith('text/')):
            raise FileValidationError('MIME type nao permitido para este upload.')

    # Tamanho
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    max_size = max_size or _SIZE_LIMITS.get(context, _SIZE_LIMITS['default'])
    if size > max_size:
        raise FileValidationError(
            f"Arquivo muito grande ({size / 1024:.1f} KB). "
            f"Limite: {max_size // 1024} KB."
        )
    if size == 0:
        raise FileValidationError("Arquivo vazio.")

    # Magic bytes (assinatura binária)
    expected_magics = _MAGIC_BYTES.get(ext, [])
    sample = file.read(8192)
    header = sample[:16]
    file.seek(0)

    if expected_magics:
        if not any(header.startswith(magic) for magic in expected_magics):
            logger.warning(
                "Upload bloqueado: conteúdo real não corresponde à extensão '%s' (magic bytes inválidos)",
                ext,
            )
            raise FileValidationError(
                f"O conteúdo do arquivo não corresponde à extensão '{ext}'."
            )

    if ext in {'csv', 'json', 'txt'}:
        _validate_text_payload(ext, sample)

    detected_mime = _detect_mime_by_content(ext, header, sample)
    if allowed_mimes and detected_mime not in allowed_mimes:
        if not (ext in {'csv', 'json', 'txt'} and detected_mime.startswith('text/')):
            raise FileValidationError('Conteudo real nao corresponde ao tipo de arquivo permitido.')

    return safe_name
