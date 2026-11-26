"""Regras comuns para sinalizar qualidade e limitações dos dados."""

from __future__ import annotations

from .data_types import QualidadeDados


def qualidade_periodo(qualidade: QualidadeDados, total_registros: int, nome: str) -> None:
    if total_registros == 0:
        qualidade.add_warning(f'Não existem dados de {nome} no período informado.')


def marcar_historico_insuficiente(
    qualidade: QualidadeDados,
    registros: int,
    minimo: int,
    mensagem: str,
) -> None:
    if registros < minimo:
        qualidade.add_warning(mensagem)
