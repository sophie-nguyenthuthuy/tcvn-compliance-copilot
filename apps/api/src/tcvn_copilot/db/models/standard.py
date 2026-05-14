"""TCVN/QCVN standards, their clauses, and clause embeddings (pgvector)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tcvn_copilot.config import get_settings
from tcvn_copilot.db.models import Base

# Bind dim at import time — Alembic captures it for the migration.
_EMBED_DIM = get_settings().embedding_dim


class Standard(Base):
    __tablename__ = "standards"

    code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    title_vi: Mapped[str] = mapped_column(String(512), nullable=False)
    title_en: Mapped[str | None] = mapped_column(String(512))
    issuer: Mapped[str] = mapped_column(String(255), default="Bộ Xây dựng", nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    issued_at: Mapped[date | None] = mapped_column(Date)
    effective_at: Mapped[date | None] = mapped_column(Date)
    superseded_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("standards.id"))

    description: Mapped[str | None] = mapped_column(Text)
    source_hash: Mapped[str | None] = mapped_column(String(128))  # sha256 of canonical source

    clauses: Mapped[list["StandardClause"]] = relationship(
        back_populates="standard",
        cascade="all, delete-orphan",
        order_by="StandardClause.ordinal",
    )


class StandardClause(Base):
    """A single article / section / clause of a standard."""

    __tablename__ = "standard_clauses"
    __table_args__ = (
        UniqueConstraint("standard_id", "clause_number", name="uq_clause_per_standard"),
        Index("ix_clause_text_trgm", "text_vi", postgresql_using="gin",
              postgresql_ops={"text_vi": "gin_trgm_ops"}),
    )

    standard_id: Mapped[UUID] = mapped_column(
        ForeignKey("standards.id", ondelete="CASCADE"), index=True
    )
    clause_number: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "3.2.4"
    title_vi: Mapped[str | None] = mapped_column(String(512))
    text_vi: Mapped[str] = mapped_column(Text, nullable=False)
    text_en: Mapped[str | None] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Hierarchical anchor — Part / Chapter / Section path joined with " / "
    path: Mapped[str | None] = mapped_column(String(1024))

    # Tags used by the rule engine to scope which clauses fire for which review.
    # e.g. {"category": "fire_safety", "topic": ["egress", "stairs"]}
    tags: Mapped[list[str] | None] = mapped_column(
        # using ARRAY(String) at the DB level
        Text,  # serialised at the migration level; ORM uses array via dialect type
    )

    standard: Mapped["Standard"] = relationship(back_populates="clauses")
    embedding: Mapped["StandardClauseEmbedding | None"] = relationship(
        back_populates="clause",
        cascade="all, delete-orphan",
        uselist=False,
    )


class StandardClauseEmbedding(Base):
    """Vector embedding for a clause. Kept in a separate table so we can re-embed
    without rewriting the clause text, and to keep clause rows lean."""

    __tablename__ = "standard_clause_embeddings"
    __table_args__ = (
        Index(
            "ix_clause_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    clause_id: Mapped[UUID] = mapped_column(
        ForeignKey("standard_clauses.id", ondelete="CASCADE"), unique=True, index=True
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dim: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBED_DIM), nullable=False)

    clause: Mapped["StandardClause"] = relationship(back_populates="embedding")
