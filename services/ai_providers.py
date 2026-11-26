"""
Providers de IA.

Isola a forma de chamada do modelo para permitir trocar OpenAI-compatible,
Anthropic, Google ou provedores internos sem alterar os casos de uso.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import json
import time

import requests


class AIProviderError(RuntimeError):
    """Erro de provedor de IA."""


@dataclass
class AIProviderResponse:
    content: str
    raw: dict[str, Any]
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0


class AIProvider:
    """Contrato mínimo para qualquer provedor de IA."""

    provider_name = 'base'

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> AIProviderResponse:
        raise NotImplementedError


class OpenAICompatibleProvider(AIProvider):
    """Provider via endpoint compatível com /v1/chat/completions."""

    provider_name = 'openai-compatible'

    def __init__(self, base_url: str, api_key: str = '', timeout_seconds: int = 60):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> AIProviderResponse:
        payload: dict[str, Any] = {
            'model': model,
            'messages': messages,
        }
        if temperature is not None:
            payload['temperature'] = temperature
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        if tools:
            payload['tools'] = tools
        if tool_choice:
            payload['tool_choice'] = tool_choice

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        start = time.perf_counter()
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise AIProviderError(f'Falha ao conectar no provedor de IA: {exc}') from exc

        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code >= 400:
            raise AIProviderError(f'Provedor de IA retornou HTTP {response.status_code}: {response.text}')

        try:
            raw = response.json()
        except ValueError as exc:
            raise AIProviderError('Resposta do provedor de IA nao e JSON valido') from exc

        choices = raw.get('choices') or []
        content = ''
        if choices:
            first_choice = choices[0] or {}
            message = first_choice.get('message') or {}
            content = message.get('content') or ''

        usage = raw.get('usage') or {}
        return AIProviderResponse(
            content=content,
            raw=raw,
            model=raw.get('model') or model or '',
            prompt_tokens=int(usage.get('prompt_tokens') or 0),
            completion_tokens=int(usage.get('completion_tokens') or 0),
            total_tokens=int(usage.get('total_tokens') or 0),
            latency_ms=latency_ms,
        )


class DisabledAIProvider(AIProvider):
    """Provider de fallback que falha de forma previsivel."""

    provider_name = 'disabled'

    def chat(self, messages, *, model=None, temperature=None, max_tokens=None, tools=None, tool_choice=None):
        raise AIProviderError('Nenhum provedor de IA configurado')


class LegacyNcmClassificationProvider(AIProvider):
    """Adapter para o serviço legado de sugestão fiscal em /sugestao."""

    provider_name = 'legacy-ncm-classifier'

    def __init__(self, base_url: str = 'http://localhost:8081', timeout_seconds: int = 150):
        self.base_url = base_url.rstrip('/')
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
    ) -> AIProviderResponse:
        payload: dict[str, Any] = {}
        for message in messages:
            if message.get('role') == 'user':
                user_content = message.get('content', '')
                try:
                    parsed_content = json.loads(user_content)
                    if isinstance(parsed_content, dict):
                        payload.update(parsed_content)
                    else:
                        payload['prompt'] = user_content
                except ValueError:
                    payload['prompt'] = user_content
            elif message.get('role') == 'system':
                payload['system_prompt'] = message.get('content', '')

        if model:
            payload['model'] = model
        if temperature is not None:
            payload['temperature'] = temperature
        if max_tokens is not None:
            payload['max_tokens'] = max_tokens
        if tools:
            payload['tools'] = tools
        if tool_choice:
            payload['tool_choice'] = tool_choice

        start = time.perf_counter()
        try:
            response = requests.post(
                f'{self.base_url}/sugestao',
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise AIProviderError(f'Falha ao conectar no classificador legado de NCM: {exc}') from exc

        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code >= 400:
            raise AIProviderError(f'Classificador legado retornou HTTP {response.status_code}: {response.text}')

        try:
            raw = response.json()
        except ValueError as exc:
            raise AIProviderError('Resposta do classificador legado nao e JSON valido') from exc

        return AIProviderResponse(
            content=json.dumps(raw, ensure_ascii=False),
            raw=raw,
            model=model or 'legacy-ncm-classifier',
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            latency_ms=latency_ms,
        )