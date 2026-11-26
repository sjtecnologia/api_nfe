"""Modelos comerciais aditivos da Fase 4.6C.

Estes modelos são shadow-only: não são importados pelo fluxo fiscal e não
aplicam bloqueios. A migration correspondente ainda precisa de aprovação.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from database.models import Base


class BillingAccount(Base):
    __tablename__ = "billing_accounts"

    account_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(30), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("BillingSubscription", back_populates="account")


class BillingPlan(Base):
    __tablename__ = "billing_plans"

    plan_id = Column(Integer, primary_key=True)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)

    versions = relationship("BillingPlanVersion", back_populates="plan")


class BillingPlanVersion(Base):
    __tablename__ = "billing_plan_versions"

    plan_version_id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("billing_plans.plan_id"), nullable=False)
    version_code = Column(String(50), nullable=False, unique=True)
    price = Column(Numeric(10, 2))
    currency = Column(String(3), nullable=False, default="BRL")
    valid_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    valid_until = Column(DateTime)
    status = Column(String(30), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    plan = relationship("BillingPlan", back_populates="versions")
    features = relationship("BillingPlanFeature", back_populates="plan_version")
    subscriptions = relationship("BillingSubscription", back_populates="plan_version")


class BillingFeature(Base):
    __tablename__ = "billing_features"

    feature_id = Column(Integer, primary_key=True)
    key = Column(String(80), nullable=False, unique=True)
    name = Column(String(150), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False, default="ROADMAP")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    plan_features = relationship("BillingPlanFeature", back_populates="feature")


class BillingPlanFeature(Base):
    __tablename__ = "billing_plan_features"
    __table_args__ = (UniqueConstraint("plan_version_id", "feature_id", name="uq_billing_plan_feature"),)

    plan_feature_id = Column(Integer, primary_key=True)
    plan_version_id = Column(Integer, ForeignKey("billing_plan_versions.plan_version_id"), nullable=False)
    feature_id = Column(Integer, ForeignKey("billing_features.feature_id"), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False)
    access_level = Column(String(30), nullable=False, default="STANDARD")
    limit_type = Column(String(40), nullable=False, default="DISABLED")
    limit_value = Column(Integer)
    metadata_json = Column(Text)

    plan_version = relationship("BillingPlanVersion", back_populates="features")
    feature = relationship("BillingFeature", back_populates="plan_features")


class BillingSubscription(Base):
    __tablename__ = "billing_subscriptions"

    subscription_id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("billing_accounts.account_id"), nullable=False)
    plan_version_id = Column(Integer, ForeignKey("billing_plan_versions.plan_version_id"), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    contracted_price = Column(Numeric(10, 2))
    currency = Column(String(3), nullable=False, default="BRL")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ends_at = Column(DateTime)
    billing_cycle = Column(String(30), nullable=False, default="MONTHLY")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    account = relationship("BillingAccount", back_populates="subscriptions")
    plan_version = relationship("BillingPlanVersion", back_populates="subscriptions")
    companies = relationship("BillingSubscriptionCompany", back_populates="subscription")
    overrides = relationship("BillingSubscriptionOverride", back_populates="subscription")


class BillingSubscriptionCompany(Base):
    __tablename__ = "billing_subscription_companies"
    __table_args__ = (UniqueConstraint("subscription_id", "cliente_id", name="uq_billing_subscription_company"),)

    subscription_company_id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.subscription_id"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.cliente_id"), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    linked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    unlinked_at = Column(DateTime)

    subscription = relationship("BillingSubscription", back_populates="companies")


class BillingSubscriptionOverride(Base):
    __tablename__ = "billing_subscription_overrides"
    __table_args__ = (UniqueConstraint("subscription_id", "key", name="uq_billing_subscription_override"),)

    override_id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.subscription_id"), nullable=False)
    key = Column(String(80), nullable=False)
    value = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime)

    subscription = relationship("BillingSubscription", back_populates="overrides")


class PendingSignup(Base):
    __tablename__ = "pending_signups"
    __table_args__ = (UniqueConstraint("public_token", name="uq_pending_signup_token"),)

    pending_signup_id = Column(Integer, primary_key=True)
    public_token = Column(String(100), nullable=False)
    plan_version_id = Column(Integer, ForeignKey("billing_plan_versions.plan_version_id"), nullable=False)
    email_normalized = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="CREATED")
    contract_version = Column(String(50), nullable=False)
    contract_accepted_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime)
    metadata_json = Column(Text)

    checkout_attempts = relationship("BillingCheckoutAttempt", back_populates="pending_signup")


class BillingCheckoutAttempt(Base):
    __tablename__ = "billing_checkout_attempts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_checkout_attempt_idempotency"),)

    checkout_attempt_id = Column(Integer, primary_key=True)
    pending_signup_id = Column(Integer, ForeignKey("pending_signups.pending_signup_id"), nullable=False)
    plan_version_id = Column(Integer, ForeignKey("billing_plan_versions.plan_version_id"), nullable=False)
    provider = Column(String(30), nullable=False, default="shadow")
    provider_reference = Column(String(255))
    provider_plan_id = Column(String(255))
    external_reference = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="PENDING")
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    idempotency_key = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime)
    provider_metadata = Column(Text)

    pending_signup = relationship("PendingSignup", back_populates="checkout_attempts")


class BillingPaymentEvent(Base):
    __tablename__ = "billing_payment_events"
    __table_args__ = (UniqueConstraint("provider", "provider_event_id", name="uq_payment_provider_event"),)

    payment_event_id = Column(Integer, primary_key=True)
    provider = Column(String(30), nullable=False)
    provider_event_id = Column(String(255), nullable=False)
    checkout_attempt_id = Column(Integer, ForeignKey("billing_checkout_attempts.checkout_attempt_id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime)
    payload_hash = Column(String(64), nullable=False)
    metadata_json = Column(Text)


class PaymentProviderPlanMapping(Base):
    __tablename__ = "payment_provider_plan_mappings"
    __table_args__ = (
        UniqueConstraint("provider", "environment", "provider_plan_id", name="uq_provider_plan_mapping_external"),
        UniqueConstraint("billing_plan_version_id", "provider", "environment", name="uq_provider_plan_mapping_version"),
    )

    mapping_id = Column(Integer, primary_key=True)
    billing_plan_version_id = Column(Integer, ForeignKey("billing_plan_versions.plan_version_id"), nullable=False)
    provider = Column(String(30), nullable=False)
    provider_plan_id = Column(String(255), nullable=False)
    environment = Column(String(20), nullable=False)
    currency = Column(String(3), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(30), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
