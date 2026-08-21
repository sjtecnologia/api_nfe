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
