"""Resolução determinística de períodos para análises."""

from __future__ import annotations

from datetime import date, timedelta

from .data_types import PeriodoAnalise


def periodo_anterior(periodo: PeriodoAnalise) -> PeriodoAnalise:
    """Retorna período imediatamente anterior com a mesma duração."""
    dias = periodo.dias
    fim = periodo.inicio - timedelta(days=1)
    return PeriodoAnalise(inicio=fim - timedelta(days=dias - 1), fim=fim)


def variacao_atual_anterior(atual: float, anterior: float) -> dict[str, float | None]:
    """Calcula variações sem delegar cálculo à IA."""
    absoluta = atual - anterior
    percentual = None if anterior == 0 else (absoluta / anterior) * 100
    return {
        'absoluta': round(absoluta, 2),
        'percentual': round(percentual, 2) if percentual is not None else None,
    }


def limitar_periodo(periodo: PeriodoAnalise, max_dias: int = 366) -> PeriodoAnalise:
    if periodo.inicio > periodo.fim:
        raise ValueError('data_inicio deve ser anterior ou igual a data_fim')
    if periodo.dias > max_dias:
        raise ValueError(f'o período não pode exceder {max_dias} dias')
    return periodo
