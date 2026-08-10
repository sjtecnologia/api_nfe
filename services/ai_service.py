"""
AIService - camada única para IA no EmiteMax.

Responsabilidades:
- centralizar prompts e provider
- registrar uso e custos estimados
- aplicar limites por cliente/usuário/plano
- expor helpers seguros para respostas estruturadas
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
import logging
import os
from typing import Any, Optional

from sqlalchemy import func, text

from config.settings import (
    AI_DEFAULT_DAILY_LIMIT,
    AI_DEFAULT_MAX_TOKENS,
    AI_DEFAULT_MONTHLY_LIMIT,
    AI_DEFAULT_TEMPERATURE,
    AI_PROVIDER_API_KEY,
    AI_PROVIDER_MODEL,
    AI_PROVIDER_TIMEOUT_SECONDS,
    AI_PROVIDER_URL,
)
from database.connection import get_db
from database.models import (
    AiConversation,
    AiFeedback,
    AiGeneratedContent,
    AiMessage,
    AiPrompt,
    AiUsageLimit,
    AiUsageLog,
    AssinaturaCliente,
    Cliente,
    PlanoNFe,
)
from utils.db_utils import db_session
from services.ai_prompts import PromptDefinition, PromptRegistry
from services.ai_providers import AIProvider, AIProviderError, AIProviderResponse, DisabledAIProvider, OpenAICompatibleProvider
from services.ai_tools import AIToolRegistry


logger = logging.getLogger(__name__)


@dataclass
class AIServiceConfig:
    provider_url: str = AI_PROVIDER_URL
    provider_model: str = AI_PROVIDER_MODEL
    provider_api_key: str = AI_PROVIDER_API_KEY
    timeout_seconds: int = AI_PROVIDER_TIMEOUT_SECONDS
    default_temperature: float = AI_DEFAULT_TEMPERATURE
    default_max_tokens: int = AI_DEFAULT_MAX_TOKENS
    default_monthly_limit: int = AI_DEFAULT_MONTHLY_LIMIT
    default_daily_limit: int = AI_DEFAULT_DAILY_LIMIT


class AIUsageLimitExceeded(RuntimeError):
    """O limite de uso de IA foi atingido."""


class AIResponseFormatError(RuntimeError):
    """A resposta da IA nao possui o formato esperado."""


class AITenantAccessError(RuntimeError):
    """Acesso negado ao tenant informado."""


class AIService:
    def __init__(
        self,
        db=None,
        provider: Optional[AIProvider] = None,
        prompt_registry: Optional[PromptRegistry] = None,
        tool_registry: Optional[AIToolRegistry] = None,
        config: Optional[AIServiceConfig] = None,
    ):
        self.db = db
        self.config = config or AIServiceConfig()
        self.prompt_registry = prompt_registry or PromptRegistry()
        self.tool_registry = tool_registry or AIToolRegistry()
        self.provider = provider or self._build_default_provider()

    @classmethod
    def from_db(cls, db, **kwargs):
        return cls(db=db, **kwargs)

    def _build_default_provider(self) -> AIProvider:
        if not self.config.provider_url:
            return DisabledAIProvider()
        return OpenAICompatibleProvider(
            base_url=self.config.provider_url,
            api_key=self.config.provider_api_key,
            timeout_seconds=self.config.timeout_seconds,
        )

    def list_prompts(self) -> list[dict[str, Any]]:
        return [prompt.to_dict() for prompt in self.prompt_registry.list_active()]

    def get_prompt(self, nome: str) -> Optional[PromptDefinition]:
        return self.prompt_registry.get(nome)

    def render_prompt(self, nome: str, variables: Optional[dict[str, Any]] = None) -> str:
        prompt = self.prompt_registry.get(nome)
        if not prompt:
            raise KeyError(f'Prompt nao encontrado: {nome}')

        variables = variables or {}
        safe_variables = {key: self._stringify_value(value) for key, value in variables.items()}
        try:
            rendered = prompt.prompt.format(**safe_variables)
        except KeyError as exc:
            raise KeyError(f'Variavel ausente no prompt {nome}: {exc}') from exc
        return rendered

    def build_messages(
        self,
        prompt_name: str,
        user_message: str,
        variables: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        prompt = self.prompt_registry.get(prompt_name)
        if not prompt:
            raise KeyError(f'Prompt nao encontrado: {prompt_name}')

        system_prompt = self.render_prompt(prompt_name, variables)
        if context:
            system_prompt = f"{system_prompt}\n\nCONTEXTO ESTRUTURADO:\n{self._safe_json(context)}"

        return [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message},
        ]

    def chat(
        self,
        *,
        prompt_name: str,
        user_message: str,
        variables: Optional[dict[str, Any]] = None,
        context: Optional[dict[str, Any]] = None,
        cliente_id: Optional[int] = None,
        user_id: Optional[int] = None,
        functionality: Optional[str] = None,
        conversation_id: Optional[int] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools_scope: Optional[str] = None,
        record: bool = True,
    ) -> dict[str, Any]:
        prompt_def = self.prompt_registry.get(prompt_name)
        if not prompt_def:
            raise KeyError(f'Prompt nao encontrado: {prompt_name}')

        resolved_model = model or prompt_def.modelo or self.config.provider_model
        resolved_temperature = temperature if temperature is not None else float(prompt_def.temperatura or self.config.default_temperature)
        resolved_max_tokens = max_tokens or self.config.default_max_tokens
        functionality_name = functionality or prompt_def.funcionalidade or prompt_name

        if cliente_id is not None and user_id is not None:
            self.assert_tenant_access(cliente_id=cliente_id, user_id=user_id)

        self._check_usage_limit(
            cliente_id=cliente_id,
            user_id=user_id,
            funcionalidade=functionality_name,
        )

        messages = self.build_messages(
            prompt_name=prompt_name,
            user_message=user_message,
            variables=variables,
            context=context,
        )

        tools = self.tool_registry.to_openai_tools(tools_scope) if tools_scope else None
        start_time = datetime.now()
        try:
            provider_response = self.provider.chat(
                messages,
                model=resolved_model,
                temperature=resolved_temperature,
                max_tokens=resolved_max_tokens,
                tools=tools,
            )
        except AIProviderError as exc:
            self._record_usage(
                cliente_id=cliente_id,
                user_id=user_id,
                funcionalidade=functionality_name,
                prompt_def=prompt_def,
                provider_name=getattr(self.provider, 'provider_name', 'unknown'),
                model=resolved_model,
                response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                status='ERROR',
                error_message=str(exc),
                conversation_id=conversation_id,
            )
            raise

        usage = self._record_usage(
            cliente_id=cliente_id,
            user_id=user_id,
            funcionalidade=functionality_name,
            prompt_def=prompt_def,
            provider_name=getattr(self.provider, 'provider_name', 'unknown'),
            model=provider_response.model or resolved_model,
            response_time_ms=provider_response.latency_ms,
            prompt_tokens=provider_response.prompt_tokens,
            completion_tokens=provider_response.completion_tokens,
            total_tokens=provider_response.total_tokens,
            conversation_id=conversation_id,
            metadata={
                'tools_scope': tools_scope,
                'prompt_name': prompt_name,
            },
        ) if record else None

        return {
            'success': True,
            'content': provider_response.content,
            'model': provider_response.model or resolved_model,
            'provider': getattr(self.provider, 'provider_name', 'unknown'),
            'prompt_name': prompt_name,
            'prompt_version': prompt_def.versao,
            'functionalidade': functionality_name,
            'usage': usage,
            'raw': provider_response.raw,
        }

    def generate_json(self, **kwargs) -> dict[str, Any]:
        result = self.chat(**kwargs)
        content = (result.get('content') or '').strip()
        if not content:
            raise AIResponseFormatError('A resposta da IA veio vazia')

        parsed = self._parse_json_payload(content)
        result['parsed'] = parsed
        return result

    def start_conversation(
        self,
        *,
        cliente_id: int,
        user_id: Optional[int],
        funcionalidade: str,
        titulo: Optional[str] = None,
        contexto: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        with self._db_context() as db:
            conversation = AiConversation(
                cliente_id=cliente_id,
                user_id=user_id,
                funcionalidade=funcionalidade,
                titulo=titulo,
                contexto=self._serialize_json_field(contexto),
                status='ATIVA',
                last_message_at=datetime.now(),
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            return conversation.to_dict()

    def append_message(
        self,
        *,
        conversation_id: int,
        cliente_id: int,
        user_id: Optional[int],
        funcionalidade: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        cost_estimated: float | Decimal = 0,
        tool_calls: Optional[Any] = None,
    ) -> dict[str, Any]:
        with self._db_context() as db:
            message = AiMessage(
                conversation_id=conversation_id,
                cliente_id=cliente_id,
                user_id=user_id,
                funcionalidade=funcionalidade,
                role=role,
                content=content,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_estimated=cost_estimated,
                tool_calls=self._serialize_json_field(tool_calls),
            )
            db.add(message)
            db.query(AiConversation).filter(AiConversation.conversation_id == conversation_id).update({
                AiConversation.last_message_at: datetime.now(),
                AiConversation.updated_at: datetime.now(),
            })
            db.commit()
            db.refresh(message)
            return message.to_dict()

    def save_generated_content(
        self,
        *,
        cliente_id: int,
        user_id: Optional[int],
        funcionalidade: str,
        output_content: str,
        canal: Optional[str] = None,
        input_data: Optional[dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        with self._db_context() as db:
            content = AiGeneratedContent(
                cliente_id=cliente_id,
                user_id=user_id,
                funcionalidade=functionalidade,
                canal=canal,
                input_data=self._serialize_json_field(input_data),
                output_content=output_content,
                model=model,
            )
            db.add(content)
            db.commit()
            db.refresh(content)
            return content.to_dict()

    def register_feedback(
        self,
        *,
        cliente_id: int,
        user_id: Optional[int],
        funcionalidade: str,
        feedback: str,
        comentario: Optional[str] = None,
        conversation_id: Optional[int] = None,
        message_id: Optional[int] = None,
    ) -> dict[str, Any]:
        with self._db_context() as db:
            feedback_row = AiFeedback(
                cliente_id=cliente_id,
                user_id=user_id,
                funcionalidade=funcionalidade,
                feedback=feedback,
                comentario=comentario,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            db.add(feedback_row)
            db.commit()
            db.refresh(feedback_row)
            return feedback_row.to_dict()

    def get_usage_summary(self, cliente_id: int, funcionalidade: Optional[str] = None) -> dict[str, Any]:
        with self._db_context() as db:
            query = db.query(
                func.count(AiUsageLog.usage_id),
                func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
                func.coalesce(func.sum(AiUsageLog.cost_estimated), 0),
            ).filter(AiUsageLog.cliente_id == cliente_id)
            if funcionalidade:
                query = query.filter(AiUsageLog.funcionalidade == funcionalidade)
            start_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(AiUsageLog.created_at >= start_month)
            count, tokens, cost = query.one()
            return {
                'cliente_id': cliente_id,
                'funcionalidade': funcionalidade,
                'mensal': {
                    'requests': int(count or 0),
                    'tokens': int(tokens or 0),
                    'cost_estimated': float(cost or 0),
                },
            }

    def get_effective_limit(self, cliente_id: int, user_id: Optional[int], funcionalidade: str) -> int:
        with self._db_context() as db:
            limit_row = self._get_effective_limit(db, cliente_id=cliente_id, user_id=user_id, funcionalidade=funcionalidade)
            if limit_row and getattr(limit_row, 'limite_mensal', None) is not None:
                return int(limit_row.limite_mensal)
            return self.config.default_monthly_limit

    def _check_usage_limit(self, *, cliente_id: Optional[int], user_id: Optional[int], funcionalidade: str) -> None:
        if cliente_id is None:
            return

        monthly_limit = self.get_effective_limit(cliente_id, user_id, funcionalidade)
        if monthly_limit <= 0:
            return

        with self._db_context() as db:
            start_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = db.query(func.count(AiUsageLog.usage_id)).filter(
                AiUsageLog.cliente_id == cliente_id,
                AiUsageLog.created_at >= start_month,
            )
            if user_id is not None:
                query = query.filter(AiUsageLog.user_id == user_id)
            if funcionalidade:
                query = query.filter(AiUsageLog.funcionalidade == funcionalidade)

            used = int(query.scalar() or 0)
            if used >= monthly_limit:
                raise AIUsageLimitExceeded('Você atingiu o limite de utilização da IA do seu plano.')

    def _get_effective_limit(self, db, *, cliente_id: int, user_id: Optional[int], funcionalidade: str):
        query = db.query(AiUsageLimit).filter(
            AiUsageLimit.ativo.is_(True),
            AiUsageLimit.funcionalidade == funcionalidade,
        )

        if user_id is not None:
            user_limit = query.filter(AiUsageLimit.user_id == user_id).order_by(AiUsageLimit.updated_at.desc()).first()
            if user_limit:
                return user_limit

        client_limit = query.filter(AiUsageLimit.cliente_id == cliente_id, AiUsageLimit.user_id.is_(None)).order_by(AiUsageLimit.updated_at.desc()).first()
        if client_limit:
            return client_limit

        subscription = db.query(AssinaturaCliente).filter(
            AssinaturaCliente.cliente_id == cliente_id,
            AssinaturaCliente.status == 'ATIVA',
        ).order_by(AssinaturaCliente.updated_at.desc()).first()
        if subscription and subscription.plano_id:
            plan = db.query(PlanoNFe).filter(PlanoNFe.plano_id == subscription.plano_id).first()
            if plan and plan.quantidade_nfes:
                return type('TempLimit', (), {'limite_mensal': int(plan.quantidade_nfes)})()

        return type('TempLimit', (), {'limite_mensal': self.config.default_monthly_limit})()

    def _record_usage(
        self,
        *,
        cliente_id: Optional[int],
        user_id: Optional[int],
        funcionalidade: str,
        prompt_def: PromptDefinition,
        provider_name: str,
        model: str,
        response_time_ms: int,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        status: str = 'SUCCESS',
        error_message: Optional[str] = None,
        conversation_id: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        if cliente_id is None:
            return None

        feature_name = funcionalidade
        estimated_cost = self._estimate_cost(model=model, total_tokens=total_tokens)
        with self._db_context() as db:
            usage = AiUsageLog(
                conversation_id=conversation_id,
                prompt_id=None,
                cliente_id=cliente_id,
                user_id=user_id,
                funcionalidade=feature_name,
                provider=provider_name,
                model=model,
                request_type='chat',
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_estimated=estimated_cost,
                response_time_ms=response_time_ms,
                status=status,
                error_message=error_message,
                metadata_json=self._serialize_json_field(metadata),
            )

            try:
                db.add(usage)
                db.commit()
                db.refresh(usage)
                return usage.to_dict()
            except Exception as exc:
                db.rollback()
                logger.warning('Nao foi possivel registrar uso de IA: %s', exc)
                return None

    def _estimate_cost(self, *, model: str, total_tokens: int) -> Decimal:
        if total_tokens <= 0:
            return Decimal('0')
        rate_per_1k = Decimal('0.0005') if 'mini' in (model or '').lower() else Decimal('0.0020')
        return (Decimal(total_tokens) / Decimal('1000')) * rate_per_1k

    def assert_tenant_access(
        self,
        *,
        cliente_id: Optional[int],
        user_id: Optional[int],
        accessible_client_ids: Optional[list[int]] = None,
    ) -> None:
        if cliente_id is None:
            return

        if accessible_client_ids and cliente_id in accessible_client_ids:
            return

        if user_id is None:
            return

        with self._db_context() as db:
            if self._user_is_super_admin(db, user_id=user_id):
                return
            if self._user_has_client_access(db, cliente_id=cliente_id, user_id=user_id):
                return
        raise AITenantAccessError('Acesso negado ao tenant informado')

    def _user_is_super_admin(self, db, *, user_id: Optional[int]) -> bool:
        if user_id is None:
            return False
        result = db.execute(text("""
            SELECT 1
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id
              AND LOWER(r.name) = 'super_admin'
            LIMIT 1
        """), {'user_id': user_id}).first()
        return bool(result)

    def _user_has_client_access(self, db, *, cliente_id: int, user_id: Optional[int]) -> bool:
        if user_id is None:
            return False
        result = db.execute(text("""
            SELECT 1
            FROM user_clients
            WHERE user_id = :user_id
              AND client_id = :cliente_id
            LIMIT 1
        """), {'user_id': user_id, 'cliente_id': cliente_id}).first()
        return bool(result)

    @contextmanager
    def _db_context(self):
        if self.db is not None:
            yield self.db
            return

        with db_session() as db:
            yield db

    def _parse_json_payload(self, content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[len('```json'):]
        if cleaned.startswith('```'):
            cleaned = cleaned[len('```'):]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AIResponseFormatError(f'Resposta da IA nao e JSON valido: {exc}') from exc

    def _safe_json(self, data: dict[str, Any]) -> str:
        return json.dumps(data, ensure_ascii=False, default=self._stringify_value, indent=2)

    def _serialize_json_field(self, value: Any) -> Any:
        if value is None:
            return None
        if os.getenv('DB_TYPE') == 'postgresql':
            return value
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, default=self._stringify_value)

    def _stringify_value(self, value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, set):
            return list(value)
        return value