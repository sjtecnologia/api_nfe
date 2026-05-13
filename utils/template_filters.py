"""
utils/template_filters.py — Filtros Jinja2 customizados.

Registra filtros que movem lógica de apresentação do template para Python,
eliminando if/elif chains repetidos nos templates.

Uso em app.py:
    from utils.template_filters import register_filters
    register_filters(app)
"""
from markupsafe import Markup


# ─────────────────────────────────────────────────────────────────────────────
# Status NFe
# ─────────────────────────────────────────────────────────────────────────────

_NFE_STATUS_MAP = {
    'AUTORIZADA':  ('success', 'fa-check-circle',        'Autorizada'),
    'CANCELADA':   ('dark',    'fa-ban',                 'Cancelada'),
    'DENEGADA':    ('danger',  'fa-exclamation-triangle','Denegada'),
    'REJEITADA':   ('danger',  'fa-times-circle',        'Rejeitada'),
    'PROCESSANDO': ('warning', 'fa-clock',               'Processando'),
    'RASCUNHO':    ('secondary','fa-edit',               'Rascunho'),
    'INUTILIZADA': ('secondary','fa-archive',            'Inutilizada'),
    'ERRO':        ('danger',  'fa-exclamation-circle',  'Erro'),
}


def nfe_status_badge(status, tooltip=None):
    """
    Retorna HTML de badge Bootstrap 5 para o status de uma NFe.

    {{ nfe.status | nfe_status_badge | safe }}
    {{ nfe.status | nfe_status_badge(nfe.mensagem_sefaz) | safe }}
    """
    key = (status or '').upper()
    color, icon, label = _NFE_STATUS_MAP.get(key, ('secondary', 'fa-question', status or 'N/A'))
    extra = ''
    if tooltip:
        extra = f' data-bs-toggle="tooltip" data-bs-placement="top" title="{tooltip}"'
    html = (
        f'<span class="badge bg-{color}"{extra}>'
        f'<i class="fas {icon}"></i> {label}</span>'
    )
    return Markup(html)


# ─────────────────────────────────────────────────────────────────────────────
# Finalidade de emissão NFe
# ─────────────────────────────────────────────────────────────────────────────

_FINALIDADE_MAP = {
    '1': ('primary',   'Normal'),
    '2': ('info',      'Complementar'),
    '3': ('warning',   'Ajuste'),
    '4': ('secondary', 'Devolução'),
}


def finalidade_badge(value):
    """
    Badge para finalidade de emissão (1=Normal, 2=Complementar, 3=Ajuste, 4=Devolução).

    {{ nfe.finalidade_emissao | finalidade_badge | safe }}
    """
    key = str(value) if value is not None else ''
    color, label = _FINALIDADE_MAP.get(key, ('secondary', key or 'N/A'))
    extra_class = ' text-dark' if color == 'warning' else ''
    return Markup(f'<span class="badge bg-{color}{extra_class}">{label}</span>')


def tipo_nfe_badge(value):
    """
    Badge para tipo de NFe (0=Entrada, 1=Saída).

    {{ nfe.tipo_nfe | tipo_nfe_badge | safe }}
    """
    key = str(value)
    if key == '1':
        return Markup('<span class="badge bg-info">1 - Saída</span>')
    return Markup('<span class="badge bg-secondary">0 - Entrada</span>')


# ─────────────────────────────────────────────────────────────────────────────
# Status NFS-e
# ─────────────────────────────────────────────────────────────────────────────

_NFSE_STATUS_CODE_MAP = {
    1: ('success', 'Autorizada'),
    2: ('danger',  'Cancelada'),
    3: ('dark',    'Rejeitada'),
}


def nfse_status_badge(codigo_status):
    """
    Badge para status de NFS-e a partir do código numérico (1/2/3).

    {{ nfse.codigo_status | nfse_status_badge | safe }}
    """
    try:
        code = int(codigo_status)
    except (TypeError, ValueError):
        code = -1
    color, label = _NFSE_STATUS_CODE_MAP.get(code, ('secondary', codigo_status or 'N/A'))
    return Markup(f'<span class="badge bg-{color}">{label}</span>')


# ─────────────────────────────────────────────────────────────────────────────
# Formatação de data/hora
# ─────────────────────────────────────────────────────────────────────────────

def format_datetime(value, fmt='%d/%m/%Y %H:%M'):
    """
    Formata um objeto datetime ou string ISO como data legível.

    {{ nfe.data_criacao | format_datetime }}
    {{ nfe.data_emissao | format_datetime('%d/%m/%Y') }}
    """
    if value is None:
        return 'N/A'
    if hasattr(value, 'strftime'):
        return value.strftime(fmt)
    # Tenta converter string ISO
    from datetime import datetime
    for iso_fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(str(value), iso_fmt).strftime(fmt)
        except ValueError:
            continue
    return str(value)


def format_currency(value):
    """
    Formata valor monetário como R$ 1.234,56.

    {{ nfe.valor_total | format_currency }}
    """
    if value is None:
        return 'R$ 0,00'
    try:
        f = float(value)
        return f'R$ {f:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return str(value)


# ─────────────────────────────────────────────────────────────────────────────
# Chave de acesso truncada
# ─────────────────────────────────────────────────────────────────────────────

def truncate_chave(chave, head=8, tail=8):
    """
    Trunca chave de acesso para exibição: primeiros N + '...' + últimos M dígitos.

    {{ nfe.chave_acesso | truncate_chave }}
    {{ nfe.chave_acesso | truncate_chave(4, 4) }}
    """
    if not chave:
        return 'N/A'
    chave = str(chave)
    if len(chave) <= head + tail:
        return chave
    return f'{chave[:head]}...{chave[-tail:]}'


# ─────────────────────────────────────────────────────────────────────────────
# CNPJ/CPF formatado
# ─────────────────────────────────────────────────────────────────────────────

def format_cnpj_cpf(value):
    """
    Formata CNPJ (00.000.000/0001-00) ou CPF (000.000.000-00) a partir de dígitos.

    {{ emitente.cnpj | format_cnpj_cpf }}
    """
    if not value:
        return ''
    digits = ''.join(c for c in str(value) if c.isdigit())
    if len(digits) == 14:
        return f'{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}'
    if len(digits) == 11:
        return f'{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}'
    return value


# ─────────────────────────────────────────────────────────────────────────────
# Registro
# ─────────────────────────────────────────────────────────────────────────────

def register_filters(app):
    """Registra todos os filtros customizados na instância Flask."""
    app.jinja_env.filters['nfe_status_badge']  = nfe_status_badge
    app.jinja_env.filters['finalidade_badge']  = finalidade_badge
    app.jinja_env.filters['tipo_nfe_badge']    = tipo_nfe_badge
    app.jinja_env.filters['nfse_status_badge'] = nfse_status_badge
    app.jinja_env.filters['format_datetime']   = format_datetime
    app.jinja_env.filters['format_currency']   = format_currency
    app.jinja_env.filters['truncate_chave']    = truncate_chave
    app.jinja_env.filters['format_cnpj_cpf']   = format_cnpj_cpf
