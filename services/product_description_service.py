"""Geração assistida de descrição comercial de produtos."""

from __future__ import annotations

import json
import logging
from typing import Any

from services.ai_service import AIResponseFormatError, AIService, AIUsageLimitExceeded
from services.ai_providers import AIProviderError

logger = logging.getLogger(__name__)


class ProductDescriptionError(ValueError):
    """Erro de validação ou formato na geração de descrição."""


class ProductDescriptionUnavailable(RuntimeError):
    """Provider de IA indisponível."""


class ProductDescriptionService:
    FUNCTIONALITY = 'product_description_generation'
    MAX_ADDITIONAL_INFO = 2000

    def __init__(self, db):
        self._db = db

    def generate(
        self,
        *,
        product_data: dict[str, Any],
        additional_info: str = '',
        cliente_id: int,
        user_id: int | None,
    ) -> dict[str, Any]:
        additional_info = (additional_info or '').strip()
        if len(additional_info) > self.MAX_ADDITIONAL_INFO:
            raise ProductDescriptionError(
                f'Informações adicionais devem ter no máximo {self.MAX_ADDITIONAL_INFO} caracteres.'
            )

        context = self._build_context(product_data, additional_info)
        ai_service = AIService(db=self._db)

        try:
            result = ai_service.generate_json(
                prompt_name='product_description',
                user_message=json.dumps(context, ensure_ascii=False),
                variables={},
                context=context,
                cliente_id=cliente_id,
                user_id=user_id,
                functionality=self.FUNCTIONALITY,
                tools_scope='products',
                record=True,
            )
        except AIUsageLimitExceeded:
            raise
        except AIProviderError as exc:
            logger.warning('Provider indisponível ao gerar descrição: %s', exc)
            raise ProductDescriptionUnavailable(
                'Serviço de IA não está disponível neste momento.'
            ) from exc
        except AIResponseFormatError as exc:
            logger.warning('Resposta inválida ao gerar descrição: %s', exc)
            raise ProductDescriptionError(
                'A IA retornou uma resposta inválida. Tente novamente.'
            ) from exc

        parsed = self._validate_result(result.get('parsed') or {})
        saved = ai_service.save_generated_content(
            cliente_id=cliente_id,
            user_id=user_id,
            funcionalidade=self.FUNCTIONALITY,
            canal='produto',
            input_data=context,
            output_content=json.dumps(parsed, ensure_ascii=False),
            model=result.get('model'),
        )
        parsed['generated_content_id'] = saved.get('generated_content_id')
        parsed['model'] = result.get('model')
        return parsed

    @staticmethod
    def _build_context(product_data: dict[str, Any], additional_info: str) -> dict[str, Any]:
        allowed_fields = {
            'produto_id', 'codigo_interno', 'descricao', 'unidade_comercial',
            'tipo_item', 'preco_unitario_padrao', 'ncm_codigo', 'ncm_descricao',
            'cest', 'cfop_codigo', 'cfop_descricao',
        }
        context = {
            key: value
            for key, value in product_data.items()
            if key in allowed_fields and value not in (None, '')
        }
        context['informacoes_adicionais'] = additional_info
        return context

    @staticmethod
    def _as_string_list(value: Any, field_name: str) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ProductDescriptionError(f'Campo {field_name} deve ser uma lista.')
        return [str(item).strip() for item in value if str(item).strip()][:10]

    def _validate_result(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ProductDescriptionError('Resposta estruturada da IA inválida.')

        required_text = ('titulo', 'descricao_curta', 'descricao_completa')
        result: dict[str, Any] = {}
        for field_name in required_text:
            value = raw.get(field_name)
            if value is None:
                raise ProductDescriptionError(f'Campo {field_name} ausente na resposta da IA.')
            result[field_name] = str(value).strip()

        result['caracteristicas'] = self._as_string_list(raw.get('caracteristicas'), 'caracteristicas')
        result['beneficios'] = self._as_string_list(raw.get('beneficios'), 'beneficios')
        result['palavras_chave'] = self._as_string_list(raw.get('palavras_chave'), 'palavras_chave')
        result['avisos'] = self._as_string_list(raw.get('avisos'), 'avisos')
        return result
