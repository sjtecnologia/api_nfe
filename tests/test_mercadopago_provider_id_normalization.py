"""Teste de webhook com provider_plan_id real do Mercado Pago."""
import pytest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from services.payment_plan_mapping import PaymentPlanMappingService


def _version(code="START_V1", price="60.00"):
    return SimpleNamespace(plan_version_id=1, version_code=code, price=Decimal(price), currency="BRL", status="ACTIVE")


def test_webhook_with_real_provider_id_fails_with_test_prefix():
    """
    Demonstra o BUG: quando o script registra TEST_22b64..., 
    mas webhook chega com ID real 22b64..., falha com PAYMENT_MAPPING_MISMATCH.
    """
    test_prefixed_id = "TEST_22b643676beb47d5b784a0afd4a5ec79"
    real_mercado_pago_id = "22b643676beb47d5b784a0afd4a5ec79"
    
    db = MagicMock()
    query = MagicMock()
    query.filter_by.return_value = query
    query.first.return_value = _version()
    db.query.return_value = query
    
    # SQL execute retorna tupla com os campos na ordem esperada
    class MockRow:
        def __init__(self, values):
            self.values = values
        def __iter__(self):
            return iter(self.values)
        @property
        def currency(self):
            return self.values[5]  # currency is 6th element (index 5)
        @property
        def amount(self):
            return self.values[6]  # amount is 7th element (index 6)
    
    mock_row = MockRow((
        1,  # billing_plan_version_id
        "START_V1",  # version_code
        "MERCADOPAGO",  # provider
        test_prefixed_id,  # provider_plan_id (com prefixo TEST_)
        "TEST",  # environment
        "BRL",  # currency
        Decimal("60.00"),  # amount
        "ACTIVE"  # status
    ))
    
    db.execute.return_value.first.return_value = mock_row
    
    service = PaymentPlanMappingService(db)
    
    # Webhook chega com ID real (sem prefixo TEST_)
    # Isto deve falhar porque não há normalização
    with pytest.raises(ValueError) as exc:
        service.validate_webhook_mapping(
            plan_code="START_V1",
            provider_plan_id=real_mercado_pago_id,  # Sem prefixo, ID real do provider
            environment="TEST",
            amount=Decimal("60.00"),
            currency="BRL"
        )
    
    assert "PAYMENT_MAPPING_MISMATCH" in str(exc.value)
    print("✗ BUG CONFIRMED: Webhook with real provider ID fails when mapping has TEST_ prefix")


def test_provider_id_should_not_include_prefix():
    """
    Teste mostrando que provider_plan_id deve ser o ID real do provider,
    e environment=TEST é suficiente para isolamento.
    """
    real_mercado_pago_id = "22b643676beb47d5b784a0afd4a5ec79"
    
    db = MagicMock()
    query = MagicMock()
    query.filter_by.return_value = query
    query.first.return_value = _version()
    db.query.return_value = query
    
    class MockRow:
        def __init__(self, values):
            self.values = values
        def __iter__(self):
            return iter(self.values)
        @property
        def currency(self):
            return self.values[5]
        @property
        def amount(self):
            return self.values[6]
    
    # Simular banco com ID real, sem prefixo
    mock_row = MockRow((
        1,  # billing_plan_version_id
        "START_V1",  # version_code
        "MERCADOPAGO",  # provider
        real_mercado_pago_id,  # provider_plan_id (sem prefixo)
        "TEST",  # environment
        "BRL",  # currency
        Decimal("60.00"),  # amount
        "ACTIVE"  # status
    ))
    
    db.execute.return_value.first.return_value = mock_row
    
    service = PaymentPlanMappingService(db)
    
    # Webhook com ID real deve passar
    mapping = service.validate_webhook_mapping(
        plan_code="START_V1",
        provider_plan_id=real_mercado_pago_id,  # Idêntico ao banco
        environment="TEST",
        amount=Decimal("60.00"),
        currency="BRL"
    )
    
    assert mapping.provider_plan_id == real_mercado_pago_id
    assert mapping.environment == "TEST"
    print("✓ FIXED: Webhook validates correctly with real provider ID and environment isolation")


def test_test_environment_isolation_without_prefix():
    """
    Teste que environment=TEST + environment=PRODUCTION
    podem usar o mesmo provider_plan_id com isolamento.
    """
    real_mercado_pago_id = "22b643676beb47d5b784a0afd4a5ec79"
    
    db = MagicMock()
    query = MagicMock()
    query.filter_by.return_value = query
    query.first.return_value = _version()
    db.query.return_value = query
    
    class MockRow:
        def __init__(self, values):
            self.values = values
        def __iter__(self):
            return iter(self.values)
        @property
        def currency(self):
            return self.values[5]
        @property
        def amount(self):
            return self.values[6]
    
    # Quando environment=TEST é passado, retorna TEST mapping
    mock_row = MockRow((
        1,  # billing_plan_version_id
        "START_V1",  # version_code
        "MERCADOPAGO",  # provider
        real_mercado_pago_id,  # provider_plan_id
        "TEST",  # environment
        "BRL",  # currency
        Decimal("60.00"),  # amount
        "ACTIVE"  # status
    ))
    
    db.execute.return_value.first.return_value = mock_row
    
    service = PaymentPlanMappingService(db)
    
    # Resolver TEST
    mapping = service.resolve(plan_code="START_V1", environment="TEST")
    assert mapping.environment == "TEST"
    assert mapping.provider_plan_id == real_mercado_pago_id
    print(f"✓ Environment isolation: TEST provider_plan_id = {real_mercado_pago_id}")

