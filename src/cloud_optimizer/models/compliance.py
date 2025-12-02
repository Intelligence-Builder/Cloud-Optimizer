"""Compliance framework models."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cloud_optimizer.database import Base


class ComplianceFramework(Base):
    """Compliance framework model.

    Represents a compliance framework (e.g., CIS, PCI-DSS, HIPAA).
    """

    __tablename__ = "compliance_frameworks"

    framework_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False)

    controls: Mapped[list["ComplianceControl"]] = relationship(
        "ComplianceControl", back_populates="framework"
    )


class ComplianceControl(Base):
    """Compliance control model.

    Represents a specific control within a compliance framework.
    """

    __tablename__ = "compliance_controls"

    control_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    framework_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("compliance_frameworks.framework_id"),
        nullable=False,
    )
    control_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    framework: Mapped["ComplianceFramework"] = relationship(
        "ComplianceFramework", back_populates="controls"
    )


class RuleComplianceMapping(Base):
    """Rule to compliance control mapping.

    Maps scanner rules to compliance framework controls.
    """

    __tablename__ = "rule_compliance_mappings"

    mapping_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    control_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("compliance_controls.control_id"),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
