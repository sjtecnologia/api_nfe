"""Contratos de saída dos agregadores de inteligência."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class PeriodoAnalise:
    inicio: date
    fim: date

    @property
    def dias(self) -> int:
        return (self.fim - self.inicio).days + 1

    def to_dict(self) -> dict[str, str]:
        return {'inicio': self.inicio.isoformat(), 'fim': self.fim.isoformat()}


@dataclass
class QualidadeDados:
    suficiente: bool = True
    avisos: list[str] = field(default_factory=list)
    origens: list[str] = field(default_factory=list)

    def add_warning(self, message: str) -> None:
        if message not in self.avisos:
            self.avisos.append(message)
        self.suficiente = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DadosAgregados:
    cliente_id: int
    periodo: PeriodoAnalise
    metricas: dict[str, Any] = field(default_factory=dict)
    comparativos: dict[str, Any] = field(default_factory=dict)
    listas: dict[str, Any] = field(default_factory=dict)
    qualidade_dados: QualidadeDados = field(default_factory=QualidadeDados)
    gerado_em: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            'cliente_id': self.cliente_id,
            'periodo': self.periodo.to_dict(),
            'metricas': self.metricas,
            'comparativos': self.comparativos,
            'listas': self.listas,
            'qualidade_dados': self.qualidade_dados.to_dict(),
            'gerado_em': self.gerado_em.isoformat(),
        }


@dataclass
class BusinessSignal:
    """Sinal temporário em memória; não representa uma entidade persistida."""

    domain: str
    code: str
    type: str
    severity: str
    title: str
    description: str
    evidence: dict[str, Any] = field(default_factory=dict)
    action: dict[str, str] | None = None
    relevance: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            'domain': self.domain,
            'code': self.code,
            'type': self.type,
            'severity': self.severity,
            'title': self.title,
            'description': self.description,
            'evidence': self.evidence,
            'action': self.action,
        }
