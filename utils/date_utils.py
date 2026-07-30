"""
Utilitários de data/hora.
Elimina o bloco de cálculo de período duplicado em admin_routes.py.
"""
from datetime import datetime, timedelta
from typing import Tuple, Optional


def parse_date_range(
    data_inicio_str: Optional[str],
    data_fim_str: Optional[str],
    periodo: str = 'tudo',
    date_format: str = '%Y-%m-%d'
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Resolve o intervalo de datas a partir de strings ou de um período pré-definido.

    Períodos suportados: 'hoje', 'semana', 'mes', 'trimestre', 'ano', 'tudo'.
    Retorna (None, None) para 'tudo' ou período desconhecido.

    Uso:
        from utils.date_utils import parse_date_range

        data_inicio, data_fim = parse_date_range(
            request.args.get('data_inicio'),
            request.args.get('data_fim'),
            request.args.get('periodo', 'tudo')
        )
    """
    if data_inicio_str and data_fim_str:
        try:
            return (
                datetime.strptime(data_inicio_str, date_format),
                datetime.strptime(data_fim_str, date_format),
            )
        except (ValueError, TypeError):
            pass  # fallback para período

    hoje = datetime.now()

    periodos = {
        'hoje':      (
            hoje.replace(hour=0, minute=0, second=0, microsecond=0),
            hoje.replace(hour=23, minute=59, second=59, microsecond=999999),
        ),
        'semana':    (hoje - timedelta(days=hoje.weekday()), hoje),
        'mes':       (hoje.replace(day=1), hoje),
        'trimestre': (hoje - timedelta(days=90), hoje),
        'ano':       (hoje.replace(month=1, day=1), hoje),
    }

    return periodos.get(periodo, (None, None))
