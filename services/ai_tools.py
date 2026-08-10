"""
Catálogo controlado de ferramentas internas da IA.

As tools não acessam tabelas diretamente no modelo. O registry expõe apenas
metadados e handlers explícitos para consultas controladas no backend.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class AIToolDefinition:
    nome: str
    descricao: str
    parametros: dict[str, Any]
    scope: str
    handler: Optional[Callable[..., Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            'type': 'function',
            'function': {
                'name': self.nome,
                'description': self.descricao,
                'parameters': self.parametros,
            },
        }


DEFAULT_AI_TOOLS: list[AIToolDefinition] = [
    AIToolDefinition(
        nome='getSalesSummary',
        descricao='Retorna resumo de vendas por período para a empresa autenticada.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'data_inicio': {'type': 'string'},
                'data_fim': {'type': 'string'},
            },
            'required': ['cliente_id'],
        },
        scope='sales',
    ),
    AIToolDefinition(
        nome='getTopProducts',
        descricao='Lista os produtos com maior volume ou faturamento.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'limit': {'type': 'integer'},
            },
            'required': ['cliente_id'],
        },
        scope='sales',
    ),
    AIToolDefinition(
        nome='getProduct',
        descricao='Busca um produto específico do cliente autenticado.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'produto_id': {'type': 'integer'},
            },
            'required': ['cliente_id', 'produto_id'],
        },
        scope='products',
    ),
    AIToolDefinition(
        nome='getCustomer',
        descricao='Busca um cliente ou destinatário da empresa autenticada.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'customer_id': {'type': 'integer'},
            },
            'required': ['cliente_id'],
        },
        scope='customers',
    ),
    AIToolDefinition(
        nome='getStock',
        descricao='Retorna informações de estoque do cliente autenticado.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
            },
            'required': ['cliente_id'],
        },
        scope='inventory',
    ),
    AIToolDefinition(
        nome='getFinancialSummary',
        descricao='Retorna resumo financeiro consolidado.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'data_inicio': {'type': 'string'},
                'data_fim': {'type': 'string'},
            },
            'required': ['cliente_id'],
        },
        scope='financial',
    ),
    AIToolDefinition(
        nome='getInvoices',
        descricao='Consulta documentos fiscais da empresa autenticada.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'modelo': {'type': 'string'},
                'data_inicio': {'type': 'string'},
                'data_fim': {'type': 'string'},
            },
            'required': ['cliente_id'],
        },
        scope='fiscal',
    ),
    AIToolDefinition(
        nome='getSalesByPeriod',
        descricao='Agrupa vendas por período para tendências e comparativos.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'periodo': {'type': 'string'},
            },
            'required': ['cliente_id'],
        },
        scope='sales',
    ),
    AIToolDefinition(
        nome='getInactiveProducts',
        descricao='Lista produtos sem venda há determinado período.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'dias': {'type': 'integer'},
            },
            'required': ['cliente_id'],
        },
        scope='insights',
    ),
    AIToolDefinition(
        nome='getLowStockProducts',
        descricao='Lista produtos com estoque crítico ou baixo.',
        parametros={
            'type': 'object',
            'properties': {
                'cliente_id': {'type': 'integer'},
                'dias_cobertura': {'type': 'integer'},
            },
            'required': ['cliente_id'],
        },
        scope='inventory',
    ),
]


class AIToolRegistry:
    def __init__(self, tools: Optional[list[AIToolDefinition]] = None):
        self._tools = {tool.nome: tool for tool in (tools or DEFAULT_AI_TOOLS)}

    def register(self, tool: AIToolDefinition) -> None:
        self._tools[tool.nome] = tool

    def get(self, nome: str) -> Optional[AIToolDefinition]:
        return self._tools.get(nome)

    def list(self) -> list[AIToolDefinition]:
        return list(self._tools.values())

    def list_by_scope(self, scope: str) -> list[AIToolDefinition]:
        return [tool for tool in self._tools.values() if tool.scope == scope]

    def to_openai_tools(self, scope: Optional[str] = None) -> list[dict[str, Any]]:
        tools = self.list_by_scope(scope) if scope else self.list()
        return [tool.to_openai_tool() for tool in tools]

    def execute(self, nome: str, **kwargs: Any) -> Any:
        tool = self.get(nome)
        if not tool:
            raise KeyError(f'Tool nao encontrada: {nome}')
        if not tool.handler:
            raise NotImplementedError(f'Tool {nome} ainda nao possui handler implementado')
        return tool.handler(**kwargs)