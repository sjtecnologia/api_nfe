import pytest

from services.ai_prompts import PromptRegistry
from services.ai_service import AIService, AIServiceConfig, AIResponseFormatError
from services.ai_tools import AIToolRegistry


def test_prompt_registry_has_default_prompts():
    registry = PromptRegistry()
    assert registry.get('assistant_business') is not None
    assert registry.get('assistant_fiscal') is not None


def test_tool_registry_exposes_controlled_tools():
    registry = AIToolRegistry()
    tool_names = {tool.nome for tool in registry.list()}
    assert 'getSalesSummary' in tool_names
    assert 'getLowStockProducts' in tool_names


def test_ai_service_can_render_prompt():
    service = AIService(config=AIServiceConfig(provider_url=''))
    rendered = service.render_prompt('assistant_business', {'scope': 'empresa'})
    assert 'EmiteMax IA' in rendered or 'assistente' in rendered.lower()


def test_ai_service_rejects_invalid_json_payload():
    service = AIService(config=AIServiceConfig(provider_url=''))
    with pytest.raises(AIResponseFormatError):
        service._parse_json_payload('texto livre sem json')


def test_ai_service_serializes_json_fields_for_non_postgres():
    service = AIService(config=AIServiceConfig(provider_url=''))
    assert service._serialize_json_field({'a': 1}) == '{"a": 1}'
    assert service._serialize_json_field(None) is None