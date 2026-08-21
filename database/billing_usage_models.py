"""Modelos de medição comercial shadow-only da Fase 4.6E."""
from datetime import datetime

from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import relationship

from database.models import Base


class BillingUsageEvent(Base):
    __tablename__ = "billing_usage_events"
    __table_args__ = (UniqueConstraint("metric_key", "event_key", name="uq_billing_usage_event_key"),)

    usage_event_id = Column(BigInteger, primary_key=True)
    account_id = Column(Integer, ForeignKey("billing_accounts.account_id"))
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.subscription_id"))
    cliente_id = Column(Integer, ForeignKey("clientes.cliente_id"))
    metric_key = Column(String(50), nullable=False)
    event_key = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    source_type = Column(String(30), nullable=False)
    source_id = Column(String(255))
    status = Column(String(20), nullable=False, default="COUNTED")
    metadata_json = Column(JSON)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class BillingUsageCounter(Base):
    __tablename__ = "billing_usage_counters"
    __table_args__ = (UniqueConstraint("subscription_id", "metric_key", "period_start", "period_end", name="uq_billing_usage_counter_period"),)

    usage_counter_id = Column(BigInteger, primary_key=True)
    subscription_id = Column(Integer, ForeignKey("billing_subscriptions.subscription_id"), nullable=False)
    metric_key = Column(String(50), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
