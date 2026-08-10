"""
Catálogo central de prompts da IA.

Mantém os prompts em um único lugar para evitar strings espalhadas pelo código.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass(frozen=True)
class PromptDefinition:
    nome: str
    funcionalidade: str
    versao: str
    prompt: str
    modelo: str
    temperatura: float
    status: str = 'ATIVO'
    parametros: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_PROMPTS: dict[str, PromptDefinition] = {
    'assistant_business': PromptDefinition(
        nome='assistant_business',
        funcionalidade='assistente',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.2,
        prompt=(
            'Você é o EmiteMax IA, um assistente de gestão empresarial. '
            'Responda apenas com base no contexto fornecido. '
            'Se os dados forem insuficientes, diga que não encontrou informações suficientes. '
            'Nunca invente números, clientes, produtos ou eventos.'
        ),
        parametros={'scope': 'empresa', 'safety': 'strict'},
    ),
    'assistant_fiscal': PromptDefinition(
        nome='assistant_fiscal',
        funcionalidade='fiscal',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.1,
        prompt=(
            'Você é o Assistente Fiscal do EmiteMax. Explique processos fiscais com cautela. '
            'Não substitua contador. Use apenas documentação, conhecimento interno e contexto fornecido. '
            'Quando houver incerteza, recomende validação com o responsável fiscal.'
        ),
        parametros={'safety': 'fiscal-cautious'},
    ),
    'product_fill': PromptDefinition(
        nome='product_fill',
        funcionalidade='produtos',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.2,
        prompt=(
            'Você auxilia no preenchimento inteligente de produtos. Sugira campos comerciais, '
            'mas nunca invente atributos fiscais ou comerciais ausentes no contexto. '
            'Use a lógica fiscal existente do sistema como fonte principal quando houver NCM/CFOP.'
        ),
        parametros={'requires_confirmation': True},
    ),
    'marketing_ad': PromptDefinition(
        nome='marketing_ad',
        funcionalidade='marketing',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.7,
        prompt=(
            'Gere conteúdo comercial para o canal informado usando apenas os dados reais do produto. '
            'Não invente especificações, garantia, materiais ou dimensões.'
        ),
        parametros={'channels': ['mercado_livre', 'shopee', 'instagram', 'facebook', 'whatsapp']},
    ),
    'whatsapp_message': PromptDefinition(
        nome='whatsapp_message',
        funcionalidade='mensagens',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.6,
        prompt=(
            'Gere mensagens comerciais para WhatsApp de forma curta, clara e respeitosa. '
            'Use apenas os dados fornecidos e permita variações de tom.'
        ),
        parametros={'tones': ['formal', 'amigavel', 'persuasivo']},
    ),
    'sales_analysis': PromptDefinition(
        nome='sales_analysis',
        funcionalidade='vendas',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.2,
        prompt=(
            'Analise vendas e indicadores do negócio com base em dados estruturados. '
            'Nunca invente números. Destaque tendências, quedas e oportunidades.'
        ),
        parametros={'scope': 'sales'},
    ),
    'daily_summary': PromptDefinition(
        nome='daily_summary',
        funcionalidade='resumo_diario',
        versao='1.0.0',
        modelo='gpt-4o-mini',
        temperatura=0.2,
        prompt=(
            'Produza um resumo inteligente diário com base em métricas fornecidas pelo backend. '
            'Interprete os dados, mas não crie fatos novos.'
        ),
        parametros={'scope': 'daily_kpis'},
    ),
    'product_classification': PromptDefinition(
        nome='product_classification',
        funcionalidade='classificacao_produto',
        versao='1.0.0',
        modelo='legacy-product-classifier',
        temperatura=0.0,
        prompt=(
            'Você classifica produtos para fins fiscais e comerciais. '
            'Retorne somente um JSON com as chaves ncm, cfop, cst, csosn, cest, descricao, confianca e observacoes. '
            'Nunca invente códigos sem base no contexto. Se houver dúvida, use o valor mais conservador e sinalize em observacoes.'
        ),
        parametros={
            'output_format': 'json',
            'required_keys': ['ncm', 'cfop', 'descricao', 'confianca'],
        },
    ),
}


class PromptRegistry:
    """Registro centralizado de prompts."""

    def __init__(self, prompts: Optional[dict[str, PromptDefinition]] = None):
        self._prompts = prompts or dict(DEFAULT_PROMPTS)

    def get(self, nome: str) -> Optional[PromptDefinition]:
        return self._prompts.get(nome)

    def list(self) -> list[PromptDefinition]:
        return list(self._prompts.values())

    def list_active(self) -> list[PromptDefinition]:
        return [prompt for prompt in self._prompts.values() if prompt.status == 'ATIVO']

    def register(self, prompt: PromptDefinition) -> None:
        self._prompts[prompt.nome] = prompt

    def to_dict(self) -> list[dict[str, Any]]:
        return [prompt.to_dict() for prompt in self._prompts.values()]